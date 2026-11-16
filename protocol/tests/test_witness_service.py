"""Witness service, StateCheckpoint path (agent 2, F task 2, slice 4a). Written BEFORE hmbc_protocol/witness_service.py existed.

`witness_service.WitnessService.sign_checkpoint(proposal)` is the F-profile honest witness for ONE type: it treats the proposal only as a candidate, recomputes every field from its OWN view of the
ledgers (SIGNING-RULES section 3, StateCheckpoint row (a)-(f)), and only then asks the durable store (slice 1) to record the choice and return the signature (section 2). `derive_checkpoint` is the
PROPOSER side (the pool/adapter derives the proposal once from its own reads). The ledger is an INJECTED view; the store is the real one; the signatures are real EIP-712 over the production digest
with a synthetic public key. NOT a real ledger, NOT the pool, NOT the other three types (decision, receipt, governance are later slices) and not the D50 live reads.

Explicit choices where F0 does not fix the refusal class (recorded, not discovered). Order: shape (MALFORMED), destination (WRONG_DESTINATION: it needs no read), then rows (a) to (f). A wrong sequence,
a block the witness cannot confirm, a snapshot that disagrees with its own reads, a stale view and an expiry above the window are STALE_STATE with reason PROPOSAL_MISMATCH (the message names the field);
a `keyEpoch` other than 0 is WRONG_EPOCH (as E's decision check); a different `witnessSetVersion` is STALE_STATE with WITNESS_SET_MISMATCH; an expiry at or before the observation is EXPIRED; a view
that cannot be read is ADAPTER_UNAVAILABLE with LEDGER_UNREACHABLE; the store's own refusals pass through (CONFLICT_PINNED with the recorded value, WITNESS_FAULTED).
"""
import ast
import copy
import hashlib
import json
import os

import pytest

from eth_account import Account

from hmbc_protocol import eip712, keys, messages
from hmbc_protocol import witness_service as svc
from hmbc_protocol import witness_state as ws
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")
_spec = importlib.util.spec_from_file_location("d50_reference", os.path.join(V, "d50_reference.py"))
d50 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d50)
B = d50.synthetic_binding_document("repaired-f")
BIND = d50.binding_v2(B)
DEPLOY = json.load(open(os.path.join(ROOT, "protocol", "tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json")))
PBC_ID, DBC_ID = DEPLOY["chains"]["pbc"]["chainId"], DEPLOY["chains"]["dbc"]["chainId"]
PSC = DEPLOY["chains"]["pbc"]["contracts"]["PSC"]
KEY = keys.synthetic_private_key("witness-1")
ADDR = Account.from_key(KEY).address.lower()
OWNER = "witness:" + ADDR
assert B["chains"]["pbc"]["chainId"] == PBC_ID and B["chains"]["dbc"]["chainId"] == DBC_ID


def h(label):
    return "0x" + hashlib.sha256(label.encode()).hexdigest()


class FakeView:
    """The witness's own RPC view, injected. `fail` names a method that raises LedgerUnreachable."""

    def __init__(self):
        self.pbc_head = 250
        self.dbc_number, self.dbc_ts = 90, 1000
        self.pbc_ts_base = 5000
        self.reads = {}                       # block number -> {"authEpoch", "policyVersion", "witnessSetVersion"}; default below
        self.hash_override = {}               # block number -> hash the view reports
        self.current = None                   # DBC current checkpoint: {"sequence", "sourceBlockNumber"} or None
        self.fail = None
        self.calls = []
        self.lenient = False                  # a view whose block read succeeds beyond its own observed head (a race between two reads)

    def _maybe_fail(self, name):
        self.calls.append(name)
        if self.fail == name:
            raise svc.LedgerUnreachable(name)

    def pbc_hash(self, n):
        return self.hash_override.get(n, h("pbc:%d" % n))

    def observe(self, chain):
        self._maybe_fail("observe:" + chain)
        if chain == "pbc":
            return {"chainId": PBC_ID, "blockNumber": str(self.pbc_head), "blockHash": self.pbc_hash(self.pbc_head), "timestamp": str(self.pbc_ts_base + self.pbc_head)}
        return {"chainId": DBC_ID, "blockNumber": str(self.dbc_number), "blockHash": h("dbc:%d" % self.dbc_number), "timestamp": str(self.dbc_ts)}

    def pbc_block(self, number):
        self._maybe_fail("pbc_block")
        number = int(number)
        return None if (number > self.pbc_head and not self.lenient) or number < 0 else {"number": str(number), "hash": self.pbc_hash(number), "timestamp": str(self.pbc_ts_base + number)}

    def reads_at(self, number):
        self._maybe_fail("reads_at")
        return dict(self.reads.get(int(number), {"authEpoch": "3", "policyVersion": "1", "witnessSetVersion": "2"}))

    def dbc_current_checkpoint(self):
        self._maybe_fail("dbc_current_checkpoint")
        return None if self.current is None else dict(self.current)


