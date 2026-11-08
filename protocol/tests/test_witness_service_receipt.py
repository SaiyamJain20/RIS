"""Witness service, GrantReceipt path (agent 2, F task 2, slice 4c). Written BEFORE `derive_receipt` and `sign_receipt` existed in hmbc_protocol/witness_service.py.

A receipt is a PURE FUNCTION of ledger state (SIGNING-RULES section 5): in E the witness put "the DBC head when asked" into `dbcBlockNumber/Hash`, so two witnesses asked at different times signed different
receipts. Under F the block is the one that CONTAINS the unique `GrantIssued(grantId, ...)` log of the KSSC, so every honest witness derives byte-identical receipt bytes whenever it is asked. The witness DERIVES
its receipt from its own injected view (the E `attest_grant` logic with that change) and signs only a proposal EQUAL to it. A receipt carries evidence of DBC authorization only (unchanged from E).

Same discipline as slices 4a and 4b: the real store, real EIP-712 digests and signatures with a synthetic key, an INJECTED fake ledger view, no ledger. Refusal classes follow E (NOT_COMMITTED: no allowed grant
yet, or the witness has not seen the grant block; WRONG_SUBJECT: the PSC record does not match, or the log is not unique); a proposal that differs from the derivation is STALE_STATE / PROPOSAL_MISMATCH (explicit
choice). GrantReceipt has NO liveness field, so a conflicting effect for the same request digest is pinned until the PSC records the outcome, and then the derivation refuses anyway: the store's
`executed-receipt` death evidence is a capability this service does not use (recorded as a limit).
"""
import json

import pytest

from hmbc_protocol import eip712, keys, messages
from hmbc_protocol import witness_service as svc
from hmbc_protocol import witness_state as ws
from eth_account import Account

from test_witness_service import B, BIND, DBC_ID, DEPLOY, KEY, ADDR, OWNER, PBC_ID, h, refusal, snapshot
from test_witness_service_decision import DATA_ID, GID, KSSC, DView

LOG_BLOCK = 80


class RView(DView):
    def __init__(self):
        super().__init__()
        self.grant_allowed = True
        self.grant_digest_override = None
        self.grant_key_epoch, self.grant_expires = "0", "1015"
        self.issued = [{"block": LOG_BLOCK, "hash": h("dbc:%d" % LOG_BLOCK)}]
        self.dbc_number = 90

    def grant_id(self):
        return "0x" + eip712.grant_id(bytes.fromhex(self.digest()[2:]), KSSC, int(DBC_ID)).hex()

    def grant(self, grant_id):
        self._maybe_fail("grant")
        return {"digest": self.grant_digest_override or self.digest(), "dataId": DATA_ID, "gid": GID, "keyEpoch": self.grant_key_epoch, "expiresAt": self.grant_expires, "allowed": self.grant_allowed}

    def grant_issued_logs(self, grant_id):
        self._maybe_fail("grant_issued_logs")
        return list(self.issued)


@pytest.fixture
def view():
    return RView()


@pytest.fixture
def store(tmp_path):
    return ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER)


