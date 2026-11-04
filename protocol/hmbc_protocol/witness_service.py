"""F-profile honest witness, StateCheckpoint (slice 4a) and AccessDecision (slice 4b) paths (HMBC2020 successor, F task 2).

PAPER-DERIVED RECONSTRUCTION of SIGNING-RULES sections 2, 3 (StateCheckpoint row) and 4. `WitnessService.sign_checkpoint(proposal)` treats the proposal only as a candidate: it recomputes every field
from the witness's OWN view of the ledgers (an injected `view`), refuses on the first failing row, and only then asks the durable store (`witness_state`) to record the choice and return the
signature, which exists only after the store committed. `derive_checkpoint` is the PROPOSER side (the pool derives the proposal once from its own reads and keeps it).

Scope: StateCheckpoint and AccessDecision. Receipt and governance are later slices; the D50 live-read reconstruction is another.
AccessDecision is a PURE FUNCTION of the request and the DBC's current checkpoint, so `derive_decision` DERIVES the decision from the witness's own view (the E `witness.decide` logic with the F changes:
`expiresAt = min(request.expiresAt, checkpoint.expiresAt)`, no host-clock term) and `sign_decision` signs only when the proposal EQUALS that derivation field by field (rows (c) to (e) of the decision row).
The grant-existence death of an ALLOW decision is a store capability this service never needs: a request whose nonce is consumed is refused REPLAY before anything is recorded. The carried E `witness.py` is NOT changed (the successor adapter picks the
F service for F profiles), so E behaviour cannot move because of this module. No host clock, no randomness, no network: the only time is the observed block timestamp of the target ledger.

The injected view (what the witness reads from its own RPC):
  observe(chain)            -> {"chainId", "blockNumber", "blockHash", "timestamp"} of the LATEST block of "pbc" or "dbc" (decimal strings, 0x block hash)
  pbc_block(number)         -> {"number", "hash"} or None when the PBC has no such block
  reads_at(number)          -> {"authEpoch", "policyVersion", "witnessSetVersion"} as of that PBC block
  dbc_current_checkpoint()  -> None, or the DBC's current checkpoint (the checkpoint path reads "sequence" and "sourceBlockNumber"; the decision path reads all ten fields)
Decision path only: pbc_block(n) also carries "timestamp"; now(chain) -> int (max of latest and pending, as E: conservative for REFUSING); psc_request(digest) -> {"status", "gid", "dataId",
  "destinationChainId", "kssc", "expiresAt"}; forwarded_logs(digest) -> [{"txHash", "block"}]; forwarding_call(txHash) -> None or {"to", "method", "request", "signature", "bundle"};
  nonce_consumed(gid, nonce) -> bool; credentials(gid, bundle, at_timestamp, block) -> (code, records); policy_satisfied(dataId, records) -> bool.
Any of them may raise `LedgerUnreachable`; the service maps that to ADAPTER_UNAVAILABLE / LEDGER_UNREACHABLE and writes nothing.

Refusal classes where F0 does not fix one (explicit choices): shape MALFORMED; chain or psc WRONG_DESTINATION; a wrong sequence, an unconfirmable block, a snapshot that disagrees with the witness's reads,
a stale view and an expiry above the window STALE_STATE with reason PROPOSAL_MISMATCH (the message names the field); keyEpoch other than 0 WRONG_EPOCH; another witnessSetVersion STALE_STATE with
WITNESS_SET_MISMATCH; an expiry at or before the observation EXPIRED. The store's own refusals pass through unchanged (CONFLICT_PINNED with the recorded value, WITNESS_FAULTED).
"""
from __future__ import annotations

from eth_account import Account

from . import eip712, messages, wire
from . import witness_state as ws

EFFECT_DECISION = ("result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash")
DECISION_FIELDS = ("requestDigest", "result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash", "expiresAt")
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


def _refusal(code, text):
    return WitnessRefusal(code, None, text)


def _unreachable(e):
    return WitnessRefusal("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE", f"the ledger could not be read: {e}")


def derive_decision(view, deployment, request_digest, *, witness_set_version):
    """The decision this witness would sign for `request_digest`, derived from its own reads, with the credential records it attests. Raises WitnessRefusal with the E classes."""
    try:
        return _derive_decision(view, deployment, request_digest, witness_set_version)
    except LedgerUnreachable as e:
        raise _unreachable(e) from None


