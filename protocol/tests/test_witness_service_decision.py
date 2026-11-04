"""Witness service, AccessDecision path (agent 2, F task 2, slice 4b). Written BEFORE `sign_decision` and `derive_decision` existed in hmbc_protocol/witness_service.py.

A decision is a PURE FUNCTION of the request and the DBC's current checkpoint (SIGNING-RULES section 3 AccessDecision row and section 4), so the F witness does not validate a free proposal: it DERIVES its own
decision from its own ledger view (`derive_decision`: the E `witness.decide` logic ported to an injected view, with the F changes: `expiresAt = min(request.expiresAt, checkpoint.expiresAt)` and no
host-clock term) and signs only when the proposal EQUALS its derivation field by field (row (d): `stateSequence`, `sourceBlockNumber`, `sourceBlockHash` are the DBC's current checkpoint's; row (e): the
deterministic expiry; row (c): `result` and `credentialDigest` are the witness's own evaluation). The pool uses the same function to build the proposal; independence is across witnesses' separate views.

Same discipline as slice 4a: real store, real EIP-712 digests and signatures (synthetic key), an INJECTED fake ledger view, no ledger. The credential evaluation (`credentials`, `policy_satisfied`) is a
fake: the real TMSC/ACSC evaluation is the ledger's, not tested here. The E refusal classes (REPLAY, WRONG_SUBJECT, STALE_STATE, WRONG_EPOCH, WRONG_DESTINATION, EXPIRED) are kept as E had them; a proposal that
differs from the witness's derivation is STALE_STATE with reason PROPOSAL_MISMATCH naming the field (an explicit choice).
"""
import copy
import json

import pytest

from hmbc_protocol import eip712, messages
from hmbc_protocol import witness_service as svc
from hmbc_protocol import witness_state as ws

from test_witness_service import (B, BIND, DBC_ID, DEPLOY, KEY, ADDR, OWNER, PBC_ID, PSC, FakeView, h, refusal, snapshot)

KSSC = DEPLOY["chains"]["dbc"]["contracts"]["KSSC"]
GID = "0x" + "c1" * 20
DATA_ID = "0x" + "d1" * 32
RECIPIENT = "0x" + "e1" * 32
RECORD = {"issuer": "0x" + "aa" * 20, "role": "0x" + "bb" * 32, "kind": "1", "serial": "5", "anchorVersion": "1", "validUntil": "5000"}


class DView(FakeView):
    """A fake with one forwarded request, one DBC checkpoint and a scripted credential evaluation."""

    def __init__(self):
        super().__init__()
        self.dbc_ts = 1000
        self.request = {"sourceChainId": PBC_ID, "destinationChainId": DBC_ID, "psc": PSC, "kssc": KSSC, "gid": GID, "dataId": DATA_ID, "action": "1", "policyVersion": "1", "authEpoch": "3",
                        "keyEpoch": "0", "nonce": "7", "expiresAt": "1020", "recipientKeyHash": RECIPIENT}
        self.cp = {"sequence": "4", "authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": PBC_ID, "psc": PSC, "sourceBlockNumber": "200",
                   "sourceBlockHash": h("pbc:200"), "expiresAt": "1040"}
        self.current = self.cp
        self.forwarded_block = 150
        self.status = "1"
        self.logs = 1
        self.tx_to, self.tx_method = PSC, "requestAccess"
        self.consumed = False
        self.cred_code, self.records, self.satisfied = "0", [dict(RECORD)], True
        self.pbc_now_extra = 0
        self.rec_override = {}
        self.pbc_head = 250

    def digest(self):
        return "0x" + messages.digest_of("AccessRequest", self.request, messages.domain_for("AccessRequest", self.request, DEPLOY)).hex()

    def psc_request(self, digest):
        self._maybe_fail("psc_request")
        rec = {"status": self.status, "gid": self.request["gid"], "dataId": self.request["dataId"], "destinationChainId": self.request["destinationChainId"], "kssc": self.request["kssc"],
               "expiresAt": self.request["expiresAt"]}
        rec.update(self.rec_override)
        return rec

    def forwarded_logs(self, digest):
        self._maybe_fail("forwarded_logs")
        return [{"txHash": h("tx%d" % i), "block": self.forwarded_block} for i in range(self.logs)]

    def forwarding_call(self, tx_hash):
        self._maybe_fail("forwarding_call")
        return {"to": self.tx_to, "method": self.tx_method, "request": copy.deepcopy(self.request), "signature": "0x" + "00" * 65, "bundle": {"claims": []}}

    def dbc_current_checkpoint(self):
        self._maybe_fail("dbc_current_checkpoint")
        return None if self.current is None else dict(self.current)

    def now(self, chain):
        self._maybe_fail("now:" + chain)
        return self.dbc_ts if chain == "dbc" else self.dbc_ts + self.pbc_now_extra               # one clock domain for the fake; the PBC may run ahead by `pbc_now_extra`

    def nonce_consumed(self, gid, nonce):
        self._maybe_fail("nonce_consumed")
        return self.consumed

    def credentials(self, gid, bundle, at_timestamp, block):
        self._maybe_fail("credentials")
        self.last_credentials_call = (gid, at_timestamp, block)
        return self.cred_code, copy.deepcopy(self.records)

    def policy_satisfied(self, data_id, records):
        self._maybe_fail("policy_satisfied")
        return self.satisfied