@pytest.fixture
def service(store, view):
    return svc.WitnessService(store=store, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")


def derive(view):
    return svc.derive_receipt(view, DEPLOY, view.grant_id(), witness_set_version="2")


def digest_of(r):
    return svc._receipt_digest(r, DEPLOY)


def test_the_carried_e_validator_refuses_an_f_receipt_so_the_service_hashes_it_itself():
    """A finding, kept as a test: wire.grant_receipt (E) fixes witnessSetVersion=1, so an F receipt (version 2) must not be routed through it or through messages.digest_of."""
    r = {"requestDigest": "0x" + "11" * 32, "grantId": "0x" + "22" * 32, "gid": GID, "dataId": DATA_ID, "keyEpoch": "0", "grantExpiresAt": "1015", "witnessSetVersion": "2", "dbcChainId": DBC_ID,
         "kssc": KSSC, "dbcBlockNumber": "80", "dbcBlockHash": "0x" + "33" * 32}
    from hmbc_protocol import wire
    with pytest.raises(wire.WireError):
        wire.grant_receipt(r)
    with pytest.raises(wire.WireError):
        messages.digest_of("GrantReceipt", r, messages.domain_for("GrantReceipt", r, DEPLOY))
    e = dict(r, witnessSetVersion="1")                                                           # the F digest function agrees with the E one wherever E accepts the receipt
    assert svc._receipt_digest(e, DEPLOY) == messages.digest_of("GrantReceipt", e, messages.domain_for("GrantReceipt", e, DEPLOY))
    assert svc._receipt_digest(r, DEPLOY) != svc._receipt_digest(e, DEPLOY)


def expected(view):
    return {"requestDigest": view.digest(), "grantId": view.grant_id(), "gid": GID, "dataId": DATA_ID, "keyEpoch": "0", "grantExpiresAt": "1015", "witnessSetVersion": "2", "dbcChainId": DBC_ID,
            "kssc": KSSC, "dbcBlockNumber": str(LOG_BLOCK), "dbcBlockHash": h("dbc:%d" % LOG_BLOCK)}


# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_derived_receipt_is_built_from_the_grant_and_the_grant_issued_block(view):
    assert derive(view) == expected(view)


def test_the_receipt_does_not_depend_on_when_the_witness_is_asked(view):
    first = derive(view)
    view.dbc_number, view.dbc_ts = 95, 1007                                                      # the DBC head moved on: E's receipt would have changed, F's does not
    assert derive(view) == first
    other = RView()
    other.dbc_number = 140                                                                       # a second witness with a later view of the same ledger
    assert derive(other) == first


def test_a_matching_proposal_is_signed_and_recorded_under_the_request_digest_with_no_expiry(service, view, store):
    r = derive(view)
    sig = service.sign_receipt(r)
    assert eip712.recover(digest_of(r), sig) == ADDR
    ev = store.evidence()
    c = ev["conflicts"][0]
    assert c["type"] == "GrantReceipt" and c["keyField"] == view.digest()
    assert c["domainSeparator"] == "0x" + eip712.domain_separator(messages.domain_for("GrantReceipt", r, DEPLOY)).hex()
    assert set(c["effect"]) == {"grantId", "gid", "dataId", "keyEpoch", "grantExpiresAt", "witnessSetVersion", "dbcChainId", "kssc", "dbcBlockNumber", "dbcBlockHash"} and c["digests"][0]["signature"] == sig
    assert ev["observations"][0]["chainId"] == PBC_ID                                           # the target ledger of a receipt is the PBC
    assert json.dumps(c["digests"][0]).count("expiresAt") == 0 or c["digests"][0].get("expiresAt") is None
    assert service.sign_receipt(r) == sig


def test_two_witnesses_with_different_views_sign_byte_identical_receipts(tmp_path, view):
    other_view = RView()
    other_view.dbc_number, other_view.dbc_ts = 150, 1100
    key2 = keys.synthetic_private_key("witness-2")
    st2 = ws.init_store(str(tmp_path / "w2"), BIND, B, "witness:" + Account.from_key(key2).address.lower())
    st1 = ws.init_store(str(tmp_path / "w1"), BIND, B, OWNER)
    s1 = svc.WitnessService(store=st1, key=KEY, view=view, deployment=DEPLOY, witness_set_version="2")
    s2 = svc.WitnessService(store=st2, key=key2, view=other_view, deployment=DEPLOY, witness_set_version="2")
    r1, r2 = derive(view), derive(other_view)
    assert r1 == r2 and digest_of(r1) == digest_of(r2)                                          # one K, one V, one digest
    a, b = s1.sign_receipt(r1), s2.sign_receipt(r2)
    assert a != b and eip712.recover(digest_of(r1), a) != eip712.recover(digest_of(r2), b)      # different signers over the same digest


@pytest.mark.parametrize("field,alt", [("requestDigest", "0x" + "ab" * 32), ("grantId", "0x" + "cd" * 32), ("gid", "0x" + "01" * 20), ("dataId", "0x" + "02" * 32), ("keyEpoch", "1"),
                                       ("grantExpiresAt", "1016"), ("witnessSetVersion", "3"), ("dbcChainId", "1"), ("kssc", "0x" + "03" * 20), ("dbcBlockNumber", "90"),
                                       ("dbcBlockHash", "0x" + "ef" * 32)])
def test_a_proposal_that_differs_from_the_witnesss_derivation_in_any_field_is_refused(service, view, store, field, alt):
    bad = dict(derive(view), **{field: alt})
    before = snapshot(store)
    r = refusal(lambda: service.sign_receipt(bad))
    assert r is not None and snapshot(store) == before
    if field not in ("requestDigest", "grantId"):
        assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and field in r.message


@pytest.mark.parametrize("bad", [None, [], "x", {}, {"grantId": "0x" + "00" * 32}], ids=["none", "list", "str", "empty", "partial"])
def test_a_proposal_of_the_wrong_shape_is_malformed(service, view, store, bad):
    before = snapshot(store)
    r = refusal(lambda: service.sign_receipt(bad))
    assert (r.code, r.reason) == ("MALFORMED", None) and snapshot(store) == before


REFUSALS = [
    ("no allowed grant", lambda v: setattr(v, "grant_allowed", False), "NOT_COMMITTED"),
    ("the grant belongs to another request than its id says", lambda v: setattr(v, "grant_digest_override", "0x" + "55" * 32), "NOT_COMMITTED"),
    ("the witness has not seen the grant block (no GrantIssued log yet)", lambda v: setattr(v, "issued", []), "NOT_COMMITTED"),
    ("the GrantIssued log is in a block after the witness's own DBC head", lambda v: setattr(v, "issued", [{"block": 91, "hash": h("dbc:91")}]), "NOT_COMMITTED"),
    ("two GrantIssued logs", lambda v: setattr(v, "issued", [{"block": 80, "hash": h("dbc:80")}, {"block": 81, "hash": h("dbc:81")}]), "WRONG_SUBJECT"),
    ("the PSC has not forwarded the request", lambda v: setattr(v, "status", "0"), "WRONG_SUBJECT"),
    ("the PSC already recorded an outcome", lambda v: setattr(v, "status", "2"), "WRONG_SUBJECT"),
    ("the PSC record's gid differs from the grant's", lambda v: v.rec_override.update(gid="0x" + "01" * 20), "WRONG_SUBJECT"),
    ("the PSC record's dataId differs from the grant's", lambda v: v.rec_override.update(dataId="0x" + "02" * 32), "WRONG_SUBJECT"),
]


@pytest.mark.parametrize("name,mutate,code", REFUSALS, ids=[r[0] for r in REFUSALS])
def test_each_failing_condition_refuses_with_the_e_class_and_writes_nothing(service, view, store, name, mutate, code):
    own = derive(view)
    mutate(view)
    before = snapshot(store)
    r = refusal(lambda: svc.derive_receipt(view, DEPLOY, view.grant_id(), witness_set_version="2"))
    assert r is not None and r.code == code, (name, getattr(r, "code", None))
    r2 = refusal(lambda: service.sign_receipt(own))
    assert r2 is not None and r2.code == code and snapshot(store) == before


def test_the_receipt_copies_the_key_epoch_and_the_expiry_from_the_grant(view):
    view.grant_key_epoch, view.grant_expires = "3", "2000"
    r = derive(view)
    assert (r["keyEpoch"], r["grantExpiresAt"]) == ("3", "2000")


def test_a_grant_with_a_zero_expiry_gives_no_receipt(view):
    view.grant_expires = "0"
    r = refusal(lambda: derive(view))
    assert (r.code, r.reason) == ("WRONG_SUBJECT", None) and "canonical GrantReceipt" in r.message              # a ledger value out of range is a refusal, never a raw exception


def test_a_malformed_grant_id_is_malformed(view):
    for bad in ("0x12", "0X" + "AB" * 32, 5, None, "0x" + "AB" * 32):
        r = refusal(lambda: svc.derive_receipt(view, DEPLOY, bad, witness_set_version="2"))
        assert (r.code, r.reason) == ("MALFORMED", None), bad


def test_an_unreadable_view_refuses_with_ledger_unreachable_and_writes_nothing(service, view, store):
    r0 = derive(view)
    for name in ("grant", "grant_issued_logs", "psc_request", "observe:dbc"):
        view.fail = name
        before = snapshot(store)
        r = refusal(lambda: service.sign_receipt(r0))
        assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE"), name
        assert snapshot(store) == before, name
    view.fail = "observe:dbc"
    assert refusal(lambda: svc.derive_receipt(view, DEPLOY, view.grant_id(), witness_set_version="2")).reason == "LEDGER_UNREACHABLE"      # the proposer-side derivation maps it too
    view.fail = None
    assert service.sign_receipt(r0)


def test_a_conflicting_receipt_for_the_same_request_is_pinned_and_stays_pinned_there_is_no_expiry(service, view, store):
    first = derive(view)
    service.sign_receipt(first)
    view.issued = [{"block": 70, "hash": h("dbc:70")}]                                           # the log appears in another block: only a ledger reorganisation, outside the assumptions
    other = derive(view)
    assert other["dbcBlockNumber"] == "70"
    for ts in (1000, 5000, 10 ** 9):
        view.dbc_ts = ts
        r = refusal(lambda: service.sign_receipt(other))
        assert (r.code, r.reason) == ("STALE_STATE", "CONFLICT_PINNED") and r.recorded is None
    assert [c["effect"]["dbcBlockNumber"] for c in store.evidence()["conflicts"]] == [str(LOG_BLOCK)]


def test_the_witness_set_version_comes_from_the_witness_not_the_caller(view):
    r = svc.derive_receipt(view, DEPLOY, view.grant_id(), witness_set_version="7")
    assert r["witnessSetVersion"] == "7"
