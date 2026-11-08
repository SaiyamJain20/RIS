"""Witness service, GovernanceAction path (agent 2, F task 2, slice 4d). Written BEFORE `sign_governance` existed in hmbc_protocol/witness_service.py.

A governance action comes from an operator decision, not from ledger state, so the witness validates a WHOLE proposed action (SIGNING-RULES section 3, GovernanceAction row): (a) the typed-field rules, (b)
`nonce == Governance.governanceNonce() + 1`, (c) its own `witnessSetVersion`, (d) the TMSC preconditions NOW (ADD: root neither authority nor tombstoned; REMOVE and SET: root is an authority), (e) its LOCAL
APPROVAL, and (f) `expiresAt` inside the window `obs < e <= obs + 120` of the PBC (the target ledger). The local approval is a TEST-ONLY allow-list of (action, root, admins) tuples injected by the runner;
a witness with none signs nothing (fail closed). This is a reconstruction choice for a SPECIFICATION GAP (the paper gives no rule for what makes a hospital's witness consent), not a discovered behaviour.

An INDEPENDENT cross-check exists: agent 3's published signing vector (`interfaces/v2/vectors/signing.json`, synthetic and offline) carries three GovernanceAction typed data with digests, struct hashes and the
signatures of witnesses 0, 3 and 2. The service signs the vector's messages with the synthetic keys of those witnesses; the digests and the RFC 6979 signatures must equal the vector's bytes. (The vector was
produced with the same production encoder by the same project: it is a cross-check against the published bytes, not an external oracle.) The ledger and the TMSC state are an injected FAKE.

Explicit refusal classes where F0 does not fix one: typed-field failures MALFORMED; a wrong nonce STALE_STATE / PROPOSAL_MISMATCH; another witnessSetVersion STALE_STATE / WITNESS_SET_MISMATCH; ADD of a root that
is already an authority ALREADY_REGISTERED, of a tombstoned root REVOKED; REMOVE or SET of a root that is not an authority NOT_REGISTERED; not on the local allow-list POLICY_DENIED; an expiry at or before the
observation EXPIRED, above the window STALE_STATE / PROPOSAL_MISMATCH; a deployment without a Governance contract WRONG_PROFILE.
"""
import copy
import json
import os
import subprocess

import pytest

from hmbc_protocol import eip712, keys
from hmbc_protocol import witness_service as svc
from hmbc_protocol import witness_state as ws
from eth_account import Account

from test_witness_service import B, BIND, DEPLOY, KEY, ADDR, OWNER, FakeView, h, refusal, snapshot

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GOV = "0x" + "77" * 20
GDEPLOY = copy.deepcopy(DEPLOY)
GDEPLOY["chains"]["pbc"]["contracts"]["Governance"] = GOV
R1, R2 = "0x" + "88" * 20, "0x" + "99" * 20
A1, A2, A3 = "0x" + "11" * 20, "0x" + "22" * 20, "0x" + "33" * 20
NOW = 1_800_000_000


class GView(FakeView):
    def __init__(self):
        super().__init__()
        self.pbc_ts_base = NOW - self.pbc_head                                                   # the PBC's latest block timestamp is NOW
        self.nonce = 0
        self.authorities, self.tombstoned = set(), set()

    def governance_nonce(self):
        self._maybe_fail("governance_nonce")
        return self.nonce

    def is_authority(self, addr):
        self._maybe_fail("is_authority")
        return addr in self.authorities

    def removed_authority(self, addr):
        self._maybe_fail("removed_authority")
        return addr in self.tombstoned


def act(action="1", root=R1, admins=(A1, A2), nonce="1", wsv="2", exp=NOW + 60):
    return {"action": action, "root": root, "admins": list(admins), "nonce": nonce, "witnessSetVersion": wsv, "expiresAt": str(exp)}


ALLOW = [("1", R1, (A1, A2)), ("2", R1, ()), ("3", R1, ()), ("3", R1, (A3,)), ("1", R2, (A1,))]


@pytest.fixture
def view():
    v = GView()
    v.authorities = {R1}
    return v


@pytest.fixture
def store(tmp_path):
    return ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER)


