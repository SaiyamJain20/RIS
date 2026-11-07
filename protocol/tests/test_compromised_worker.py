"""TEST-ONLY compromised key-worker variant H5 (agent 2, F task 3; INVENTORY FM-08 and row F-19, PLAN B-F1 bullet 4). Written BEFORE testtools/compromised_worker.py existed.

What it shows, and what it does NOT. The F certificate layer (q = 3 of 4 witness signatures checked by the real contracts) authorises a GRANT; it does not hold or guard the key worker's secrets. A worker that has
been taken over simply stops asking: `CompromisedWorker` releases the symbolic capability for a request digest it was TOLD about without any ledger-committed grant, while for every other grant it behaves exactly like
the honest `Worker`. The grant id is a hash of the request digest, so a compromised worker can only release for a digest it is given (the CLAIMS); that also keeps the variant from degenerating into
"allow everything". The honest worker refuses the same grant id with NOT_COMMITTED (positive control, same inputs). SYMBOLIC ONLY: the response token is a TEST-ONLY random handle, so this is a statement
about WHERE authorisation is enforced, never a secrecy or ABE conclusion, and never witness-only resilience (that is the Byzantine-witness work).

Offline tests: a stub ledger answers `grantDetails` with the all-zero grant the real KSSC returns for an unknown id. LIVE tests (`test_live_*`, real Anvil + agent 1's F ledger snapshot 85c59f5, skipped when
Foundry or the commit is missing): the real KSSC has no such grant, a real quorum certificate layer works on the same chain, and the compromised worker still releases.
"""
import hashlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from hmbc_protocol import eip712, keys, symbolic
from hmbc_protocol.worker import Worker, WorkerError

from test_faulty_witness import imported_modules
from test_rpc_binding_view_live import accept_checkpoint, f_ledger, live_f, real_witnesses  # noqa: F401  (live_f is a fixture)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
FX = os.path.join(PROTO, "tests", "fixtures")
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")
ENV = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
MANIFEST = json.load(open(F2))
KSSC = MANIFEST["chains"]["dbc"]["contracts"]["KSSC"]
DBC_CHAIN = int(MANIFEST["chains"]["dbc"]["chainId"])
NOW = 1_791_000_000
ZERO = "0x" + "00" * 32
DATA_ID, OWNER, PAYLOAD = "0x" + "d1" * 32, "0x" + "a1" * 20, "0x" + "c1" * 32
RECORD = {"dataId": DATA_ID, "owner": OWNER, "payloadDigest": PAYLOAD}
POLICY = {"clauses": [[{"role": "0x" + "b1" * 32, "kind": "1", "issuerMode": "0"}]]}
REQUEST = "0x" + "e1" * 32                         # a request digest the PBC never forwarded and the DBC never granted
GID = "0x" + "99" * 20


def grant_id_of(request_digest):
    return "0x" + eip712.grant_id(bytes.fromhex(request_digest[2:]), KSSC, DBC_CHAIN).hex()


def claim(**over):
    c = {"requestDigest": REQUEST, "dataId": DATA_ID, "gid": GID, "recipientKeyRef": "keyref:user:mallory"}
    c.update(over)
    return c


class StubDbc:
    chain_id = DBC_CHAIN

    def __init__(self):
        self.calls = []

    def now(self):
        return NOW

    def call(self, contract, fn, *args):
        self.calls.append((fn, args))
        assert fn == "grantDetails", fn
        return {"exists": False, "allowed": False, "requestDigest": ZERO, "dataId": ZERO, "gid": "0x" + "00" * 20, "keyEpoch": "0", "expiresAt": "0", "recipientKeyHash": ZERO}


def stub_ledger(deployment=MANIFEST):
    return SimpleNamespace(deployment=deployment, KSSC=SimpleNamespace(address=KSSC), dbc=StubDbc())


