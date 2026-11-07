"""E regression pins against REAL chains (agent 2, Step 5; the live half of test_e_regression_pins.py). PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic TEST-ONLY keys.

  1. The worker deployment fingerprint on FRESH Anvil pairs for every profile the E suite deploys (repaired-e, paper-strict, paper-minimal and both mutants): historical code == current code on the same
     deployment manifest, and the value is the one A2-0039 measured on fresh chains (`9886222d774b769e`, protocol/evidence/return-review-2026-10-12/fingerprint-measurement.txt) for all six deployments. The
     fingerprint binds chain ids and the PSC/RSC/KSSC/ACSC addresses only, so fresh chains from one deploy script give one value whatever the profile: that is the DOCUMENTED weakness (D-2 of A2-0039), pinned
     here so a change of the formula cannot go unnoticed. If a value differs the test fails and prints it: that is a finding, not a flake.
  2. The DEFAULT worker export on a REAL release flow (a legitimate grant, one release, one retry), written by the current Worker and exported by the HISTORICAL and by the current `worker_log`: the two byte
     strings are equal, non-empty and never contain the raw token (only its keccak digest). Repaired-e (the profile-2 recipient branch) and paper-strict (the paper branch) are both exercised.
Needs Foundry 1.8.5 and the pinned ledger commit like every other live file; with `support.foundry()` it honours HMBC_FOUNDRY_DIR. READ THE SKIP COUNT: a live fixture skips, it does not fail, when Foundry is missing.
"""
import json

import pytest
from eth_utils import keccak

from hmbc_protocol.worker import Worker
from test_e_regression_pins import PROTO, hist, probe, probe_script, run_py, sha256_bytes  # noqa: F401  (hist and probe_script are fixtures)
from test_paper_profile import paper_grant
from test_worker import P1_POLICY, P1_RECORD, grant

FRESH_FINGERPRINT_PREFIX = "9886222d774b769e"          # A2-0039: the same on fresh chains for repaired-e (twice), both mutants, paper-strict and paper-minimal
PROFILE_FIXTURES = [("repaired-e", "ledger_chains"), ("paper-strict", "ledger_chains_paper"), ("paper-minimal", "ledger_chains_paper_minimal"),
                    ("mutant-no-nonce", "ledger_chains_no_nonce"), ("mutant-no-receipt-binding", "ledger_chains_no_receipt_binding")]


def test_the_worker_fingerprint_on_fresh_chains_is_the_measured_value_under_the_historical_and_the_current_code(request, tmp_path, hist, probe_script):
    values = {}
    for profile, fixture in PROFILE_FIXTURES:
        chains = request.getfixturevalue(fixture)
        manifest = tmp_path / f"{profile}.json"
        manifest.write_text(json.dumps(chains.deployment))
        assert chains.deployment["profile"] == profile
        old = probe(hist, probe_script, manifest, tmp_path / f"{profile}-hist")
        new = probe(PROTO, probe_script, manifest, tmp_path / f"{profile}-cur")
        assert old == new, f"{profile}: the historical and the current fingerprint differ ({old[:16]} vs {new[:16]})"
        values[profile] = new
    assert {p: v[:16] for p, v in values.items()} == {p: FRESH_FINGERPRINT_PREFIX for p, _ in PROFILE_FIXTURES}, {p: v[:16] for p, v in values.items()}
    assert len(set(values.values())) == 1                  # one value for all five: the profile is not part of the fingerprint (D-2)


def export_bytes(tree, state):
    p = run_py(tree, ["-m", "hmbc_protocol.worker_log", "--state-dir", str(state)])
    assert p.returncode == 0 and p.stderr == b"", (p.returncode, p.stderr[-300:])
    assert len(p.stdout) > 100, "an empty export would make the comparison vacuous"
    return p.stdout


@pytest.mark.parametrize("flow", ["repaired-e", "paper-strict"])
def test_the_default_worker_export_of_a_real_release_flow_is_byte_identical_under_the_historical_and_the_current_code(request, tmp_path, hist, flow):
    led, ctx = request.getfixturevalue("world" if flow == "repaired-e" else "world_paper")
    _, grant_id = grant(led, ctx) if flow == "repaired-e" else paper_grant(led, ctx)
    state = tmp_path / "state"
    w = Worker(led, state, clock=led.dbc.now)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    resp = w.release(grant_id)
    again = w.release(grant_id)                            # a retry: a second recorded attempt, the same cached response
    assert again == resp
    w.db.close()
    historical, current = export_bytes(hist, state), export_bytes(PROTO, state)
    assert historical == current, (sha256_bytes(historical)[:16], sha256_bytes(current)[:16])
    doc = json.loads(current)
    assert [e["type"] for e in doc["events"]] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]
    assert doc["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "2"} and len(doc["releases"]) == 1
    token = resp["responseEnvelope"]["token"]
    assert token.encode() not in current and token[2:].encode() not in current
    assert doc["releases"][0]["tokenDigest"] == "0x" + keccak(bytes.fromhex(token[2:])).hex()
    assert (doc["releases"][0]["delivery"], doc["releases"][0]["sendAttempts"], doc["releases"][0]["completedAttempts"]) == ("unknown", 2, 2)
