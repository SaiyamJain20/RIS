"""F-profile honest witness, StateCheckpoint path (HMBC2020 successor, F task 2 slice 4a).

PAPER-DERIVED RECONSTRUCTION of SIGNING-RULES sections 2, 3 (StateCheckpoint row) and 4. `WitnessService.sign_checkpoint(proposal)` treats the proposal only as a candidate: it recomputes every field
from the witness's OWN view of the ledgers (an injected `view`), refuses on the first failing row, and only then asks the durable store (`witness_state`) to record the choice and return the
signature, which exists only after the store committed. `derive_checkpoint` is the PROPOSER side (the pool derives the proposal once from its own reads and keeps it).

Scope: StateCheckpoint only. Decision, receipt and governance are later slices; the D50 live-read reconstruction is another. The carried E `witness.py` is NOT changed (the successor adapter picks the
F service for F profiles), so E behaviour cannot move because of this module. No host clock, no randomness, no network: the only time is the observed block timestamp of the target ledger.

The injected view (what the witness reads from its own RPC):
  observe(chain)            -> {"chainId", "blockNumber", "blockHash", "timestamp"} of the LATEST block of "pbc" or "dbc" (decimal strings, 0x block hash)
  pbc_block(number)         -> {"number", "hash"} or None when the PBC has no such block
  reads_at(number)          -> {"authEpoch", "policyVersion", "witnessSetVersion"} as of that PBC block
  dbc_current_checkpoint()  -> None, or {"sequence", "sourceBlockNumber"} of the DBC's current checkpoint
Any of them may raise `LedgerUnreachable`; the service maps that to ADAPTER_UNAVAILABLE / LEDGER_UNREACHABLE and writes nothing.

Refusal classes where F0 does not fix one (explicit choices): shape MALFORMED; chain or psc WRONG_DESTINATION; a wrong sequence, an unconfirmable block, a snapshot that disagrees with the witness's reads,
a stale view and an expiry above the window STALE_STATE with reason PROPOSAL_MISMATCH (the message names the field); keyEpoch other than 0 WRONG_EPOCH; another witnessSetVersion STALE_STATE with
WITNESS_SET_MISMATCH; an expiry at or before the observation EXPIRED. The store's own refusals pass through unchanged (CONFLICT_PINNED with the recorded value, WITNESS_FAULTED).
"""
from __future__ import annotations

from eth_account import Account

from . import eip712, messages, wire
from . import witness_state as ws

EFFECT = ("authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash")
DEFAULT_PROPOSER_TTL = 30
DEFAULT_MAX_TTL = 60


class LedgerUnreachable(Exception):
    """The witness could not read a ledger (raised by the injected view)."""


class WitnessRefusal(Exception):
    def __init__(self, code, reason, message, recorded=None):
        super().__init__(f"{code}{'/' + reason if reason else ''}: {message}")
        self.code, self.reason, self.message, self.recorded = code, reason, message, recorded


def _mismatch(field, text):
    return WitnessRefusal("STALE_STATE", "PROPOSAL_MISMATCH", f"{field}: {text}")


def derive_checkpoint(view, deployment, *, ttl=DEFAULT_PROPOSER_TTL):
    """The proposal, derived once from the proposer's own reads: sequence = DBC current + 1 (or 1), the PBC latest block, its epochs, `expiresAt` = the DBC's latest block timestamp + ttl."""
    cur = view.dbc_current_checkpoint()
    head = view.observe("pbc")
    reads = view.reads_at(int(head["blockNumber"]))
    dbc = view.observe("dbc")
    pbc, psc = deployment["chains"]["pbc"], deployment["chains"]["pbc"]["contracts"]["PSC"]
    cp = {"sequence": "1" if cur is None else str(int(cur["sequence"]) + 1), "authEpoch": reads["authEpoch"], "policyVersion": reads["policyVersion"], "keyEpoch": "0",
          "witnessSetVersion": reads["witnessSetVersion"], "sourceChainId": pbc["chainId"], "psc": psc, "sourceBlockNumber": head["blockNumber"], "sourceBlockHash": head["blockHash"],
          "expiresAt": str(int(dbc["timestamp"]) + ttl)}
    wire.state_checkpoint(cp)
    return cp