def register(worker):
    """The record is already in the worker's registry: a compromised worker is one that LEGITIMATELY holds it. (The live tests register through the real `encrypt_record`.)"""
    worker.db.execute("insert into records values(?,?,?,?,?,?)", (DATA_ID, OWNER, PAYLOAD, repr(sorted(POLICY.items())), symbolic.policy_digest(POLICY), symbolic.ciphertext_digest(RECORD, POLICY)))


def modules():
    sys.path.insert(0, PROTO)
    from testtools import compromised_worker as cw
    return cw


def honest(tmp_path, led=None):
    w = Worker(led or stub_ledger(), str(tmp_path / "honest"), clock=lambda: NOW)
    register(w)
    return w


def compromised(tmp_path, claims=None, led=None, name="bad"):
    cw = modules()
    w = cw.CompromisedWorker(led or stub_ledger(), str(tmp_path / name), clock=lambda: NOW, claims=[claim()] if claims is None else claims)
    register(w)
    return w


# ---- the positive control: the honest worker refuses the same call -------------------------------------------------------------------------------------------

def test_the_honest_worker_refuses_a_grant_the_ledger_never_committed(tmp_path):
    w = honest(tmp_path)
    with pytest.raises(WorkerError) as e:
        w.release(grant_id_of(REQUEST))
    assert e.value.code == "NOT_COMMITTED"
    assert w.events() == [] and w.status(grant_id_of(REQUEST)) is None


# ---- the compromise ------------------------------------------------------------------------------------------------------------------------------------------

def test_the_compromised_worker_releases_for_a_claimed_request_without_any_ledger_committed_grant(tmp_path):
    led = stub_ledger()
    w = compromised(tmp_path, led=led)
    gid_ = grant_id_of(REQUEST)
    sent = []
    resp = w.release(gid_, transmit=sent.append)
    assert sent == [resp] and resp["grantId"] == gid_ and resp["requestDigest"] == REQUEST and resp["dataId"] == DATA_ID
    assert resp["adapterMode"] == "symbolic" and resp["responseEnvelope"]["kind"] == "symbolic-partial/v1"
    assert resp["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:mallory")
    assert [(e["type"], e["gid"]) for e in w.events()] == [("RELEASE_INTENT", GID), ("RELEASE_SENT", GID)]       # the audit trail is the honest worker's, so the evidence exporter sees it
    assert w.finish_decryption(resp, "keyref:user:mallory")["decryptable"] is True                                # and the capability completes: nothing downstream checks the ledger
    assert led.dbc.calls == []                                                                                    # the claimed release never asked the ledger anything


def test_the_response_is_still_bound_to_the_claimed_recipient_and_no_other_user_completes_it(tmp_path):
    w = compromised(tmp_path)
    resp = w.release(grant_id_of(REQUEST))
    with pytest.raises(WorkerError) as e:
        w.finish_decryption(resp, "keyref:user:alice")
    assert e.value.code == "WRONG_SUBJECT"


def test_a_retry_returns_the_same_cached_response_like_the_honest_release(tmp_path):
    w = compromised(tmp_path)
    first = w.release(grant_id_of(REQUEST))
    again = w.release(grant_id_of(REQUEST))
    assert again == first
    assert [e["type"] for e in w.events()] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]


def test_an_unclaimed_grant_gets_the_honest_refusal_so_the_variant_is_not_allow_everything(tmp_path):
    led = stub_ledger()
    w = compromised(tmp_path, led=led)
    other = grant_id_of("0x" + "e2" * 32)
    with pytest.raises(WorkerError) as e:
        w.release(other)
    assert e.value.code == "NOT_COMMITTED" and led.dbc.calls == [("grantDetails", (other,))] and w.status(other) is None


def test_a_claimed_release_still_needs_a_record_in_the_workers_registry(tmp_path):
    cw = modules()
    w = cw.CompromisedWorker(stub_ledger(), str(tmp_path / "bad"), clock=lambda: NOW, claims=[claim()])        # no record registered
    with pytest.raises(WorkerError) as e:
        w.release(grant_id_of(REQUEST))
    assert e.value.code == "WRONG_SUBJECT" and w.events() == []                                                  # the compromise is exactly "no grant check", nothing else is skipped


