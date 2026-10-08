"""Honest decision witness (E: one explicitly trusted witness, q = 1 of 1).

The witness signs ONLY facts it recomputes from ledger state: it never accepts attributes, a request body or a block from the relay.
Assumptions (stated, not hidden): the PBC and DBC are safe ledgers (the latest block is treated as final); a block hash is the
witness's own observation, not a light-client proof; E has one witness, so a compromised witness breaks every guarantee here.
Error classes follow the interface list; a refusal is an exception, never a signature.
"""
from __future__ import annotations

from eth_account import Account
from eth_utils import keccak

from . import eip712, keys, messages, wire
from .abi import AbiError
from .chain import Chain, ChainError
from .ledger import Ledger

DECISION_TTL = 30


class WitnessError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


class Witness:
    def __init__(self, led: Ledger, key_label: str | None = None):
        self.led = led
        fx = led.deployment["fixture"]
        label = key_label or fx["witnessSet"]["keyLabels"][0]
        self._key = keys.synthetic_private_key(label)
        self.address = Account.from_key(self._key).address.lower()
        pbc_set, dbc_set = led.pbc.call(led.PSC, "witnesses"), led.dbc.call(led.KSSC, "witnesses")
        if self.address not in pbc_set or self.address not in dbc_set:
            raise WitnessError("UNKNOWN_AUTHORITY", "this key is not in the configured witness set of both chains")
        self.witness_set_version = led.pbc.call(led.PSC, "witnessSetVersion")
        if led.dbc.call(led.KSSC, "witnessSetVersion") != self.witness_set_version:
            raise WitnessError("STALE_STATE", "PSC and KSSC disagree on the witness-set version")
        self.checkpoint_ttl = int(fx["ttlSeconds"]["checkpointMax"])

    # -- helpers -----------------------------------------------------------------------------------------------------------------
    def _sign(self, name: str, message: dict) -> str:
        digest = messages.digest_of(name, message, messages.domain_for(name, message, self.led.deployment))
        sig = eip712.sign_digest(self._key, digest)
        if eip712.recover(digest, sig) != self.address:          # an explicit check: `assert` is stripped by python -O
            raise WitnessError("BAD_SIGNATURE", "refusing to emit a signature that does not recover to the witness address")
        return sig

    # -- checkpoint --------------------------------------------------------------------------------------------------------------
    def checkpoint(self) -> dict:
        """A signed StateCheckpoint of the latest PBC block. Its sequence comes from the DBC, never from a caller."""
        led = self.led
        head = led.pbc.get_block("latest")
        exists, cur = led.dbc.call(led.KSSC, "currentCheckpoint")
        cp = {"sequence": str(int(cur["sequence"]) + 1) if exists else "1",
              "authEpoch": led.pbc.call(led.TMSC, "authEpoch", block=head["number"]),
              "policyVersion": led.pbc.call(led.PSC, "policyVersion", block=head["number"]),
              "keyEpoch": "0", "witnessSetVersion": self.witness_set_version,
              "sourceChainId": str(led.pbc.chain_id), "psc": led.PSC.address,
              "sourceBlockNumber": str(head["number"]), "sourceBlockHash": head["hash"],
              "expiresAt": str(led.dbc.now() + self.checkpoint_ttl)}
        wire.state_checkpoint(cp)
        return {"checkpoint": cp, "signatures": [self._sign("StateCheckpoint", cp)]}

    # -- decision ----------------------------------------------------------------------------------------------------------------
    def _forwarded_request(self, digest: str) -> tuple[dict, dict, int]:
        """(request, bundle, forwarding block) recovered from the PBC itself: the logged event and the transaction calldata."""
        led = self.led
        rec = led.pbc.call(led.PSC, "getRequest", digest)
        if rec["status"] == "2":
            raise WitnessError("REPLAY", "an outcome is already recorded for this request")
        if rec["status"] != "1":
            raise WitnessError("WRONG_SUBJECT", "the PBC has not forwarded this request digest")
        topic0 = "0x" + keccak(text=led.PSC.event_signature("AccessForwarded")).hex()
        logs = led.pbc.get_logs(led.PSC.address, [topic0, digest])
        if len(logs) != 1:
            raise WitnessError("WRONG_SUBJECT", "expected exactly one AccessForwarded log for this digest")
        try:
            tx = led.pbc.get_transaction(logs[0]["transactionHash"])
            if str(tx.get("to", "")).lower() != led.PSC.address:    # a wrapper/multicall could hand the PSC a different bundle than the calldata shows
                raise WitnessError("WRONG_SUBJECT", "the forwarding transaction was not sent directly to the PSC")
            name, args = led.PSC.decode_input(bytes.fromhex(tx["input"][2:]))
        except (AbiError, ChainError):
            raise WitnessError("WRONG_SUBJECT", "the forwarding transaction is not a direct requestAccess call") from None
        if name != "requestAccess":
            raise WitnessError("WRONG_SUBJECT", "the forwarding transaction is not requestAccess")
        request, _sig, bundle = args
        recomputed = "0x" + messages.digest_of("AccessRequest", request, messages.domain_for("AccessRequest", request, led.deployment)).hex()
        if recomputed != digest:
            raise WitnessError("WRONG_SUBJECT", "recovered request does not hash to the requested digest")
        if (request["gid"], request["dataId"], request["destinationChainId"], request["kssc"], request["expiresAt"]) != (
                rec["gid"], rec["dataId"], rec["destinationChainId"], rec["kssc"], rec["expiresAt"]):
            raise WitnessError("WRONG_SUBJECT", "recovered request disagrees with the PSC record")
        return request, bundle, int(logs[0]["blockNumber"], 16)

    def decide(self, request_digest: str) -> dict:
        led = self.led
        try:
            wire.hash32(request_digest)
        except wire.WireError as e:
            raise WitnessError("MALFORMED", str(e)) from None
        request, bundle, forwarded_at = self._forwarded_request(request_digest)
        exists, cp = led.dbc.call(led.KSSC, "currentCheckpoint")
        dbc_now, pbc_now = led.dbc.now(), led.pbc.now()
        if not exists or dbc_now >= int(cp["expiresAt"]):
            raise WitnessError("STALE_STATE", "the DBC holds no fresh checkpoint; collect and accept a new one")
        src = int(cp["sourceBlockNumber"])
        if led.pbc.get_block(src)["hash"] != cp["sourceBlockHash"] or led.pbc.call(led.TMSC, "authEpoch", block=src) != cp["authEpoch"]:
            raise WitnessError("STALE_STATE", "the DBC checkpoint does not describe the PBC block it names")
        if forwarded_at > src:
            raise WitnessError("STALE_STATE", "the DBC checkpoint predates this request; collect a new checkpoint")
        if request["authEpoch"] != cp["authEpoch"] or request["policyVersion"] != cp["policyVersion"]:
            raise WitnessError("STALE_STATE", "request authEpoch/policyVersion differ from the DBC checkpoint")
        if request["keyEpoch"] != cp["keyEpoch"]:
            raise WitnessError("WRONG_EPOCH", "request keyEpoch differs from the DBC checkpoint")
        if request["destinationChainId"] != str(led.dbc.chain_id) or request["kssc"] != led.KSSC.address:
            raise WitnessError("WRONG_DESTINATION", "the request names another destination than this DBC")
        if led.dbc.call(led.KSSC, "nonceConsumed", request["gid"], request["nonce"]) is True:
            raise WitnessError("REPLAY", "the DBC already consumed this (gid, nonce); an ALLOW would revert")
        if max(dbc_now, pbc_now) >= int(request["expiresAt"]):
            raise WitnessError("EXPIRED", "the request has expired on at least one chain's clock")
        # Independent credential evaluation at the checkpoint's PBC block, with that block's own timestamp (A1-0011 answer 1; A29).
        at = led.pbc.get_block(src)["timestamp"]
        code, records = led.pbc.call(led.TMSC, "checkCredentials", request["gid"], bundle, str(at), block=src)
        # ALLOW needs valid credentials AND a policy the DBC will accept (A1-0017): an ALLOW the ACSC rejects reverts POLICY_DENIED and
        # loses the DBC's own audit record, whereas a signed DENY is logged there. The ACSC still reverts a forged ALLOW (defence in depth).
        # DecisionVerifier step 13 re-checks every record at DBC `now`: a record that lapsed since the checkpoint block would make even a DENY
        # revert EXPIRED, so a lapsed set is attested as "no valid credentials" (empty records) and denied.
        if code == "0" and any(int(r["validUntil"]) <= dbc_now for r in records):
            code, records = "REVOKED-BY-TIME", []
        satisfied = code == "0" and led.dbc.call(led.ACSC, "evaluate", request["dataId"], records) is True
        decision = {"requestDigest": request_digest, "result": "1" if satisfied else "0",
                    "credentialDigest": "0x" + eip712.credential_digest(records).hex(), "stateSequence": cp["sequence"],
                    "witnessSetVersion": cp["witnessSetVersion"], "sourceBlockNumber": cp["sourceBlockNumber"],
                    "sourceBlockHash": cp["sourceBlockHash"],
                    "expiresAt": str(min(int(request["expiresAt"]), int(cp["expiresAt"]), dbc_now + DECISION_TTL))}
        wire.access_decision(decision)
        return {"decision": decision, "signatures": [self._sign("AccessDecision", decision)], "credentialRecords": records}

    # -- receipt -----------------------------------------------------------------------------------------------------------------
    def attest_grant(self, grant_id: str) -> dict:
        led = self.led
        try:
            wire.hash32(grant_id)
        except wire.WireError as e:
            raise WitnessError("MALFORMED", str(e)) from None
        head = led.dbc.get_block("latest")
        digest, data_id, gid, key_epoch, expires, allowed = led.dbc.call(led.KSSC, "getGrant", grant_id, block=head["number"])
        if not allowed or "0x" + eip712.grant_id(bytes.fromhex(digest[2:]), led.KSSC.address, led.dbc.chain_id).hex() != grant_id:
            raise WitnessError("NOT_COMMITTED", "no allowed grant with this id exists on the DBC")
        rec = led.pbc.call(led.PSC, "getRequest", digest)
        if rec["status"] != "1" or (rec["gid"], rec["dataId"]) != (gid, data_id):
            raise WitnessError("WRONG_SUBJECT", "the PBC record does not match the DBC grant")
        receipt = {"requestDigest": digest, "grantId": grant_id, "gid": gid, "dataId": data_id, "keyEpoch": key_epoch,
                   "grantExpiresAt": expires, "witnessSetVersion": self.witness_set_version, "dbcChainId": str(led.dbc.chain_id),
                   "kssc": led.KSSC.address, "dbcBlockNumber": str(head["number"]), "dbcBlockHash": head["hash"]}
        wire.grant_receipt(receipt)
        return {"receipt": receipt, "signatures": [self._sign("GrantReceipt", receipt)]}
