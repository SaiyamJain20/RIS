"""F-profile honest witness, StateCheckpoint (4a), AccessDecision (4b), GrantReceipt (4c) and GovernanceAction (4d) paths (HMBC2020 successor, F task 2).

PAPER-DERIVED RECONSTRUCTION of SIGNING-RULES sections 2, 3 (StateCheckpoint row) and 4. `WitnessService.sign_checkpoint(proposal)` treats the proposal only as a candidate: it recomputes every field
from the witness's OWN view of the ledgers (an injected `view`), refuses on the first failing row, and only then asks the durable store (`witness_state`) to record the choice and return the
signature, which exists only after the store committed. `derive_checkpoint` is the PROPOSER side (the pool derives the proposal once from its own reads and keeps it).

Scope: all four signed types. The D50 live-read reconstruction is a later slice.
AccessDecision is a PURE FUNCTION of the request and the DBC's current checkpoint, so `derive_decision` DERIVES the decision from the witness's own view (the E `witness.decide` logic with the F changes:
`expiresAt = min(request.expiresAt, checkpoint.expiresAt)`, no host-clock term) and `sign_decision` signs only when the proposal EQUALS that derivation field by field (rows (c) to (e) of the decision row).
The grant-existence death of an ALLOW decision is a store capability this service never needs: a request whose nonce is consumed is refused REPLAY before anything is recorded.
GrantReceipt is also a PURE FUNCTION of ledger state (SIGNING-RULES section 5): `dbcBlockNumber/Hash` is the block that CONTAINS the unique `GrantIssued` log, not "the DBC head when asked", so every honest
witness derives byte-identical receipt bytes. `derive_receipt` / `sign_receipt` follow the decision pattern (derive, compare field by field, sign). The receipt has no liveness field, so a conflicting effect for
the same request digest stays pinned; the store's `executed-receipt` death evidence is not used by this service (once the PSC records the outcome the derivation refuses anyway).
GovernanceAction comes from an operator decision, not from ledger state, so the witness validates a WHOLE proposed action (typed-field rules, nonce == governanceNonce + 1, its own witnessSetVersion, the TMSC
preconditions NOW, its LOCAL APPROVAL, and an expiry inside the PBC window `obs < e <= obs + 120`). The local approval is a TEST-ONLY allow-list of (action, root, admins) tuples injected by the runner;
a witness without one signs nothing (fail closed). That is a reconstruction choice for a specification gap (SIGNING-RULES section 3), not a discovered behaviour. The carried E `witness.py` is NOT changed (the successor adapter picks the
F service for F profiles), so E behaviour cannot move because of this module. No host clock, no randomness, no network: the only time is the observed block timestamp of the target ledger.

The injected view (what the witness reads from its own RPC):
  observe(chain)            -> {"chainId", "blockNumber", "blockHash", "timestamp"} of the LATEST block of "pbc" or "dbc" (decimal strings, 0x block hash)
  pbc_block(number)         -> {"number", "hash"} or None when the PBC has no such block
  reads_at(number)          -> {"authEpoch", "policyVersion", "witnessSetVersion"} as of that PBC block
  dbc_current_checkpoint()  -> None, or the DBC's current checkpoint (the checkpoint path reads "sequence" and "sourceBlockNumber"; the decision path reads all ten fields)
Decision path only: pbc_block(n) also carries "timestamp"; now(chain) -> int (max of latest and pending, as E: conservative for REFUSING); psc_request(digest) -> {"status", "gid", "dataId",
  "destinationChainId", "kssc", "expiresAt"}; forwarded_logs(digest) -> [{"txHash", "block"}]; forwarding_call(txHash) -> None or {"to", "method", "request", "signature", "bundle"};
  nonce_consumed(gid, nonce) -> bool; credentials(gid, bundle, at_timestamp, block) -> (code, records); policy_satisfied(dataId, records) -> bool.
Governance path only: governance_nonce() -> int; is_authority(address) -> bool; removed_authority(address) -> bool (the TMSC's tombstone); observe("pbc") is the target ledger.
Receipt path only: grant(grantId) -> {"digest", "dataId", "gid", "keyEpoch", "expiresAt", "allowed"}; grant_issued_logs(grantId) -> [{"block", "hash"}] of the KSSC's GrantIssued logs for that grant id.
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
EFFECT_RECEIPT = ("grantId", "gid", "dataId", "keyEpoch", "grantExpiresAt", "witnessSetVersion", "dbcChainId", "kssc", "dbcBlockNumber", "dbcBlockHash")
RECEIPT_FIELDS = ("requestDigest",) + EFFECT_RECEIPT
DECISION_FIELDS = ("requestDigest", "result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash", "expiresAt")
EFFECT = ("authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash")
GOV_FIELDS = ("action", "root", "admins", "nonce", "witnessSetVersion", "expiresAt")
EFFECT_GOV = ("action", "root", "admins", "witnessSetVersion")
MAX_ADMINS = 8
DEFAULT_MAX_GOV_TTL = 120
ZERO_ADDRESS = "0x" + "00" * 20
_GOV_TYPE = [{"name": "action", "type": "uint8"}, {"name": "root", "type": "address"}, {"name": "admins", "type": "address[]"}, {"name": "nonce", "type": "uint64"},
             {"name": "witnessSetVersion", "type": "uint64"}, {"name": "expiresAt", "type": "uint64"}]
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
    try:
        wire.access_decision(decision)
    except wire.WireError:
        raise _refusal("WRONG_SUBJECT", "the ledger state does not form a canonical AccessDecision (a value is out of range)") from None
    return decision, records


_RECEIPT_VALIDATORS = {"requestDigest": wire.hash32, "grantId": wire.hash32, "gid": wire.address, "dataId": wire.hash32, "keyEpoch": lambda v: wire.uint(v, 64), "grantExpiresAt": lambda v: wire.uint(v, 64),
                       "witnessSetVersion": lambda v: wire.uint(v, 64), "dbcChainId": lambda v: wire.uint(v, 256), "kssc": wire.address, "dbcBlockNumber": lambda v: wire.uint(v, 256),
                       "dbcBlockHash": wire.hash32}


def _receipt_shape(v):
    """The F receipt shape. `wire.grant_receipt` is the E validator and hard-codes keyEpoch=0 and witnessSetVersion=1, so an F receipt (version 2) cannot go through it and the carried E file is not
    changed; the field types are the same. A receipt of a ledger that grants nothing (grantExpiresAt 0) is refused as in E."""
    if not isinstance(v, dict) or set(v) != set(RECEIPT_FIELDS):
        raise wire.WireError("GrantReceipt: fields differ")
    for k, check in _RECEIPT_VALIDATORS.items():
        check(v[k])
    if int(v["grantExpiresAt"]) == 0:
        raise wire.WireError("grantExpiresAt must be positive")
    return v


def _receipt_digest(receipt, deployment):
    """The EIP-712 digest of a receipt under the HMBCReceipt domain, built from the shared type table (the E `messages.digest_of` would run the E-only validator first)."""
    typed = {"types": {"EIP712Domain": eip712.DOMAIN_TYPE, "GrantReceipt": messages.TYPES["GrantReceipt"]}, "primaryType": "GrantReceipt",
             "domain": messages.domain_for("GrantReceipt", receipt, deployment), "message": receipt}
    return eip712.digest(typed)


def derive_receipt(view, deployment, grant_id, *, witness_set_version):
    """The receipt this witness would sign for `grant_id`, derived from its own reads. Raises WitnessRefusal with the E classes."""
    try:
        return _derive_receipt(view, deployment, grant_id, witness_set_version)
    except LedgerUnreachable as e:
        raise _unreachable(e) from None


def _derive_receipt(view, deployment, grant_id, wsv):
    try:
        wire.hash32(grant_id)
    except (wire.WireError, TypeError):
        raise _refusal("MALFORMED", "the grant id is not a canonical 32-byte hash") from None
    dbc = deployment["chains"]["dbc"]
    kssc = dbc["contracts"]["KSSC"]
    head = view.observe("dbc")
    g = view.grant(grant_id)
    if not g["allowed"] or "0x" + eip712.grant_id(bytes.fromhex(g["digest"][2:]), kssc, int(dbc["chainId"])).hex() != grant_id:
        raise _refusal("NOT_COMMITTED", "no allowed grant with this id exists on the DBC")
    logs = [x for x in view.grant_issued_logs(grant_id) if int(x["block"]) <= int(head["blockNumber"])]
    if not logs:
        raise _refusal("NOT_COMMITTED", "this witness has not seen the block that contains the GrantIssued log")
    if len(logs) != 1:
        raise _refusal("WRONG_SUBJECT", "expected exactly one GrantIssued log for this grant id")
    rec = view.psc_request(g["digest"])
    if rec["status"] != "1" or (rec["gid"], rec["dataId"]) != (g["gid"], g["dataId"]):
        raise _refusal("WRONG_SUBJECT", "the PBC record does not match the DBC grant")
    receipt = {"requestDigest": g["digest"], "grantId": grant_id, "gid": g["gid"], "dataId": g["dataId"], "keyEpoch": g["keyEpoch"], "grantExpiresAt": g["expiresAt"], "witnessSetVersion": wsv,
               "dbcChainId": dbc["chainId"], "kssc": kssc, "dbcBlockNumber": str(int(logs[0]["block"])), "dbcBlockHash": logs[0]["hash"]}
    try:
        _receipt_shape(receipt)
    except wire.WireError:
        raise _refusal("WRONG_SUBJECT", "the ledger state does not form a canonical GrantReceipt (a value is out of range)") from None
    return receipt


def _governance_domain(deployment):
    """HMBCGovernance / 1 / PBC chainId / Governance address, or None when the deployment has no Governance contract (an E profile)."""
    pbc = deployment["chains"]["pbc"]
    gov = pbc["contracts"].get("Governance")
    return None if gov is None else {"name": "HMBCGovernance", "version": "1", "chainId": pbc["chainId"], "verifyingContract": gov}


def _governance_digest(message, deployment):
    typed = {"types": {"EIP712Domain": eip712.DOMAIN_TYPE, "GovernanceAction": _GOV_TYPE}, "primaryType": "GovernanceAction", "domain": _governance_domain(deployment), "message": message}
    return eip712.digest(typed)


def _governance_shape(v):
    """The typed-field rules (A1 section 2): action in {1,2,3}; root non-zero; admins a list of non-zero lowercase addresses, strictly ascending, at most MAX_ADMINS; ADD needs 1..MAX_ADMINS admins, REMOVE
    none, SET 0..MAX_ADMINS; integers canonical decimal strings within their widths."""
    if not isinstance(v, dict) or set(v) != set(GOV_FIELDS):
        raise wire.WireError("GovernanceAction: fields differ")
    wire.uint(v["action"], 8)
    wire.address(v["root"])
    wire.uint(v["nonce"], 64)
    wire.uint(v["witnessSetVersion"], 64)
    wire.uint(v["expiresAt"], 64)
    admins = v["admins"]
    if v["action"] not in ("1", "2", "3") or v["root"] == ZERO_ADDRESS or not isinstance(admins, list) or len(admins) > MAX_ADMINS:
        raise wire.WireError("GovernanceAction: action, root or admins out of range")
    for a in admins:
        wire.address(a)
    if any(a == ZERO_ADDRESS for a in admins) or any(x >= y for x, y in zip(admins, admins[1:])):
        raise wire.WireError("GovernanceAction: admins must be non-zero and strictly ascending")
    if (v["action"] == "1" and not admins) or (v["action"] == "2" and admins):
        raise wire.WireError("GovernanceAction: ADD needs admins, REMOVE allows none")
    return v


class WitnessService:
    def __init__(self, *, store, key, view, deployment, witness_set_version, max_checkpoint_ttl=DEFAULT_MAX_TTL, max_governance_ttl=DEFAULT_MAX_GOV_TTL, allowed_governance=None):
        if not isinstance(max_checkpoint_ttl, int) or isinstance(max_checkpoint_ttl, bool) or max_checkpoint_ttl < 1:
            raise ValueError("max_checkpoint_ttl must be a positive integer")
        if not isinstance(max_governance_ttl, int) or isinstance(max_governance_ttl, bool) or max_governance_ttl < 1:
            raise ValueError("max_governance_ttl must be a positive integer")
        self._max_gov_ttl = max_governance_ttl
        # TEST-ONLY local approval: a snapshot of (action, root, admins) tuples; None signs nothing
        self._allow = None if allowed_governance is None else frozenset((a, r, tuple(ad)) for a, r, ad in allowed_governance)
        self._store, self._key, self._view, self._max_ttl = store, key, view, max_checkpoint_ttl
        self.address = Account.from_key(key).address.lower()
        self._wsv = witness_set_version
        pbc = deployment["chains"]["pbc"]
        self._pbc_id, self._psc = pbc["chainId"], pbc["contracts"]["PSC"]
        self._domain = "0x" + eip712.domain_separator(messages.domain_for("StateCheckpoint", {}, deployment)).hex()
        self._decision_domain = "0x" + eip712.domain_separator(messages.domain_for("AccessDecision", {}, deployment)).hex()
        self._receipt_domain = "0x" + eip712.domain_separator(messages.domain_for("GrantReceipt", {}, deployment)).hex()
        gdom = _governance_domain(deployment)
        self._governance_sep = None if gdom is None else "0x" + eip712.domain_separator(gdom).hex()
        self._deployment = deployment

    # ---- the F signing rule for a checkpoint ------------------------------------------------------------------------------------------------------------------------
    def sign_checkpoint(self, proposal):
        return self._guarded(lambda: self._sign_checkpoint(proposal))

    def sign_decision(self, proposal):
        return self._guarded(lambda: self._sign_decision(proposal))

    def sign_receipt(self, proposal):
        return self._guarded(lambda: self._sign_receipt(proposal))

    def sign_governance(self, proposal):
        return self._guarded(lambda: self._sign_governance(proposal))

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

    def _sign_receipt(self, proposal):
        try:
            prop = dict(_receipt_shape(proposal))
        except (wire.WireError, TypeError):
            raise _refusal("MALFORMED", "the proposal is not a canonical GrantReceipt") from None
        own = _derive_receipt(self._view, self._deployment, prop["grantId"], self._wsv)
        for f in RECEIPT_FIELDS:
            if prop[f] != own[f]:
                raise _mismatch(f, "differs from this witness's own derivation")
        digest = _receipt_digest(own, self._deployment)
        return self._store.sign(type="GrantReceipt", domain=self._receipt_domain, wsv=own["witnessSetVersion"], key=own["requestDigest"], effect={k: own[k] for k in EFFECT_RECEIPT},
                                expires_at=None, digest="0x" + digest.hex(), signer=self._signer, observe=lambda: self._view.observe("pbc"))

    def _sign_governance(self, proposal):
        if self._governance_sep is None:
            raise _refusal("WRONG_PROFILE", "this deployment has no Governance contract (governance exists only in repaired-f)")
        try:
            g = dict(_governance_shape(proposal))
        except (wire.WireError, TypeError):
            raise _refusal("MALFORMED", "the proposal is not a canonical GovernanceAction") from None
        view = self._view
        current = int(view.governance_nonce())
        if int(g["nonce"]) != current + 1:
            raise _mismatch("nonce", f"the next governance nonce is {current + 1}")
        if g["witnessSetVersion"] != self._wsv:
            raise WitnessRefusal("STALE_STATE", "WITNESS_SET_MISMATCH", "witnessSetVersion differs from this witness's own")
        root = g["root"]
        if g["action"] == "1":
            if view.is_authority(root):
                raise _refusal("ALREADY_REGISTERED", "ADD of a root that is already an authority would revert at the TMSC")
            if view.removed_authority(root):
                raise _refusal("REVOKED", "ADD of a tombstoned root would revert at the TMSC")
        elif not view.is_authority(root):
            raise _refusal("NOT_REGISTERED", "REMOVE or SET of a root that is not an authority would revert at the TMSC")
        if self._allow is None or (g["action"], root, tuple(g["admins"])) not in self._allow:
            raise _refusal("POLICY_DENIED", "this witness's local allow-list does not approve this action")
        ts = int(view.observe("pbc")["timestamp"])
        e = int(g["expiresAt"])
        if e <= ts:
            raise _refusal("EXPIRED", "expiresAt is not after the PBC's latest block timestamp")
        if e > ts + self._max_gov_ttl:
            raise _mismatch("expiresAt", f"is more than {self._max_gov_ttl} s after the PBC's latest block timestamp")
        digest = _governance_digest(g, self._deployment)
        return self._store.sign(type="GovernanceAction", domain=self._governance_sep, wsv=g["witnessSetVersion"], key=g["nonce"], effect={k: g[k] for k in EFFECT_GOV}, expires_at=g["expiresAt"],
                                digest="0x" + digest.hex(), signer=self._signer, observe=lambda: self._view.observe("pbc"), overtaken=("overtaken-governance", str(current)))

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
