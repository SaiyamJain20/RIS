"""Agent 3's E0 supplement revision 2 (A3-0016): the two prospective mutant-killing controls, MEASURED on the live pinned ledger.

Nothing here is an E1/E2 result: the runner role is played by this test and the controls run on a local Anvil pair. They exist so that agent 2's answer to
A3-0016 can state measured outcomes (and measured non-outcomes) instead of static reasoning. Receipt fixtures come from the TEST-ONLY deviating-witness tool
(protocol/testtools), which is outside the production adapter boundary and returns only a signed artifact.
"""
import json
import pathlib
import subprocess
import sys

import pytest

from hmbc_protocol import chain, eip712
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness
import ledger_setup as setup

PROTOCOL = pathlib.Path(__file__).resolve().parents[1]
OUTCOME = "0x" + "ab" * 32
FIELDS = ["requestDigest", "gid", "dataId"]


def tool(tmp_path, led, *args):
    dep = tmp_path / "deployment.json"
    dep.write_text(json.dumps(led.deployment))
    p = subprocess.run([sys.executable, "-m", "testtools.deviating_witness", "--deployment", str(dep), *args], cwd=PROTOCOL,
                       env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=60)
    return p


def granted(led, ctx, nonce="1", ttl=30):
    """A fresh forwarded AND granted request (the supplement's per-trial precondition)."""
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce=nonce, ttl=ttl))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    grant_id = relay.deliver(signed, w.decide(signed["requestDigest"]))
    assert grant_id is not None
    return signed, grant_id


def status(led, digest):
    return led.pbc.call(led.PSC, "getRequest", digest)["status"]


# ------------------------------------------------------------------ receipt binding -------------------------------------------------------

def test_the_positive_counterpart_records_the_outcome(world):
    led, ctx = world
    signed, grant_id = granted(led, ctx)
    Relay(led, "relay").report_outcome(signed["requestDigest"], OUTCOME, Witness(led).attest_grant(grant_id))
    assert status(led, signed["requestDigest"]) == "2"


@pytest.mark.parametrize("field", FIELDS)
def test_repaired_e_rejects_a_validly_resigned_inconsistent_receipt_with_wrong_subject(world, tmp_path, field):
    led, ctx = world
    signed, grant_id = granted(led, ctx)
    p = tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", field)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["deviation"]["field"] == field and out["deviation"]["original"] != out["deviation"]["altered"]
    assert out["receipt"][field] == out["deviation"]["altered"]                     # the inconsistent field is retained, never normalised away
    with pytest.raises(chain.Rejected) as e:
        Relay(led, "relay").report_outcome(signed["requestDigest"], OUTCOME, out)
    assert e.value.code == "WRONG_SUBJECT"
    assert status(led, signed["requestDigest"]) == "1"                             # still FORWARDED: no outcome, no transition