def make_service(store, view, key=KEY, allow=ALLOW, deployment=GDEPLOY):
    return svc.WitnessService(store=store, key=key, view=view, deployment=deployment, witness_set_version="2", allowed_governance=allow)


@pytest.fixture
def service(store, view):
    view.authorities = set()                                                                     # ADD of R1 needs R1 to be neither authority nor tombstoned
    return make_service(store, view)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the published signing vector
# --------------------------------------------------------------------------------------------------------------------------------------------------------
FIXTURE = os.path.join(ROOT, "protocol", "tests", "fixtures", "agent3-v2-signing-governance-vectors.json")


def _vectors():
    return json.load(open(FIXTURE))["vectors"]


def test_the_fixture_vectors_equal_agent_3s_published_blob_when_git_can_show_it():
    fx = json.load(open(FIXTURE))
    prov = fx["provenance"]
    try:
        blob = subprocess.check_output(["git", "-C", ROOT, "show", prov["commit"] + ":" + prov["path"]], stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pytest.skip("the published blob is not reachable from here (a disposable copy has no repository)")
    import hashlib
    assert hashlib.sha256(blob).hexdigest() == prov["blobSha256"]
    assert [v for v in json.loads(blob)["vectors"] if v["name"] == "GovernanceAction"] == fx["vectors"]


def test_the_service_reproduces_the_published_governance_vector_digests_and_signatures(tmp_path):
    vecs = _vectors()
    assert len(vecs) == 3
    n = 0
    for vec in vecs:
        msg = vec["typedData"]["message"]
        assert vec["typedData"]["domain"]["verifyingContract"] == GOV and vec["typedData"]["domain"]["chainId"] == GDEPLOY["chains"]["pbc"]["chainId"]
        assert "0x" + svc._governance_digest(msg, GDEPLOY).hex() == vec["digest"]
        assert "0x" + eip712.domain_separator(svc._governance_domain(GDEPLOY)).hex() == vec["domainSeparator"]
        for sigrec in vec["signatures"]:
            idx = int(sigrec["witnessIndex"])
            key = keys.synthetic_private_key("witness-%d" % (idx + 1))
            assert Account.from_key(key).address.lower() == sigrec["signer"]
            v = GView()
            v.nonce = int(msg["nonce"]) - 1
            v.authorities = {msg["root"]} if msg["action"] != "1" else set()
            st = ws.init_store(str(tmp_path / ("w%d-%s" % (idx, vec["digest"][2:8]))), BIND, B, "witness:" + sigrec["signer"])
            sv = make_service(st, v, key=key, allow=[(msg["action"], msg["root"], tuple(msg["admins"]))])
            assert sv.sign_governance(msg) == sigrec["signature"]
            n += 1
    assert n == 9


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# signing and the record
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_valid_approved_action_is_signed_and_recorded_under_its_nonce(service, view, store):
    a = act()
    sig = service.sign_governance(a)
    assert eip712.recover(svc._governance_digest(a, GDEPLOY), sig) == ADDR
    ev = store.evidence()
    c = ev["conflicts"][0]
    assert c["type"] == "GovernanceAction" and c["keyField"] == "1" and c["witnessSetVersion"] == "2"
    assert c["effect"] == {"action": "1", "root": R1, "admins": [A1, A2], "witnessSetVersion": "2"} and c["digests"][0]["signature"] == sig
    assert c["domainSeparator"] == "0x" + eip712.domain_separator(svc._governance_domain(GDEPLOY)).hex()
    assert ev["observations"][0]["chainId"] == GDEPLOY["chains"]["pbc"]["chainId"] and ev["observations"][0]["timestamp"] == str(NOW)      # the target ledger of governance is the PBC
    assert service.sign_governance(a) == sig


def test_a_renewal_with_the_same_effect_and_a_later_expiry_signs_a_new_digest(service, view, store):
    a = act(exp=NOW + 30)
    s1 = service.sign_governance(a)
    s2 = service.sign_governance(dict(a, expiresAt=str(NOW + 90)))
    assert s2 != s1 and len(store.evidence()["conflicts"][0]["digests"]) == 2


@pytest.mark.parametrize("bad", [0, -1, True, "120", 1.5, None])
def test_the_maximum_governance_window_must_be_a_positive_integer(store, view, bad):
    with pytest.raises(ValueError):
        svc.WitnessService(store=store, key=KEY, view=view, deployment=GDEPLOY, witness_set_version="2", max_governance_ttl=bad)


def test_a_deployment_without_a_governance_contract_refuses_wrong_profile(store, view):
    sv = make_service(store, view, deployment=DEPLOY)
    r = refusal(lambda: sv.sign_governance(act()))
    assert (r.code, r.reason) == ("WRONG_PROFILE", None)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------------------------------------------------------------------------------------
BAD_SHAPES = [
    ("action 0", dict(action="0")), ("action 4", dict(action="4")), ("action as int", dict(action=1)), ("action with a leading zero", dict(action="01")),
    ("zero root", dict(root="0x" + "00" * 20)), ("uppercase root", dict(root="0x" + "AB" * 20)), ("short root", dict(root="0x1234")),
    ("admins not ascending", dict(admins=[A2, A1])), ("duplicate admins", dict(admins=[A1, A1])), ("a zero admin", dict(admins=["0x" + "00" * 20, A1])),
    ("nine admins", dict(admins=["0x" + "%02x" % (i + 1) * 20 for i in range(9)])), ("ADD with no admins", dict(admins=[])), ("REMOVE with admins", dict(action="2", admins=[A1])),
    ("admins not a list", dict(admins=A1)), ("admins as a tuple", dict(admins=(A1, A2))), ("nonce as int", dict(nonce=1)), ("nonce with a leading zero", dict(nonce="01")),
    ("nonce beyond uint64", dict(nonce="18446744073709551616")), ("expiresAt negative", dict(exp="-1")), ("witnessSetVersion empty", dict(witnessSetVersion="")), ("witnessSetVersion with a leading zero", dict(witnessSetVersion="02")),
]


@pytest.mark.parametrize("name,over", BAD_SHAPES, ids=[b[0] for b in BAD_SHAPES])
def test_a_field_that_breaks_the_typed_rules_is_malformed_and_nothing_is_written(service, view, store, name, over):
    a = act()
    for k, v in over.items():
        a["expiresAt" if k == "exp" else k] = v
    before = snapshot(store)
    r = refusal(lambda: service.sign_governance(a))
    assert (r.code, r.reason) == ("MALFORMED", None) and snapshot(store) == before


@pytest.mark.parametrize("bad", [None, [], "x", 5, {}, {"action": "1"}], ids=["none", "list", "str", "int", "empty", "partial"])
def test_a_proposal_of_the_wrong_shape_is_malformed(service, store, bad):
    before = snapshot(store)
    r = refusal(lambda: service.sign_governance(bad))
    assert (r.code, r.reason) == ("MALFORMED", None) and snapshot(store) == before


def test_remove_allows_no_admins_set_allows_zero_to_eight_and_add_one_to_eight(service, view, store):
    view.authorities = {R1}
    many = ["0x" + "%02x" % (i + 1) * 20 for i in range(8)]
    allow = [("3", R1, ()), ("3", R1, tuple(many)), ("2", R1, ()), ("1", R2, tuple(many))]
    sv = make_service(store, view, allow=allow)
    assert sv.sign_governance(act(action="3", admins=[], nonce="1"))
    view.nonce = 1
    assert sv.sign_governance(act(action="3", admins=many, nonce="2"))
    view.nonce = 2
    assert sv.sign_governance(act(action="2", admins=[], nonce="3"))
    view.nonce = 3
    assert sv.sign_governance(act(action="1", root=R2, admins=many, nonce="4"))                  # exactly eight


def test_the_nonce_must_be_the_governance_nonce_plus_one(service, view, store):
    for n, ok in (("0", False), ("1", True), ("2", False)):
        before = snapshot(store)
        r = refusal(lambda: service.sign_governance(act(nonce=n)))
        if ok:
            assert r is None
        else:
            assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and "nonce" in r.message and snapshot(store) == before
    view.nonce = 5
    assert refusal(lambda: service.sign_governance(act(nonce="1"))).reason == "PROPOSAL_MISMATCH"
    assert refusal(lambda: service.sign_governance(act(nonce="7"))).reason == "PROPOSAL_MISMATCH"


def test_another_witness_set_version_is_refused(service, store):
    before = snapshot(store)
    r = refusal(lambda: service.sign_governance(act(wsv="3")))
    assert (r.code, r.reason) == ("STALE_STATE", "WITNESS_SET_MISMATCH") and snapshot(store) == before


PRECONDITIONS = [
    ("ADD of a root that is already an authority", lambda v: v.authorities.add(R1), act(), "ALREADY_REGISTERED"),
    ("ADD of a tombstoned root", lambda v: v.tombstoned.add(R1), act(), "REVOKED"),
    ("REMOVE of a root that is not an authority", lambda v: None, act(action="2", admins=[]), "NOT_REGISTERED"),
    ("SET of a root that is not an authority", lambda v: None, act(action="3", admins=[]), "NOT_REGISTERED"),
]


@pytest.mark.parametrize("name,mutate,a,code", PRECONDITIONS, ids=[p[0] for p in PRECONDITIONS])
def test_a_failing_tmsc_precondition_is_refused_up_front_so_a_doomed_action_never_pins_the_key(service, view, store, name, mutate, a, code):
    mutate(view)
    before = snapshot(store)
    r = refusal(lambda: service.sign_governance(a))
    assert r is not None and r.code == code and snapshot(store) == before


def test_remove_and_set_of_an_authority_are_accepted(service, view):
    view.authorities = {R1}
    assert service.sign_governance(act(action="2", admins=[]))
    view.nonce = 1
    assert service.sign_governance(act(action="3", admins=[], nonce="2"))


def test_the_local_allow_list_decides_and_a_witness_without_one_signs_nothing(store, view):
    view.authorities = set()
    none_ = make_service(store, view, allow=None)
    r = refusal(lambda: none_.sign_governance(act()))
    assert (r.code, r.reason) == ("POLICY_DENIED", None) and "allow" in r.message
    empty = make_service(store, view, allow=[])
    assert refusal(lambda: empty.sign_governance(act())).code == "POLICY_DENIED"
    for other in (act(admins=[A1, A3]), act(admins=[A1]), act(root=R2), act(action="3")):         # any difference in action, root or admins (order included) is not the approved tuple
        sv = make_service(store, view, allow=[("1", R1, (A1, A2))])
        view.authorities = {R1} if other["action"] == "3" else set()
        assert refusal(lambda: sv.sign_governance(other)).code == "POLICY_DENIED", other
    view.authorities = set()
    assert make_service(store, view, allow=[("1", R1, (A1, A2))]).sign_governance(act())


def test_the_allow_list_is_a_snapshot_not_an_alias(store, view):
    view.authorities = set()
    allow = [("1", R1, (A1, A2))]
    sv = make_service(store, view, allow=allow)
    allow.clear()
    assert sv.sign_governance(act())


def test_the_expiry_window_is_the_pbc_observation_plus_up_to_120_seconds(service, view, store):
    for exp, expect in ((NOW, "EXPIRED"), (NOW - 5, "EXPIRED"), (NOW + 1, None), (NOW + 120, None), (NOW + 121, "PROPOSAL_MISMATCH")):
        before = snapshot(store)
        r = refusal(lambda: service.sign_governance(act(exp=exp)))
        if expect is None:
            assert r is None, exp
        elif expect == "EXPIRED":
            assert (r.code, r.reason) == ("EXPIRED", None) and snapshot(store) == before
        else:
            assert (r.code, r.reason) == ("STALE_STATE", "PROPOSAL_MISMATCH") and "expiresAt" in r.message and snapshot(store) == before


def test_an_unreadable_view_refuses_with_ledger_unreachable_and_writes_nothing(service, view, store):
    for name in ("governance_nonce", "is_authority", "removed_authority", "observe:pbc"):
        view.fail = name
        before = snapshot(store)
        r = refusal(lambda: service.sign_governance(act()))
        assert (r.code, r.reason) == ("ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE"), name
        assert snapshot(store) == before, name
    view.fail = None
    assert service.sign_governance(act())


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the durable rule through the governance path
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_different_approved_action_for_the_same_nonce_is_pinned_until_the_old_one_is_observed_dead(store, view):
    view.authorities = set()
    sv = make_service(store, view, allow=[("1", R1, (A1, A2)), ("1", R2, (A1,))])
    sv.sign_governance(act(exp=NOW + 30))
    r = refusal(lambda: sv.sign_governance(act(root=R2, admins=[A1], exp=NOW + 50)))
    assert (r.code, r.reason) == ("STALE_STATE", "CONFLICT_PINNED") and r.recorded is None            # recorded values exist only for checkpoints
    view.pbc_ts_base += 29                                                                       # one second before the old expiry
    assert refusal(lambda: sv.sign_governance(act(root=R2, admins=[A1], exp=NOW + 79))).reason == "CONFLICT_PINNED"
    view.pbc_ts_base += 1                                                                        # the observed PBC timestamp reaches the old expiry: it is dead
    assert sv.sign_governance(act(root=R2, admins=[A1], exp=NOW + 80))
    ev = store.evidence()
    assert len(ev["superseded"]) == 1 and ev["superseded"][0]["effect"]["root"] == R1 and ev["superseded"][0]["death"]["kind"] == "expiry"


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# property: every single-field alteration against an independently written oracle
# --------------------------------------------------------------------------------------------------------------------------------------------------------
ALT = {"action": ["0", "2", "3", "4"], "root": [R2, "0x" + "00" * 20, "0x" + "aa" * 20], "admins": [[], [A1], [A1, A3], [A2, A1], [A1, A1], [A1, A2, A3]], "nonce": ["0", "2", "99"],
       "witnessSetVersion": ["0", "1", "3"], "expiresAt": ["0", str(NOW), str(NOW + 1), str(NOW + 120), str(NOW + 121), "99999999999"]}


def oracle_accepts(view, a, allow):
    """The rules restated independently of the service (same author: correlated)."""
    import re
    addr = re.compile(r"0x[0-9a-f]{40}")
    ad = a["admins"]
    typed = (a["action"] in ("1", "2", "3") and addr.fullmatch(a["root"]) and a["root"] != "0x" + "00" * 20 and isinstance(ad, list) and all(isinstance(x, str) and addr.fullmatch(x) and x != "0x" + "00" * 20 for x in ad)
             and all(x < y for x, y in zip(ad, ad[1:])) and len(ad) <= 8 and not (a["action"] == "1" and not ad) and not (a["action"] == "2" and ad))
    if not typed:
        return False
    if int(a["nonce"]) != view.nonce + 1 or a["witnessSetVersion"] != "2":
        return False
    root, act_ = a["root"], a["action"]
    if act_ == "1" and (root in view.authorities or root in view.tombstoned):
        return False
    if act_ in ("2", "3") and root not in view.authorities:
        return False
    if (act_, root, tuple(ad)) not in [(x, y, tuple(z)) for x, y, z in allow]:
        return False
    return NOW < int(a["expiresAt"]) <= NOW + 120


def test_property_the_witness_signs_a_governance_action_iff_the_independent_oracle_accepts(tmp_path):
    n = signed = 0
    for base_action, authorities in (("1", set()), ("2", {R1}), ("3", {R1})):
        view = GView()
        view.authorities = set(authorities)
        base = act(action=base_action, admins=[] if base_action != "1" else [A1, A2])
        cases = [{}] + [{f: v} for f in ALT for v in ALT[f]]
        for k, over in enumerate(cases):
            st = ws.init_store(str(tmp_path / ("s%s%d" % (base_action, k))), BIND, B, OWNER)
            sv = make_service(st, view)
            a = dict(base, **over)
            want = bool(oracle_accepts(view, a, ALLOW))
            try:
                sv.sign_governance(a)
                got = True
            except svc.WitnessRefusal:
                got = False
            assert got == want, (base_action, over, got, want)
            signed += got
            n += 1
    assert n > 60 and 0 < signed < n