def _derive_decision(view, deployment, digest, wsv):
    try:
        wire.hash32(digest)
    except (wire.WireError, TypeError):
        raise _refusal("MALFORMED", "the request digest is not a canonical 32-byte hash") from None
    psc, dbc = deployment["chains"]["pbc"]["contracts"]["PSC"], deployment["chains"]["dbc"]
    rec = view.psc_request(digest)
    if rec["status"] == "2":
        raise _refusal("REPLAY", "an outcome is already recorded for this request")
    if rec["status"] != "1":
        raise _refusal("WRONG_SUBJECT", "the PBC has not forwarded this request digest")
    logs = view.forwarded_logs(digest)
    if len(logs) != 1:
        raise _refusal("WRONG_SUBJECT", "expected exactly one AccessForwarded log for this digest")
    call = view.forwarding_call(logs[0]["txHash"])
    if call is None or call["to"] != psc or call["method"] != "requestAccess":
        raise _refusal("WRONG_SUBJECT", "the forwarding transaction is not a direct requestAccess call to the PSC")
    request = call["request"]
    try:
        recomputed = "0x" + messages.digest_of("AccessRequest", request, messages.domain_for("AccessRequest", request, deployment)).hex()
    except (ValueError, KeyError, TypeError):
        raise _refusal("WRONG_SUBJECT", "the recovered request is malformed") from None
    if recomputed != digest:
        raise _refusal("WRONG_SUBJECT", "the recovered request does not hash to the requested digest")
    if tuple(request[k] for k in ("gid", "dataId", "destinationChainId", "kssc", "expiresAt")) != tuple(rec[k] for k in ("gid", "dataId", "destinationChainId", "kssc", "expiresAt")):
        raise _refusal("WRONG_SUBJECT", "the recovered request disagrees with the PSC record")
    cp = view.dbc_current_checkpoint()
    dbc_now, pbc_now = view.now("dbc"), view.now("pbc")
    if cp is None or dbc_now >= int(cp["expiresAt"]):
        raise _refusal("STALE_STATE", "the DBC holds no fresh checkpoint; collect and accept a new one")
    src = int(cp["sourceBlockNumber"])
    block = view.pbc_block(src)
    if block is None or block["hash"] != cp["sourceBlockHash"] or view.reads_at(src)["authEpoch"] != cp["authEpoch"]:
        raise _refusal("STALE_STATE", "the DBC checkpoint does not describe the PBC block it names")
    if cp["witnessSetVersion"] != wsv:
        raise WitnessRefusal("STALE_STATE", "WITNESS_SET_MISMATCH", "the checkpoint's witnessSetVersion is not this witness's")
    if int(logs[0]["block"]) > src:
        raise _refusal("STALE_STATE", "the DBC checkpoint predates this request; collect a new checkpoint")
    if request["authEpoch"] != cp["authEpoch"] or request["policyVersion"] != cp["policyVersion"]:
        raise _refusal("STALE_STATE", "request authEpoch/policyVersion differ from the DBC checkpoint")
    if request["keyEpoch"] != cp["keyEpoch"]:
        raise _refusal("WRONG_EPOCH", "request keyEpoch differs from the DBC checkpoint")
    if request["destinationChainId"] != dbc["chainId"] or request["kssc"] != dbc["contracts"]["KSSC"]:
        raise _refusal("WRONG_DESTINATION", "the request names another destination than this DBC")
    if view.nonce_consumed(request["gid"], request["nonce"]) is True:
        raise _refusal("REPLAY", "the DBC already consumed this (gid, nonce); an ALLOW would revert")
    if max(dbc_now, pbc_now) >= int(request["expiresAt"]):
        raise _refusal("EXPIRED", "the request has expired on at least one chain's clock")
    code, records = view.credentials(request["gid"], call["bundle"], block["timestamp"], src)
    if code == "0" and any(int(r["validUntil"]) <= dbc_now for r in records):
        code, records = "REVOKED-BY-TIME", []                       # a lapsed record would make even a DENY revert EXPIRED at the ledger: attest "no valid credentials"
    satisfied = code == "0" and view.policy_satisfied(request["dataId"], records) is True
    decision = {"requestDigest": digest, "result": "1" if satisfied else "0", "credentialDigest": "0x" + eip712.credential_digest(records).hex(), "stateSequence": cp["sequence"],
                "witnessSetVersion": cp["witnessSetVersion"], "sourceBlockNumber": cp["sourceBlockNumber"], "sourceBlockHash": cp["sourceBlockHash"],
                "expiresAt": str(min(int(request["expiresAt"]), int(cp["expiresAt"])))}
    wire.access_decision(decision)
    return decision, records


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
        self._decision_domain = "0x" + eip712.domain_separator(messages.domain_for("AccessDecision", {}, deployment)).hex()
        self._deployment = deployment

    # ---- the F signing rule for a checkpoint ------------------------------------------------------------------------------------------------------------------------
    def sign_checkpoint(self, proposal):
        return self._guarded(lambda: self._sign_checkpoint(proposal))

    def sign_decision(self, proposal):
        return self._guarded(lambda: self._sign_decision(proposal))

    @staticmethod
    def _guarded(fn):
        try:
            return fn()
        except LedgerUnreachable as e:
            raise _unreachable(e) from None
        except ws.StoreError as e:
            raise WitnessRefusal(e.code, e.reason, e.message, e.recorded) from None

    def _sign_checkpoint(self, proposal):
        cp = self._shape(proposal)
        current = self._validate(cp)
        return self._record(cp, current)

    def _sign_decision(self, proposal):
        try:
            prop = dict(wire.access_decision(proposal))
        except (wire.WireError, TypeError):
            raise _refusal("MALFORMED", "the proposal is not a canonical AccessDecision") from None
        own, _ = _derive_decision(self._view, self._deployment, prop["requestDigest"], self._wsv)
        for f in DECISION_FIELDS:
            if prop[f] != own[f]:
                raise _mismatch(f, "differs from this witness's own derivation")
        digest = messages.digest_of("AccessDecision", own, messages.domain_for("AccessDecision", own, self._deployment))
        return self._store.sign(type="AccessDecision", domain=self._decision_domain, wsv=own["witnessSetVersion"], key=own["requestDigest"], effect={k: own[k] for k in EFFECT_DECISION},
                                expires_at=own["expiresAt"], digest="0x" + digest.hex(), signer=self._signer, observe=lambda: self._view.observe("dbc"),
                                overtaken=("overtaken-decision-sequence", own["stateSequence"]))

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