@pytest.fixture
def view():
    return DView()


@pytest.fixture
def store(tmp_path):
    return ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER)


@pytest.fixture
def service(store, view):
    return svc.WitnessService(store=store, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")


def derive(view):
    return svc.derive_decision(view, DEPLOY, view.digest(), witness_set_version="2")


def digest_of(decision):
    return messages.digest_of("AccessDecision", decision, messages.domain_for("AccessDecision", decision, DEPLOY))


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# derivation
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_derived_decision_is_a_pure_function_of_the_request_and_the_current_checkpoint(view):
    decision, records = derive(view)
    assert decision == {"requestDigest": view.digest(), "result": "1", "credentialDigest": "0x" + eip712.credential_digest(view.records).hex(), "stateSequence": "4", "witnessSetVersion": "2",
                        "sourceBlockNumber": "200", "sourceBlockHash": h("pbc:200"), "expiresAt": "1020"}
    assert records == view.records


def test_the_expiry_is_the_minimum_of_the_request_and_the_checkpoint_and_ignores_the_witnesss_clock(view):
    assert derive(view)[0]["expiresAt"] == "1020"
    view.request["expiresAt"] = "1030"
    view.cp = view.current = dict(view.cp, expiresAt="1025")
    assert derive(view)[0]["expiresAt"] == "1025"
    for ts in (1000, 1005, 1010):                                                              # the E term dbc_now + 30 is gone: nothing here depends on how late the witness is asked
        view.dbc_ts = ts
        assert derive(view)[0]["expiresAt"] == "1025"


def test_the_evaluation_is_made_at_the_checkpoints_block_with_that_blocks_own_timestamp(view):
    derive(view)
    gid, at, block = view.last_credentials_call
    assert (gid, at, block) == (GID, str(view.pbc_ts_base + 200), 200)


def test_a_policy_that_is_not_satisfied_or_credentials_that_fail_give_a_signed_deny(view):
    view.satisfied = False
    assert derive(view)[0]["result"] == "0"
    view.satisfied, view.cred_code = True, "3"
    d, recs = derive(view)
    assert d["result"] == "0" and d["credentialDigest"] == "0x" + eip712.credential_digest(recs).hex()


def test_a_credential_that_lapsed_since_the_checkpoint_is_attested_as_none_and_denied(view):
    view.records = [dict(RECORD, validUntil="1000")]                                           # valid until exactly the DBC's now: DecisionVerifier would revert EXPIRED on it
    d, recs = derive(view)
    assert d["result"] == "0" and recs == [] and d["credentialDigest"] == "0x" + eip712.credential_digest([]).hex()
    view.records = [dict(RECORD, validUntil="1001")]
    assert derive(view)[0]["result"] == "1"


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the signature and the record
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_matching_proposal_is_signed_and_recorded_under_the_request_digest(service, view, store):
    decision, _ = derive(view)
    sig = service.sign_decision(decision)
    assert eip712.recover(digest_of(decision), sig) == ADDR
    ev = store.evidence()
    c = ev["conflicts"][0]
    assert c["type"] == "AccessDecision" and c["keyField"] == view.digest() and c["domainSeparator"] == "0x" + eip712.domain_separator(messages.domain_for("AccessDecision", decision, DEPLOY)).hex()
    assert set(c["effect"]) == {"result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash"} and c["digests"][0]["signature"] == sig
    assert ev["observations"][0]["chainId"] == DBC_ID                                          # the target ledger of a decision is the DBC
    assert service.sign_decision(decision) == sig and snapshot(store) == snapshot(store)


@pytest.mark.parametrize("field,alt", [("requestDigest", "0x" + "ab" * 32), ("result", "0"), ("credentialDigest", "0x" + "cd" * 32), ("stateSequence", "5"), ("witnessSetVersion", "3"),
                                       ("sourceBlockNumber", "201"), ("sourceBlockHash", "0x" + "ef" * 32), ("expiresAt", "1019"), ("expiresAt", "1021"), ("expiresAt", "1040")])
def test_a_proposal_that_differs_from_the_witnesss_own_derivation_in_any_field_is_refused(service, view, store, field, alt):
    decision, _ = derive(view)
    bad = dict(decision, **{field: alt})
    before = snapshot(store)
    r = refusal(lambda: service.sign_decision(bad))
    assert r is not None and r.code in ("STALE_STATE", "WRONG_SUBJECT", "MALFORMED") and snapshot(store) == before
    if field != "requestDigest":
        assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and field in r.message


@pytest.mark.parametrize("bad", [None, [], "x", {}, {"requestDigest": "0x" + "00" * 32}], ids=["none", "list", "str", "empty", "partial"])
def test_a_proposal_of_the_wrong_shape_is_malformed(service, view, store, bad):
    before = snapshot(store)
    r = refusal(lambda: service.sign_decision(bad))
    assert (r.code, r.reason) == ("MALFORMED", None) and snapshot(store) == before


def test_a_request_forwarded_in_the_checkpoints_own_block_is_accepted(service, view):
    view.forwarded_block = 200                                                                   # forwardedAt <= sourceBlockNumber: equality is allowed
    assert service.sign_decision(derive(view)[0])
    view.forwarded_block = 201
    assert refusal(lambda: svc.derive_decision(view, DEPLOY, view.digest(), witness_set_version="2")).code == "STALE_STATE"


def test_the_proposer_side_derivation_maps_an_unreadable_view_too(view):
    view.fail = "psc_request"
    r = refusal(lambda: svc.derive_decision(view, DEPLOY, view.digest(), witness_set_version="2"))
    assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE")


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# refusals of the derivation (E classes)
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def _rec(**kw):
    return lambda v: v.rec_override.update(kw)


REFUSALS = [
    ("an outcome is already recorded", lambda v: setattr(v, "status", "2"), "REPLAY"),
    ("the PSC has not forwarded the digest", lambda v: setattr(v, "status", "0"), "WRONG_SUBJECT"),
    ("no forwarding log", lambda v: setattr(v, "logs", 0), "WRONG_SUBJECT"),
    ("two forwarding logs", lambda v: setattr(v, "logs", 2), "WRONG_SUBJECT"),
    ("the forwarding transaction was not sent to the PSC", lambda v: setattr(v, "tx_to", "0x" + "99" * 20), "WRONG_SUBJECT"),
    ("the forwarding call is not requestAccess", lambda v: setattr(v, "tx_method", "multicall"), "WRONG_SUBJECT"),
    ("the PSC record's gid differs", _rec(gid="0x" + "01" * 20), "WRONG_SUBJECT"),
    ("the PSC record's dataId differs", _rec(dataId="0x" + "02" * 32), "WRONG_SUBJECT"),
    ("the PSC record's destination differs", _rec(destinationChainId="1"), "WRONG_SUBJECT"),
    ("the PSC record's kssc differs", _rec(kssc="0x" + "03" * 20), "WRONG_SUBJECT"),
    ("the PSC record's expiry differs", _rec(expiresAt="1"), "WRONG_SUBJECT"),
    ("no DBC checkpoint", lambda v: setattr(v, "current", None), "STALE_STATE"),
    ("the DBC checkpoint expired", lambda v: setattr(v, "dbc_ts", 1040), "STALE_STATE"),
    ("the checkpoint names another block hash", lambda v: setattr(v, "current", dict(v.cp, sourceBlockHash=h("forged"))), "STALE_STATE"),
    ("the checkpoint's authEpoch differs from the block's", lambda v: setattr(v, "current", dict(v.cp, authEpoch="9")), "STALE_STATE"),
    ("the request was forwarded after the checkpoint's block", lambda v: setattr(v, "forwarded_block", 201), "STALE_STATE"),
    ("the request's authEpoch differs from the checkpoint's", lambda v: v.request.update(authEpoch="2"), "STALE_STATE"),
    ("the request's policyVersion differs from the checkpoint's", lambda v: v.request.update(policyVersion="2"), "STALE_STATE"),
    ("the request's keyEpoch differs from the checkpoint's", lambda v: v.request.update(keyEpoch="1"), "WRONG_EPOCH"),
    ("another destination chain", lambda v: v.request.update(destinationChainId="1"), "WRONG_DESTINATION"),
    ("another KSSC", lambda v: v.request.update(kssc="0x" + "04" * 20), "WRONG_DESTINATION"),
    ("the nonce is already consumed", lambda v: setattr(v, "consumed", True), "REPLAY"),
    ("the request expired on the DBC clock", lambda v: setattr(v, "dbc_ts", 1020), "EXPIRED"),
    ("the request expired on the PBC clock", lambda v: setattr(v, "pbc_now_extra", 10_000), "EXPIRED"),
    ("the checkpoint's witnessSetVersion is not this witness's", lambda v: setattr(v, "current", dict(v.cp, witnessSetVersion="3")), "STALE_STATE"),
]


@pytest.mark.parametrize("name,mutate,code", REFUSALS, ids=[r[0] for r in REFUSALS])
def test_each_failing_condition_refuses_with_the_e_class_and_writes_nothing(service, view, store, name, mutate, code):
    mutate(view)
    digest = view.digest()                                                                       # the digest of the (possibly altered) request: its fields are part of what is hashed
    before = snapshot(store)
    d = {"requestDigest": digest, "result": "1", "credentialDigest": "0x" + "00" * 32, "stateSequence": "4", "witnessSetVersion": "2", "sourceBlockNumber": "200", "sourceBlockHash": h("pbc:200"), "expiresAt": "1020"}
    r = refusal(lambda: svc.derive_decision(view, DEPLOY, digest, witness_set_version="2"))
    assert r is not None and r.code == code, (name, getattr(r, "code", None))
    r2 = refusal(lambda: service.sign_decision(d))
    assert r2 is not None and r2.code == code and snapshot(store) == before


def test_a_request_that_does_not_hash_to_the_requested_digest_is_wrong_subject(service, view, store):
    digest = view.digest()
    view.request["nonce"] = "8"                                                                  # the log/calldata now carries another request than the digest names
    r = refusal(lambda: svc.derive_decision(view, DEPLOY, digest, witness_set_version="2"))
    assert (r.code, r.reason) == ("WRONG_SUBJECT", None)


def test_a_checkpoint_value_out_of_range_gives_a_refusal_not_a_raw_exception(view):
    view.cp = view.current = dict(view.cp, sequence="18446744073709551616")                      # 2**64: not a uint64
    r = refusal(lambda: svc.derive_decision(view, DEPLOY, view.digest(), witness_set_version="2"))
    assert (r.code, r.reason) == ("WRONG_SUBJECT", None) and "canonical AccessDecision" in r.message


def test_a_malformed_request_digest_is_malformed(view):
    for bad in ("0x12", "0X" + "AB" * 32, 5, None, "0x" + "AB" * 32):
        r = refusal(lambda: svc.derive_decision(view, DEPLOY, bad, witness_set_version="2"))
        assert (r.code, r.reason) == ("MALFORMED", None), bad


def test_an_unreadable_view_refuses_with_ledger_unreachable_and_writes_nothing(service, view, store):
    decision, _ = derive(view)
    for name in ("psc_request", "forwarded_logs", "forwarding_call", "dbc_current_checkpoint", "now:dbc", "now:pbc", "nonce_consumed", "credentials", "policy_satisfied", "pbc_block", "reads_at"):
        view.fail = name
        before = snapshot(store)
        r = refusal(lambda: service.sign_decision(decision))
        assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE"), name
        assert snapshot(store) == before, name
    view.fail = None
    assert service.sign_decision(decision)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the durable rule through the decision path
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_changed_evaluation_for_the_same_checkpoint_is_pinned_until_the_old_decision_is_dead(service, view, store):
    first, _ = derive(view)
    service.sign_decision(first)                                                                 # ALLOW recorded for this request digest
    view.satisfied = False                                                                       # the same request now evaluates to DENY at the same checkpoint
    deny, _ = derive(view)
    assert deny["result"] == "0" and deny["stateSequence"] == first["stateSequence"]
    r = refusal(lambda: service.sign_decision(deny))
    assert (r.code, r.reason) == ("STALE_STATE", "CONFLICT_PINNED") and r.recorded is None      # a recorded value exists only for checkpoints
    assert [c["effect"]["result"] for c in store.evidence()["conflicts"]] == ["1"]


def test_a_new_checkpoint_kills_the_old_decision_by_the_state_predicate_and_allows_the_new_one(service, view, store):
    first, _ = derive(view)
    service.sign_decision(first)
    view.cp = view.current = dict(view.cp, sequence="5", sourceBlockNumber="210", sourceBlockHash=h("pbc:210"), expiresAt="1045")
    second, _ = derive(view)
    assert second["stateSequence"] == "5" and second["sourceBlockNumber"] == "210"
    sig = service.sign_decision(second)
    assert eip712.recover(digest_of(second), sig) == ADDR
    ev = store.evidence()
    assert len(ev["superseded"]) == 1 and ev["superseded"][0]["effect"]["stateSequence"] == "4"
    assert ev["superseded"][0]["death"]["kind"] == "overtaken-decision-sequence" and ev["superseded"][0]["death"]["observed"] == "5"


def test_the_same_decision_renewed_by_nothing_cannot_be_extended_a_decision_expiry_is_deterministic(service, view, store):
    first, _ = derive(view)
    service.sign_decision(first)
    view.dbc_ts = 1010
    again, _ = derive(view)
    assert again == first                                                                        # a later request for the same state yields the same digest, not a longer one


def test_decision_proposals_property_only_the_witnesss_own_derivation_is_signed(tmp_path, view):
    """Every single-field alteration of the derived decision, over several values each, is refused; the unaltered decision is signed. A fresh store per case."""
    own, _ = derive(view)
    alts = {"requestDigest": ["0x" + "00" * 32, "0x" + "11" * 32], "result": ["0", "2"], "credentialDigest": ["0x" + "00" * 32, own["requestDigest"]],
            "stateSequence": ["0", "3", "5", "18446744073709551615"], "witnessSetVersion": ["0", "1", "3"], "sourceBlockNumber": ["0", "199", "201", "250"],
            "sourceBlockHash": ["0x" + "00" * 32, h("pbc:201")], "expiresAt": ["0", "1000", "1019", "1021", "1039", "1040", "99999"]}
    n = signed = 0
    for field in [None] + list(alts):
        for v in ([None] if field is None else alts[field]):
            st = ws.init_store(str(tmp_path / ("s%d" % n)), BIND, B, OWNER)
            sv = svc.WitnessService(store=st, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")
            prop = dict(own) if field is None else dict(own, **{field: v})
            try:
                sig = sv.sign_decision(prop)
                got = True
            except svc.WitnessRefusal:
                got = False
            assert got == (field is None), (field, v)
            signed += got
            n += 1
    assert signed == 1 and n > 25
