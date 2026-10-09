"""Honest relay: submits transactions on behalf of users/witnesses. It holds no authority of its own: every accepted action is
authorised by a user signature or a witness quorum, which the ledger verifies. Used by agent-2's own tests and E1 flow; a runner may
instead play (a deviating) relay itself with raw transactions (A2-0008)."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import eip712, keys
from .chain import ERROR_NAMES
from .ledger import Ledger


class RelayError(RuntimeError):
    pass


@dataclass
class ForwardResult:
    request_digest: str
    code: str
    credential_digest: str | None = None
    records: list = field(default_factory=list)
    log_id: str | None = None


class Relay:
    def __init__(self, led: Ledger, key_label: str):
        self.led = led
        self._key = keys.synthetic_private_key(key_label)
        from eth_account import Account
        self.address = Account.from_key(self._key).address.lower()
        if self.address != led.deployment["fixture"]["relay"]["address"]:
            raise RelayError("relay key does not match the deployment's configured relay address")

    def _events(self, receipt: dict, contract) -> list[tuple[str, dict]]:
        out = []
        for log in receipt["logs"]:
            if log["address"].lower() == contract.address:
                try:
                    out.append(contract.decode_log(log))
                except Exception:
                    continue
        return out

    def forward(self, signed: dict, bundle: dict) -> ForwardResult:
        receipt = self.led.pbc.send(self._key, self.led.PSC, "requestAccess", signed["request"], signed["signature"], bundle)
        for name, ev in self._events(receipt, self.led.PSC):
            if ev.get("requestDigest") != signed["requestDigest"]:
                continue
            if name == "AccessForwarded":
                return ForwardResult(ev["requestDigest"], "NONE", ev["credentialDigest"], ev["verifiedAttributes"], ev["requestLogId"])
            if name == "AccessDenied":
                return ForwardResult(ev["requestDigest"], ERROR_NAMES[int(ev["code"])], log_id=ev["requestLogId"])
        raise RelayError("PSC emitted neither AccessForwarded nor AccessDenied for this request")

    # -- DBC / outcome legs -------------------------------------------------------------------------------------------------------
    def accept_state(self, checkpoint_bundle: dict) -> None:
        """Submit a witness-signed StateCheckpoint to the DBC (authority = the witness signature, not this relay)."""
        self.led.dbc.send(self._key, self.led.KSSC, "acceptState", checkpoint_bundle["checkpoint"], checkpoint_bundle["signatures"])

    def deliver(self, signed: dict, decision_bundle: dict) -> str | None:
        """Submit request + witness certificate to the ACSC. Returns the grant id if the DBC issued a grant, else None (valid deny)."""
        led = self.led
        cert = {"decision": decision_bundle["decision"], "signatures": decision_bundle["signatures"]}
        led.dbc.send(self._key, led.ACSC, "consumeDecision", signed["request"], cert, decision_bundle["credentialRecords"])
        grant_id = "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
        return grant_id if led.dbc.call(led.KSSC, "getGrant", grant_id)[5] else None

    def report_outcome(self, request_digest: str, outcome_digest: str, receipt_bundle: dict) -> None:
        """Report the outcome to the PSC with a witness-signed GrantReceipt (repaired-e; only the configured relay may call)."""
        self.led.pbc.send(self._key, self.led.PSC, "reportAttestedOutcome", request_digest, outcome_digest,
                          receipt_bundle["receipt"], receipt_bundle["signatures"])