def test_the_ledger_object_is_restored_after_a_claimed_release_and_after_a_refused_one(tmp_path):
    led = stub_ledger()
    w = compromised(tmp_path, led=led)
    w.release(grant_id_of(REQUEST))
    assert w.led is led
    with pytest.raises(WorkerError):
        w.release(grant_id_of("0x" + "e2" * 32))
    assert w.led is led


# ---- construction rules --------------------------------------------------------------------------------------------------------------------------------------

def test_the_variant_refuses_a_deployment_that_does_not_declare_test_only_keys_and_creates_nothing(tmp_path):
    cw = modules()
    bad = json.loads(json.dumps(MANIFEST))
    bad["fixture"]["keyDerivation"] = "production HSM"
    with pytest.raises(SystemExit) as e:
        cw.CompromisedWorker(stub_ledger(bad), str(tmp_path / "bad"), clock=lambda: NOW, claims=[claim()])
    assert str(e.value).startswith("refusing:") and "TEST-ONLY" in str(e.value)
    assert not os.path.exists(tmp_path / "bad")


@pytest.mark.parametrize("bad", [
    claim(requestDigest="0x12"), claim(requestDigest=REQUEST.upper()), claim(dataId="nope"), claim(gid="0x12"), claim(recipientKeyRef="keyref:witness:witness-1"), claim(recipientKeyRef="alice"),
    {k: v for k, v in claim().items() if k != "gid"}, {**claim(), "extra": 1}, "not a dict", None,
], ids=["short-digest", "upper-digest", "bad-data-id", "bad-gid", "non-user-key", "no-keyref-syntax", "missing-field", "extra-field", "string", "null"])
def test_a_malformed_claim_is_refused_at_construction(tmp_path, bad):
    cw = modules()
    with pytest.raises(ValueError):
        cw.CompromisedWorker(stub_ledger(), str(tmp_path / "bad"), clock=lambda: NOW, claims=[bad])
    assert not os.path.exists(tmp_path / "bad")


@pytest.mark.parametrize("bad", ["x", {}, None, 7, ({},)], ids=["string", "object", "null", "number", "tuple"])
def test_a_claims_argument_that_is_not_a_list_is_refused(tmp_path, bad):
    cw = modules()
    with pytest.raises(ValueError):
        cw.CompromisedWorker(stub_ledger(), str(tmp_path / "bad"), clock=lambda: NOW, claims=bad)
    assert not os.path.exists(tmp_path / "bad")


REG, OTHER = "0x" + "aa" * 32, "0x" + "bb" * 32


class _Chain:
    def __init__(self, profile, registered):
        self.profile, self.registered = profile, registered

    def call(self, contract, fn, *args):
        return {"profile": self.profile, "recipientKeyHash": self.registered}[fn]


def _recipient_rule(cls, profile, grant_recipient, registered=REG):
    w = cls.__new__(cls)
    w.led, w._forging = SimpleNamespace(pbc=_Chain(profile, registered), PSC=object(), RSC=object()), False
    try:
        return ("ok", w._recipient_for({"gid": "0x" + "11" * 20, "recipientKeyHash": grant_recipient}))
    except WorkerError as e:
        return ("err", e.code, e.message)


@pytest.mark.parametrize("profile", ["0", "1", "2", "3"])
def test_outside_a_claimed_release_the_recipient_rule_is_exactly_the_honest_workers(profile):
    """Only a claimed release forges the recipient; every other call keeps the honest binding rule, on every profile."""
    cw = modules()
    for grant_recipient in (ZERO, REG, OTHER):
        for registered in (REG, ZERO):
            assert _recipient_rule(cw.CompromisedWorker, profile, grant_recipient, registered) == _recipient_rule(Worker, profile, grant_recipient, registered)