class WitnessService:
    def __init__(self, *, store, key, view, deployment, witness_set_version, max_checkpoint_ttl=DEFAULT_MAX_TTL):
        if not isinstance(max_checkpoint_ttl, int) or isinstance(max_checkpoint_ttl, bool) or max_checkpoint_ttl < 1:
            raise ValueError("max_checkpoint_ttl must be a positive integer")
        self._store, self._key, self._view, self._max_ttl = store, key, view, max_checkpoint_ttl
        self.address = Account.from_key(key).address.lower()
        self._wsv = witness_set_version
        pbc = deployment["chains"]["pbc"]
        self._pbc_id, self._psc = pbc["chainId"], pbc["contracts"]["PSC"]
        self._domain = "0x" + eip712.domain_separator(messages.domain_for("StateCheckpoint", {}, deployment)).hex()
        self._deployment = deployment

    # ---- the F signing rule for a checkpoint ------------------------------------------------------------------------------------------------------------------------
    def sign_checkpoint(self, proposal):
        try:
            cp = self._shape(proposal)
            current = self._validate(cp)
            return self._record(cp, current)
        except LedgerUnreachable as e:
            raise WitnessRefusal("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE", f"the ledger could not be read: {e}") from None
        except ws.StoreError as e:
            raise WitnessRefusal(e.code, e.reason, e.message, e.recorded) from None

    @staticmethod
    def _shape(proposal):
        try:
            return dict(wire.state_checkpoint(proposal))
        except (wire.WireError, TypeError):
            raise WitnessRefusal("MALFORMED", None, "the proposal is not a canonical StateCheckpoint") from None

    def _validate(self, cp):
        if cp["sourceChainId"] != self._pbc_id or cp["psc"] != self._psc:
            raise WitnessRefusal("WRONG_DESTINATION", None, "sourceChainId or psc differs from this deployment")
        view = self._view
        current = view.dbc_current_checkpoint()
        expected = 1 if current is None else int(current["sequence"]) + 1
        if int(cp["sequence"]) != expected:
            raise _mismatch("sequence", f"the next sequence is {expected}")
        head = view.observe("pbc")
        n = int(cp["sourceBlockNumber"])
        block = view.pbc_block(n)
        if block is None or n > int(head["blockNumber"]):
            raise _mismatch("sourceBlockNumber", "not a block this witness can see (unknown or after its own PBC head)")
        if block["hash"] != cp["sourceBlockHash"]:
            raise _mismatch("sourceBlockHash", "differs from this witness's own block hash")
        if current is not None and n < int(current["sourceBlockNumber"]):
            raise _mismatch("sourceBlockNumber", "is below the DBC current checkpoint's block")
        reads = view.reads_at(n)
        if cp["keyEpoch"] != "0":
            raise WitnessRefusal("WRONG_EPOCH", None, "keyEpoch must be 0")
        if cp["witnessSetVersion"] != self._wsv or cp["witnessSetVersion"] != reads["witnessSetVersion"]:
            raise WitnessRefusal("STALE_STATE", "WITNESS_SET_MISMATCH", "witnessSetVersion differs from this witness's own")
        for f in ("authEpoch", "policyVersion"):
            if cp[f] != reads[f]:
                raise _mismatch(f, "differs from this witness's own read at the proposal's block")
        head_reads = view.reads_at(int(head["blockNumber"]))
        for f in ("authEpoch", "policyVersion"):
            if cp[f] != head_reads[f]:
                raise _mismatch(f, "stale view: this witness reads another value at its own PBC head")
        ts = int(view.observe("dbc")["timestamp"])
        e = int(cp["expiresAt"])
        if e <= ts:
            raise WitnessRefusal("EXPIRED", None, "expiresAt is not after the DBC's latest block timestamp")
        if e > ts + self._max_ttl:
            raise _mismatch("expiresAt", f"is more than {self._max_ttl} s after the DBC's latest block timestamp")
        return current

    def _signer(self, digest_hex):
        d = bytes.fromhex(digest_hex[2:])
        sig = eip712.sign_digest(self._key, d)
        if eip712.recover(d, sig) != self.address:               # an explicit check: `assert` is stripped by python -O
            raise WitnessRefusal("BAD_SIGNATURE", None, "refusing to emit a signature that does not recover to the witness address")
        return sig

    def _record(self, cp, current):
        digest = messages.digest_of("StateCheckpoint", cp, messages.domain_for("StateCheckpoint", cp, self._deployment))
        return self._store.sign(type="StateCheckpoint", domain=self._domain, wsv=cp["witnessSetVersion"], key=cp["sequence"], effect={k: cp[k] for k in EFFECT}, expires_at=cp["expiresAt"],
                                digest="0x" + digest.hex(), signer=self._signer, observe=lambda: self._view.observe("dbc"),
                                overtaken=("overtaken-checkpoint", "0" if current is None else str(current["sequence"])))