@pytest.fixture
def view():
    return FakeView()


@pytest.fixture
def store(tmp_path):
    return ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER)


@pytest.fixture
def service(store, view):
    return svc.WitnessService(store=store, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")


def digest_of(cp):
    return messages.digest_of("StateCheckpoint", cp, messages.domain_for("StateCheckpoint", cp, DEPLOY))


def refusal(fn):
    try:
        fn()
    except svc.WitnessRefusal as e:
        return e
    return None


def snapshot(store):
    return json.dumps(store.evidence(), sort_keys=True)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the proposer side
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_proposer_derives_every_field_from_its_own_reads(view):
    cp = svc.derive_checkpoint(view, DEPLOY)
    assert cp == {"sequence": "1", "authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": PBC_ID, "psc": PSC,
                  "sourceBlockNumber": "250", "sourceBlockHash": h("pbc:250"), "expiresAt": "1030"}
    view.reads[250] = {"authEpoch": "5", "policyVersion": "4", "witnessSetVersion": "2"}                  # the epochs come from the head block, not from a default or another block
    assert (svc.derive_checkpoint(view, DEPLOY)["authEpoch"], svc.derive_checkpoint(view, DEPLOY)["policyVersion"]) == ("5", "4")
    view.reads[250] = {"authEpoch": "3", "policyVersion": "1", "witnessSetVersion": "2"}
    view.current, view.dbc_ts = {"sequence": "7", "sourceBlockNumber": "240"}, 2000
    assert svc.derive_checkpoint(view, DEPLOY)["sequence"] == "8" and svc.derive_checkpoint(view, DEPLOY)["expiresAt"] == "2030"
    assert svc.derive_checkpoint(view, DEPLOY, ttl=45)["expiresAt"] == "2045"


def test_a_derived_proposal_validates_and_signs(service, view, store):
    cp = svc.derive_checkpoint(view, DEPLOY)
    sig = service.sign_checkpoint(cp)
    assert eip712.recover(digest_of(cp), sig) == ADDR == service.address
    ev = store.evidence()
    assert len(ev["conflicts"]) == 1 and ev["conflicts"][0]["type"] == "StateCheckpoint" and ev["conflicts"][0]["keyField"] == "1"
    assert ev["conflicts"][0]["domainSeparator"] == "0x" + eip712.domain_separator(messages.domain_for("StateCheckpoint", cp, DEPLOY)).hex() and ev["conflicts"][0]["witnessSetVersion"] == "2"
    assert ev["conflicts"][0]["digests"][0]["signature"] == sig and ev["observations"][0]["chainId"] == DBC_ID and ev["observations"][0]["timestamp"] == "1000"


def test_signing_is_idempotent_and_a_renewal_with_the_same_effect_signs_a_new_digest(service, view, store):
    cp = svc.derive_checkpoint(view, DEPLOY)
    first = service.sign_checkpoint(cp)
    assert service.sign_checkpoint(cp) == first
    before = snapshot(store)
    assert service.sign_checkpoint(cp) == first and snapshot(store) == before                  # a repeat writes nothing
    view.dbc_ts = 1010
    renewed = dict(cp, expiresAt="1040")                                                        # same effect, later expiry, inside the window of the new observation
    sig2 = service.sign_checkpoint(renewed)
    assert sig2 != first and eip712.recover(digest_of(renewed), sig2) == ADDR
    assert len(store.evidence()["conflicts"][0]["digests"]) == 2


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# refusals: the class and reason of each failing row, and the store untouched
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def prop(view, **over):
    cp = svc.derive_checkpoint(view, DEPLOY)
    cp.update(over)
    return cp


CASES = [
    # name, mutate(view) before deriving, override of proposal fields, expected (code, reason)
    ("sequence too high", None, dict(sequence="2"), ("STALE_STATE", "PROPOSAL_MISMATCH")),
    ("sequence zero", None, dict(sequence="0"), ("STALE_STATE", "PROPOSAL_MISMATCH")),
    ("wrong source chain", None, dict(sourceChainId="999"), ("WRONG_DESTINATION", None)),
    ("wrong psc", None, dict(psc="0x" + "99" * 20), ("WRONG_DESTINATION", None)),
    ("block after the witness's own head", None, dict(sourceBlockNumber="251", sourceBlockHash=h("pbc:251")), ("STALE_STATE", "PROPOSAL_MISMATCH")),
    ("block hash differs", None, dict(sourceBlockHash=h("forged")), ("STALE_STATE", "PROPOSAL_MISMATCH")),
    ("keyEpoch not zero", None, dict(keyEpoch="1"), ("WRONG_EPOCH", None)),
    ("authEpoch differs from the witness's read", None, dict(authEpoch="4"), ("STALE_STATE", "PROPOSAL_MISMATCH")),
    ("policyVersion differs from the witness's read", None, dict(policyVersion="2"), ("STALE_STATE", "PROPOSAL_MISMATCH")),
    ("witnessSetVersion differs", None, dict(witnessSetVersion="1"), ("STALE_STATE", "WITNESS_SET_MISMATCH")),
    ("expiry equal to the observation", None, dict(expiresAt="1000"), ("EXPIRED", None)),
    ("expiry before the observation", None, dict(expiresAt="999"), ("EXPIRED", None)),
    ("expiry above the window", None, dict(expiresAt="1061"), ("STALE_STATE", "PROPOSAL_MISMATCH")),
]


@pytest.mark.parametrize("name,mutate,over,expected", CASES, ids=[c[0] for c in CASES])
def test_each_failing_row_refuses_with_its_class_and_writes_nothing(service, view, store, name, mutate, over, expected):
    cp = prop(view, **over)
    before = snapshot(store)
    r = refusal(lambda: service.sign_checkpoint(cp))
    assert r is not None and (r.code, r.reason) == expected and r.message
    assert snapshot(store) == before


def test_the_edges_of_the_expiry_window_are_exact(service, view):
    assert service.sign_checkpoint(prop(view, expiresAt="1001"))                              # one second after the observation
    view.dbc_ts = 2000
    assert service.sign_checkpoint(prop(view, expiresAt="2060"))                              # exactly observation + 60
    assert refusal(lambda: service.sign_checkpoint(prop(view, expiresAt="2061"))).reason == "PROPOSAL_MISMATCH"


def test_a_block_below_the_dbc_current_checkpoints_block_is_refused(service, view, store):
    view.current = {"sequence": "3", "sourceBlockNumber": "245"}
    ok = prop(view)                                                                             # head 250, sequence 4
    assert ok["sequence"] == "4"
    bad = dict(ok, sourceBlockNumber="244", sourceBlockHash=h("pbc:244"))
    before = snapshot(store)
    r = refusal(lambda: service.sign_checkpoint(bad))
    assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and "sourceBlockNumber" in r.message and snapshot(store) == before
    assert service.sign_checkpoint(dict(ok, sourceBlockNumber="245", sourceBlockHash=h("pbc:245"))) is not None   # equal to the current block is allowed (>=)


def test_the_sequence_is_pinned_to_the_dbc_current_plus_one(service, view):
    view.current = {"sequence": "5", "sourceBlockNumber": "200"}
    assert refusal(lambda: service.sign_checkpoint(prop(view, sequence="5"))).reason == "PROPOSAL_MISMATCH"       # not the next one
    assert refusal(lambda: service.sign_checkpoint(prop(view, sequence="7"))).reason == "PROPOSAL_MISMATCH"       # a gap: the unbounded-sequence poison
    assert service.sign_checkpoint(prop(view, sequence="6"))


def test_the_witness_reads_the_epochs_at_the_proposals_block_and_at_its_own_head(service, view, store):
    view.reads[240] = {"authEpoch": "2", "policyVersion": "1", "witnessSetVersion": "2"}        # an older block: epochs lower than at the head
    view.reads[250] = {"authEpoch": "3", "policyVersion": "1", "witnessSetVersion": "2"}
    older = prop(view, sourceBlockNumber="240", sourceBlockHash=h("pbc:240"), authEpoch="2")
    before = snapshot(store)
    r = refusal(lambda: service.sign_checkpoint(older))
    assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and "authEpoch" in r.message                    # (e): a stale view lacking what the witness can already see
    assert snapshot(store) == before
    older_ok = prop(view, sourceBlockNumber="240", sourceBlockHash=h("pbc:240"), authEpoch="3")                         # (d): the epoch the proposal claims is not the one at its block
    r = refusal(lambda: service.sign_checkpoint(older_ok))
    assert r.reason == "PROPOSAL_MISMATCH"
    view.reads[240] = {"authEpoch": "3", "policyVersion": "1", "witnessSetVersion": "2"}                              # no revocation between 240 and 250: an older block is fine
    assert service.sign_checkpoint(older_ok)


@pytest.mark.parametrize("cp", [None, [], "x", 5, {}, {"sequence": "1"}], ids=["none", "list", "str", "int", "empty", "partial"])
def test_a_proposal_of_the_wrong_shape_is_malformed(service, view, store, cp):
    before = snapshot(store)
    r = refusal(lambda: service.sign_checkpoint(cp))
    assert (r.code, r.reason) == ("MALFORMED", None) and snapshot(store) == before


@pytest.mark.parametrize("mut", [lambda c: c.update(extra="x"), lambda c: c.update(sequence=1), lambda c: c.update(sequence="01"), lambda c: c.update(sourceBlockHash="0x" + "AB" * 32),
                                 lambda c: c.update(psc=PSC.upper()), lambda c: c.update(expiresAt="1e3"), lambda c: c.update(sourceBlockNumber=" 250"), lambda c: c.pop("keyEpoch"),
                                 lambda c: c.update(sourceChainId="18_545"), lambda c: c.update(sequence="-1"), lambda c: c.update(authEpoch=None)])
def test_a_non_canonical_field_is_malformed_and_nothing_is_written(service, view, store, mut):
    cp = prop(view)
    mut(cp)
    before = snapshot(store)
    r = refusal(lambda: service.sign_checkpoint(cp))
    assert (r.code, r.reason) == ("MALFORMED", None) and snapshot(store) == before


def test_an_unreadable_ledger_view_refuses_with_ledger_unreachable_and_writes_nothing(service, view, store):
    cp = prop(view)
    for name in ("observe:pbc", "observe:dbc", "pbc_block", "reads_at", "dbc_current_checkpoint"):
        view.fail = name
        before = snapshot(store)
        r = refusal(lambda: service.sign_checkpoint(cp))
        assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE"), name
        assert snapshot(store) == before, name
    view.fail = None
    assert service.sign_checkpoint(cp)


def test_a_block_after_the_observed_head_is_refused_even_when_the_block_read_succeeds(service, view, store):
    view.lenient = True
    cp = prop(view, sourceBlockNumber="251", sourceBlockHash=h("pbc:251"))
    before = snapshot(store)
    r = refusal(lambda: service.sign_checkpoint(cp))
    assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and "sourceBlockNumber" in r.message and snapshot(store) == before


def test_the_witness_set_version_must_equal_both_the_configured_one_and_the_one_read_at_the_block(store, view):
    view.reads[250] = {"authEpoch": "3", "policyVersion": "1", "witnessSetVersion": "3"}         # the ledger now reports another version
    sv = svc.WitnessService(store=store, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")
    r = refusal(lambda: sv.sign_checkpoint(prop(view, witnessSetVersion="2")))                      # proposal equals the configured one, not the read one
    assert (r.code, r.reason) == ("STALE_STATE", "WITNESS_SET_MISMATCH")
    r = refusal(lambda: sv.sign_checkpoint(prop(view, witnessSetVersion="3")))                      # proposal equals the read one, not the configured one
    assert (r.code, r.reason) == ("STALE_STATE", "WITNESS_SET_MISMATCH")


@pytest.mark.parametrize("bad", [0, -1, True, "60", 1.5, None])
def test_the_maximum_window_must_be_a_positive_integer(store, view, bad):
    with pytest.raises(ValueError):
        svc.WitnessService(store=store, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2", max_checkpoint_ttl=bad)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the durable rule through the service: conflict, recorded value, supersession, tripwire
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_different_valid_value_for_the_same_sequence_is_pinned_and_returns_the_recorded_value(service, view, store):
    a = svc.derive_checkpoint(view, DEPLOY)
    sig_a = service.sign_checkpoint(a)
    view.pbc_head = 251                                                                         # a block is mined: a second VALID value for sequence 1
    b = svc.derive_checkpoint(view, DEPLOY)
    assert b["sourceBlockNumber"] == "251" and b["sequence"] == "1"
    r = refusal(lambda: service.sign_checkpoint(b))
    assert (r.code, r.reason) == ("STALE_STATE", "CONFLICT_PINNED")
    assert r.recorded == {"message": a, "signature": sig_a}                                     # the recorded value and the signature it already issued: public data
    assert eip712.recover(digest_of(r.recorded["message"]), r.recorded["signature"]) == ADDR


def test_the_pinned_key_is_released_only_when_the_old_digest_is_observed_dead(service, view, store):
    a = svc.derive_checkpoint(view, DEPLOY)
    service.sign_checkpoint(a)                                                                  # expires at 1030
    view.pbc_head, view.dbc_ts = 251, 1029
    assert refusal(lambda: service.sign_checkpoint(svc.derive_checkpoint(view, DEPLOY))).reason == "CONFLICT_PINNED"    # one second before the old expiry
    view.dbc_ts = 1030                                                                          # observed timestamp reaches the old expiry: dead
    b = svc.derive_checkpoint(view, DEPLOY)
    sig_b = service.sign_checkpoint(b)
    assert eip712.recover(digest_of(b), sig_b) == ADDR
    ev = store.evidence()
    assert len(ev["superseded"]) == 1 and ev["superseded"][0]["effect"]["sourceBlockNumber"] == "250"            # the old record is kept, with its death evidence
    assert ev["superseded"][0]["digests"][0]["digest"] == "0x" + digest_of(a).hex()
    assert [d["digest"] for d in ev["conflicts"][0]["digests"]] == ["0x" + digest_of(b).hex()] and ev["conflicts"][0]["effect"]["sourceBlockNumber"] == "251"


def test_a_clock_regression_in_the_view_sets_the_persisted_tripwire(service, view, store, tmp_path):
    service.sign_checkpoint(svc.derive_checkpoint(view, DEPLOY))
    view.dbc_ts = 999                                                                           # the DBC clock moved backwards
    r = refusal(lambda: service.sign_checkpoint(prop(view, expiresAt="1020")))
    assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "WITNESS_FAULTED")
    view.dbc_ts = 1100                                                                          # the clock recovers but the store stays faulted until an explicit clear
    r = refusal(lambda: service.sign_checkpoint(svc.derive_checkpoint(view, DEPLOY)))
    assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "WITNESS_FAULTED")


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# properties
# --------------------------------------------------------------------------------------------------------------------------------------------------------
ALT = {"sequence": ["0", "2", "3", "99", "18446744073709551616"], "authEpoch": ["0", "2", "4"], "policyVersion": ["0", "2", "7"], "keyEpoch": ["1", "2"], "witnessSetVersion": ["0", "1", "3"],
       "sourceChainId": ["0", "28545", "999"], "psc": ["0x" + "00" * 20, "0x" + "11" * 20], "sourceBlockNumber": ["0", "1", "249", "251", "9999"],
       "sourceBlockHash": [h("x"), "0x" + "00" * 32], "expiresAt": ["0", "999", "1000", "1031", "1060", "1061", "5000"]}


def oracle_accepts(view, cp):
    """An independent restatement of rows (a) to (f), written separately from the service (same author: correlated)."""
    reads_head = view.reads_at(view.pbc_head)
    n = int(cp["sourceBlockNumber"])
    cur = view.current
    ts = int(view.observe("dbc")["timestamp"])
    return (cp["sourceChainId"] == PBC_ID and cp["psc"] == PSC and cp["sequence"] == str(1 if cur is None else int(cur["sequence"]) + 1)
            and 0 <= n <= view.pbc_head and cp["sourceBlockHash"] == view.pbc_hash(n) and (cur is None or n >= int(cur["sourceBlockNumber"]))
            and cp["keyEpoch"] == "0" and cp["witnessSetVersion"] == "2" == view.reads_at(n)["witnessSetVersion"]
            and cp["authEpoch"] == view.reads_at(n)["authEpoch"] == reads_head["authEpoch"] and cp["policyVersion"] == view.reads_at(n)["policyVersion"] == reads_head["policyVersion"]
            and ts < int(cp["expiresAt"]) <= ts + 60)


def test_poison_property_every_single_field_alteration_matches_the_independent_oracle(tmp_path, view):
    """FL-7 in the model: for every single-field alteration of a valid proposal, and for combinations of two, the witness signs iff an independently written oracle accepts; a signed message is
    exactly the proposal. A fresh store per case so that no earlier record pins the key."""
    n = signed = 0
    base = svc.derive_checkpoint(view, DEPLOY)
    fields = list(ALT)
    cases = [{f: v} for f in fields for v in ALT[f]]
    cases += [{f1: v1, f2: v2} for i, f1 in enumerate(fields) for f2 in fields[i + 1:] for v1 in ALT[f1][:2] for v2 in ALT[f2][:2]]
    for k, over in enumerate(cases):
        st = ws.init_store(str(tmp_path / ("s%d" % k)), BIND, B, OWNER)
        sv = svc.WitnessService(store=st, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")
        cp = dict(base, **over)
        want = oracle_accepts(view, cp)
        try:
            sig = sv.sign_checkpoint(cp)
            got = True
        except svc.WitnessRefusal:
            got = False
        assert got == want, (over, got, want)
        if got:
            signed += 1
            assert eip712.recover(digest_of(cp), sig) == ADDR
        n += 1
    assert n > 150 and 0 < signed < n


def test_the_valid_baseline_is_accepted_by_the_oracle_and_each_field_alteration_that_changes_nothing_is_not_counted(view):
    base = svc.derive_checkpoint(view, DEPLOY)
    assert oracle_accepts(view, base)
    assert all(base[f] not in ALT[f] for f in ALT if f != "expiresAt")                          # the alternatives never equal the baseline value (the grid really alters)


def test_the_service_never_reads_a_host_clock_or_randomness():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "witness_service.py")).read()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mods.add((node.module or "").split(".")[0])
    assert not mods & {"time", "datetime", "random", "socket", "subprocess", "urllib", "http"}, mods