def test_two_claims_for_the_same_request_digest_are_refused(tmp_path):
    cw = modules()
    with pytest.raises(ValueError):
        cw.CompromisedWorker(stub_ledger(), str(tmp_path / "bad"), clock=lambda: NOW, claims=[claim(), claim(gid="0x" + "98" * 20)])


# ---- the static production boundary --------------------------------------------------------------------------------------------------------------------------

def test_the_variant_is_not_part_of_the_production_boundary():
    pkg = os.path.join(PROTO, "hmbc_protocol")
    for name in sorted(os.listdir(pkg)):
        if name.endswith(".py"):
            src = open(os.path.join(pkg, name)).read()
            assert not any(m == "testtools" or m.startswith("testtools.") for m in imported_modules(src)), name
            assert "compromised_worker" not in src, name
    for dirpath, _dirs, files in os.walk(os.path.join(PROTO, "exports")):
        for fn in files:
            text = open(os.path.join(dirpath, fn)).read()
            assert "compromised_worker" not in text and "CompromisedWorker" not in text and "testtools" not in text, fn


def test_the_module_is_loudly_test_only_symbolic_and_prints_nothing():
    src = open(os.path.join(PROTO, "testtools", "compromised_worker.py")).read()
    doc = src.split('"""')[1]
    assert "TEST-ONLY" in doc and "SYMBOLIC" in doc.upper() and "no secrecy" in doc.lower()
    assert "print(" not in src and "synthetic_private_key" not in src


# ---- LIVE: the real ledger, the real certificate layer -----------------------------------------------------------------------------------------------------

def test_live_a_working_certificate_layer_does_not_stop_a_compromised_worker_that_releases_an_ungranted_request(live_f, tmp_path):
    import ledger_setup as setup
    from hmbc_protocol.worker import Worker as HonestWorker
    cw = modules()
    led = f_ledger(live_f)
    ctx = setup.setup_pbc(led)                                                    # noqa: F841 (the same bootstrap the carried live tests use)
    witnesses, wview = real_witnesses(live_f, tmp_path)
    accept_checkpoint(live_f, witnesses, wview, led)                              # the certificate layer WORKS: three real witnesses, accepted by the real KSSC
    assert wview.dbc_current_checkpoint()["sequence"] == "1"
    record = {"dataId": setup.DATA_P1, "owner": setup.addr("H2-root"), "payloadDigest": "0x" + __import__("eth_utils").keccak(text="synthetic payload P1").hex()}
    policy = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
    request = "0x" + "e1" * 32
    ungranted = "0x" + eip712.grant_id(bytes.fromhex(request[2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "grantDetails", ungranted)["exists"] is False
    assert led.pbc.call(led.PSC, "getRequest", request)["status"] == "0"          # the PBC never forwarded it either
    honest_w = HonestWorker(led, str(tmp_path / "honest"), clock=led.dbc.now)
    honest_w.encrypt_record(record, policy, "0")
    with pytest.raises(WorkerError) as e:
        honest_w.release(ungranted)                                               # positive control: the honest worker, same ledger, same grant id
    assert e.value.code == "NOT_COMMITTED"
    bad = cw.CompromisedWorker(led, str(tmp_path / "bad"), clock=led.dbc.now,
                               claims=[{"requestDigest": request, "dataId": setup.DATA_P1, "gid": keys.resolve("keyref:user:alice", ("user",))[1], "recipientKeyRef": "keyref:user:alice"}])
    bad.encrypt_record(record, policy, "0")                                       # registered through the REAL encrypt_record: the worker legitimately holds the record
    resp = bad.release(ungranted)
    assert resp["grantId"] == ungranted and resp["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:alice")
    assert bad.finish_decryption(resp, "keyref:user:alice")["decryptable"] is True
    assert led.dbc.call(led.KSSC, "grantDetails", ungranted)["exists"] is False   # the ledger STILL has no such grant, and never will: nothing in it was consulted or changed
    assert led.pbc.call(led.PSC, "getRequest", request)["status"] == "0"