@pytest.mark.parametrize("field", FIELDS)
def test_mutant_no_receipt_binding_accepts_the_same_inconsistent_receipt(world_no_receipt_binding, tmp_path, field):
    led, ctx = world_no_receipt_binding
    assert led.pbc.call(led.PSC, "mutations") == "32"                              # exactly MUT_NO_RECEIPT_BINDING
    signed, grant_id = granted(led, ctx)
    out = json.loads(tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", field).stdout)
    Relay(led, "relay").report_outcome(signed["requestDigest"], OUTCOME, out)      # accepted although receipt.%s != the forwarded record
    assert status(led, signed["requestDigest"]) == "2"
    assert out["receipt"][field] == out["deviation"]["altered"] != out["deviation"]["original"]


@pytest.mark.parametrize("field", FIELDS)
def test_unchanged_signature_control_is_a_rejection_in_both_but_with_different_precedence(world, world_no_receipt_binding, field):
    """Not a mutant killer: both reject, so rejection alone cannot tell the profiles apart (A3-0016, A1-0020 correction). Measured precedence:
    repaired-e fails the binding check first (WRONG_SUBJECT); with only the binding guard removed the unchanged signature fails the quorum (BAD_SIGNATURE)."""
    for (led, ctx), expected in ((world, "WRONG_SUBJECT"), (world_no_receipt_binding, "BAD_SIGNATURE")):
        signed, grant_id = granted(led, ctx)
        rc = Witness(led).attest_grant(grant_id)
        altered = {**rc["receipt"], field: ("0x" + "77" * 20) if field == "gid" else ("0x" + "77" * 32)}
        with pytest.raises(chain.Rejected) as e:
            Relay(led, "relay").report_outcome(signed["requestDigest"], OUTCOME, {"receipt": altered, "signatures": rc["signatures"]})
        assert e.value.code == expected, (field, e.value.code)
        assert status(led, signed["requestDigest"]) == "1"


# ------------------------------------------------------------------ tool boundary -------------------------------------------------------------

def test_the_tool_is_not_part_of_the_production_adapter_boundary():
    code = "import sys, hmbc_protocol.adapter, hmbc_protocol.export; print(any('testtools' in m for m in sys.modules))"
    p = subprocess.run([sys.executable, "-c", code], cwd=PROTOCOL, env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert p.stdout.strip() == "False", p.stderr
    manifest = (PROTOCOL / "exports" / "adapter.json").read_text()
    assert "deviating" not in manifest and "testtools" not in manifest
    assert not any("testtools" in f.read_text() for f in (PROTOCOL / "hmbc_protocol").glob("*.py"))


def test_the_tool_refuses_a_deployment_that_is_not_marked_test_only(world, tmp_path):
    led, ctx = world
    dep = json.loads(json.dumps(led.deployment))
    dep["fixture"]["keyDerivation"] = "production keys"
    f = tmp_path / "d.json"
    f.write_text(json.dumps(dep))
    p = subprocess.run([sys.executable, "-m", "testtools.deviating_witness", "--deployment", str(f), "receipt", "--grant-id", "0x" + "55" * 32, "--field", "gid"],
                       cwd=PROTOCOL, env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=60)
    assert p.returncode != 0 and "TEST-ONLY" in p.stderr and p.stdout == ""


def test_the_tool_signs_only_for_a_grant_that_exists_and_only_for_the_three_bound_fields(world, tmp_path):
    led, ctx = world
    assert tool(tmp_path, led, "receipt", "--grant-id", "0x" + "55" * 32, "--field", "gid").returncode != 0           # no such grant: nothing signed
    signed, grant_id = granted(led, ctx)
    for bad in ("keyEpoch", "dbcBlockHash", "grantId", "kssc", ""):
        p = tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", bad)
        assert p.returncode != 0 and p.stdout == "", bad


def test_the_tool_prints_no_private_key(world, tmp_path):
    led, ctx = world
    signed, grant_id = granted(led, ctx)
    p = tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", "gid")
    from hmbc_protocol import keys
    k = keys.synthetic_private_key("witness-1")
    assert k not in p.stdout + p.stderr and k[2:] not in p.stdout + p.stderr


# ------------------------------------------------------------------ nonce control (honest pre-collected certificates) -------------------------

def nonce_schedule(led, ctx):
    """Supplement E01-same-nonce-distinct-digests-repaired-e: two valid requests, same gid/nonce, different digests; BOTH forwarded before ONE checkpoint;
    BOTH honestly certified before either is consumed; consume the first, then the second ALREADY-ISSUED certificate (the witness is not asked again)."""
    client, relay, w = UserClient("alice", led.deployment), Relay(led, "relay"), Witness(led)
    a = client.sign_request(setup.make_request(led, ctx, client, nonce="1", ttl=30))
    b = client.sign_request(setup.make_request(led, ctx, client, nonce="1", ttl=20))
    assert a["requestDigest"] != b["requestDigest"] and a["request"]["nonce"] == b["request"]["nonce"]
    assert relay.forward(a, ctx.bundle).code == "NONE" and relay.forward(b, ctx.bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    ca, cb = w.decide(a["requestDigest"]), w.decide(b["requestDigest"])
    assert ca["decision"]["result"] == cb["decision"]["result"] == "1"             # each saw nonceConsumed=false: the honest witness signs both
    first = relay.deliver(a, ca)
    assert first is not None and led.dbc.call(led.KSSC, "getGrant", first)[5] is True      # the first grant exists in every profile
    return a, b, ca, cb, first


def consume_raw(led, request, bundle):
    cert = {"decision": bundle["decision"], "signatures": bundle["signatures"]}
    return led.dbc.send(setup.key("relay"), led.ACSC, "consumeDecision", request, cert, bundle["credentialRecords"])


def test_nonce_control_repaired_e_the_second_consumption_reverts_replay(world):
    led, ctx = world
    a, b, ca, cb, first = nonce_schedule(led, ctx)
    assert led.dbc.call(led.KSSC, "nonceConsumed", ctx.alice, "1") is True                # the guard recorded the nonce
    before = led.dbc.call(led.KSSC, "getGrant", first)
    with pytest.raises(chain.Rejected) as e:
        consume_raw(led, b["request"], cb)
    assert e.value.code == "REPLAY"
    second_id = "0x" + eip712.grant_id(bytes.fromhex(b["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "getGrant", second_id)[5] is False                # no second grant
    assert led.dbc.call(led.KSSC, "getGrant", first) == before                      # the first grant is unchanged


def test_nonce_control_mutant_no_nonce_issues_a_second_distinct_grant(world_no_nonce):
    led, ctx = world_no_nonce
    assert led.pbc.call(led.PSC, "profile") == "2" and led.dbc.call(led.KSSC, "mutations") == "8"      # MUT_NO_NONCE only
    a, b, ca, cb, first = nonce_schedule(led, ctx)
    assert led.dbc.call(led.KSSC, "nonceConsumed", ctx.alice, "1") is False               # measured: this mutant never records the nonce at all
    consume_raw(led, b["request"], cb)                                              # accepted: the guard is gone
    second_id = "0x" + eip712.grant_id(bytes.fromhex(b["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert second_id != first and led.dbc.call(led.KSSC, "getGrant", second_id)[5] is True


# ------------------------------------------------------------------ revision 6: build the deviating receipt at the HONEST receipt's DBC block --------------------

def test_the_tool_can_build_its_receipt_at_the_honest_receipts_block_so_only_one_field_differs(world, tmp_path):
    """A3-0018/DELTA: the collector compares the deviating receipt with the honest one field by field. Under interval mining the DBC head moves between the two calls, which
    would change dbcBlockNumber/dbcBlockHash too; --at-block N pins the tool to the honest receipt's block so exactly the altered field differs."""
    from support import rpc
    led, ctx = world
    signed, grant_id = granted(led, ctx)
    honest = Witness(led).attest_grant(grant_id)["receipt"]
    for _ in range(3):
        rpc(led.dbc.url, "evm_mine")                                               # the head moves on
    moved = json.loads(tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", "gid").stdout)["receipt"]
    assert moved["dbcBlockNumber"] != honest["dbcBlockNumber"]                     # without the flag the unchanged fields would differ too
    out = json.loads(tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", "gid", "--at-block", honest["dbcBlockNumber"]).stdout)
    diff = {k for k in honest if honest[k] != out["receipt"][k]}
    assert diff == {"gid"}                                                         # exactly the altered field
    assert out["receipt"]["dbcBlockHash"] == honest["dbcBlockHash"]


def test_the_tool_refuses_a_block_that_does_not_exist_or_predates_the_grant(world, tmp_path):
    led, ctx = world
    before = led.dbc.get_block()["number"]
    signed, grant_id = granted(led, ctx)
    for block in (str(before), "99999999", "-1", "x", "1.5", "", "0x5"):
        p = tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", "gid", "--at-block", block)
        assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr, (block, p.stderr)


def test_at_block_accepts_only_a_plain_decimal_block_number(world, tmp_path):
    """int() would accept '+N', ' N' and 'N_n' for a block that DOES hold the grant; only the tool's own format check refuses them (the plain form works)."""
    led, ctx = world
    signed, grant_id = granted(led, ctx)
    n = str(Witness(led).attest_grant(grant_id)["receipt"]["dbcBlockNumber"])
    assert len(n) >= 2
    ok = tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", "gid", "--at-block", n)
    assert ok.returncode == 0, ok.stderr
    for spelled in (f"+{n}", f" {n}", n[:-1] + "_" + n[-1], "0" + n):
        p = tool(tmp_path, led, "receipt", "--grant-id", grant_id, "--field", "gid", "--at-block", spelled)
        expect_refused = spelled != "0" + n                                       # leading zeros are plain decimal digits and stay valid
        assert (p.returncode != 0) == expect_refused, (spelled, p.stderr)
        assert p.returncode != 0 and "refusing" in p.stderr if expect_refused else p.returncode == 0
