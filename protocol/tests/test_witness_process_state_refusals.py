"""Process-level durable-state refusals and the rollback limit of a witness PROCESS (agent 2, F task 3; INVENTORY section 4 row F-27, hook H7). Written BEFORE any of it was run.

Every test here starts the PRODUCTION `hmbc_protocol.witness_main` against a REAL deployment (real Anvil nodes, agent 1's F ledger snapshot 85c59f5; skipped when Foundry or the commit is missing). The store
is checked AFTER the D50 stages, so none of this is reachable without a chain; the store-level versions of the same refusals are in test_witness_state.py. Two groups, deliberately different:

  REFUSED (fail closed, SUCCESSOR-WIRE section 1 stage 9): a corrupt database, a missing database behind an INITIALIZED marker, record rows without a marker, a marker that disagrees with the database, a
  store bound to ANOTHER deployment (BINDING_MISMATCH), and a store that belongs to ANOTHER witness key (OWNER_MISMATCH). Each ends as ONE closed JSON line on stderr (code, message, reason), exit 2, nothing on
  stdout, no traceback, and NOTHING written: the store's logical snapshot or the file bytes are unchanged.

  NOT REFUSED, by design (the F-27 limit, INVENTORY FM-14): a CONSISTENT rollback to an older valid copy is not detectable locally. A copy of the main database file ALONE also drops committed rows that still
  sit in the write-ahead log, so it is exactly such a rollback. The test measures it: a witness started on a main-file-only copy signs a DIFFERENT value for a key the original already signed (equivocation);
  the control, a consistent copy (main file + -wal + marker, taken while no writer is active), keeps the pin. This is an ASSUMPTION VIOLATION (the runner's file copy is outside the model), a tested
  reconstruction result, not a defect that a refusal could remove.

Process death is the only crash mode used anywhere; power loss and OS crashes are untested.
"""
import hashlib
import json
import os
import shutil

import pytest

from hmbc_protocol import witness_state as ws
from testtools import state_oracle

from test_faulty_witness import expected_signature, production, two_checkpoints
from test_rpc_binding_view_live import WitnessProc, live_f, live_f_fresh  # noqa: F401  (live_f, live_f_fresh are fixtures)


def store_dir(tmp_path, index, state="wstate"):
    return str(tmp_path / state / ("witness-%d" % index))


def start(live, tmp_path, index, state="wstate"):
    """Start the production witness, send nothing and close stdin: a clean start exits 0, a refused one exits 2 with ONE JSON line. Returns (rc, stdout, stderr)."""
    p = WitnessProc(live, tmp_path, index, state=state)
    out, err = p.p.communicate(timeout=120)
    return p.p.returncode, out, err


def refusal(result):
    rc, out, err = result
    assert rc == 2 and out == "" and "Traceback" not in err, (rc, out, err[-300:])
    lines = err.strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and set(obj["error"]) >= {"code", "message"}
    return obj["error"]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def listing(d):
    return sorted(os.listdir(d))


def initialised(live, tmp_path, index, state="wstate"):
    assert start(live, tmp_path, index, state) == (0, "", "")
    return store_dir(tmp_path, index, state)


# ---- offline: the state directory itself ------------------------------------------------------------------------------------------------------------------

def test_a_state_directory_that_group_or_other_can_reach_is_refused_by_the_process_before_any_chain_is_asked(tmp_path):
    import subprocess
    import sys
    proto = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    fx = os.path.join(proto, "tests", "fixtures")
    state = tmp_path / "state"
    state.mkdir()
    os.chmod(state, 0o755)
    p = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.witness_main", "--deployment", os.path.join(fx, "agent1-85c59f5-f-base-deployment.json"), "--abi-dir",
                        os.path.join(fx, "agent1-85c59f5-abi"), "--index", "0", "--key-label", "witness-1", "--state-dir", str(state)], capture_output=True, text=True, cwd=proto,
                       env={"PYTHONPATH": proto, "PATH": "/usr/bin:/bin"}, timeout=60)
    err = refusal((p.returncode, p.stdout, p.stderr))
    assert err["code"] == "MALFORMED" and "chmod 700" in err["message"]
    assert os.listdir(state) == []


# ---- the control ----------------------------------------------------------------------------------------------------------------------------------------------

def test_live_a_fresh_state_is_initialised_and_a_second_start_reopens_it_without_changing_it(live_f, tmp_path):
    d = initialised(live_f, tmp_path, 0)
    snap = state_oracle.logical_snapshot(d)
    assert start(live_f, tmp_path, 0) == (0, "", "")
    assert state_oracle.logical_snapshot(d) == snap and {"signing.sqlite", "INITIALIZED"} <= set(listing(d))


# ---- refused: corrupt, missing, inconsistent -----------------------------------------------------------------------------------------------------------------

def test_live_a_corrupt_database_is_refused_store_corrupt_and_the_bytes_are_left_alone(live_f, tmp_path):
    d = initialised(live_f, tmp_path, 0)
    db = os.path.join(d, "signing.sqlite")
    for side in ("-wal", "-shm"):
        if os.path.exists(db + side):
            os.remove(db + side)
    open(db, "wb").write(b"this is not a database " * 200)
    before, names = sha(db), listing(d)
    err = refusal(start(live_f, tmp_path, 0))
    assert (err["code"], err["reason"]) == ("ADAPTER_UNAVAILABLE", "STORE_CORRUPT"), err
    assert sha(db) == before and listing(d) == names                                      # not repaired, not replaced, nothing created


def test_live_a_missing_database_behind_an_initialized_marker_is_refused_store_missing_and_nothing_is_recreated(live_f, tmp_path):
    d = initialised(live_f, tmp_path, 0)
    for name in ("signing.sqlite", "signing.sqlite-wal", "signing.sqlite-shm"):
        if os.path.exists(os.path.join(d, name)):
            os.remove(os.path.join(d, name))
    names = listing(d)
    err = refusal(start(live_f, tmp_path, 0))
    assert (err["code"], err["reason"]) == ("ADAPTER_UNAVAILABLE", "STORE_MISSING"), err
    assert listing(d) == names and "signing.sqlite" not in names                           # a deleted store is never silently recreated under an old marker


def test_live_record_rows_without_the_marker_are_refused_store_corrupt(live_f, tmp_path):
    a, _b = two_checkpoints(live_f)
    first = WitnessProc(live_f, tmp_path, 0)
    assert first.ask("checkpoint", a)["type"] == "signature"
    assert first.close() == (0, "")
    d = store_dir(tmp_path, 0)
    os.remove(os.path.join(d, "INITIALIZED"))
    snap = state_oracle.logical_snapshot(d)
    err = refusal(start(live_f, tmp_path, 0))
    assert (err["code"], err["reason"]) == ("ADAPTER_UNAVAILABLE", "STORE_CORRUPT"), err
    assert state_oracle.logical_snapshot(d) == snap and "INITIALIZED" not in listing(d)    # the witness does not re-bless a store that already holds signing history


def test_live_a_marker_that_disagrees_with_the_database_is_refused_store_corrupt(live_f, tmp_path):
    d = initialised(live_f, tmp_path, 0)
    marker = os.path.join(d, "INITIALIZED")
    m = json.load(open(marker))
    m["binding_v2"] = "f" * 64
    open(marker, "w").write(json.dumps(m, sort_keys=True, separators=(",", ":")))
    before = sha(marker)
    err = refusal(start(live_f, tmp_path, 0))
    assert (err["code"], err["reason"]) == ("ADAPTER_UNAVAILABLE", "STORE_CORRUPT"), err
    assert sha(marker) == before


# ---- refused: the wrong deployment and the wrong key --------------------------------------------------------------------------------------------------------

def test_live_a_store_bound_to_another_deployment_is_refused_binding_mismatch_and_unchanged(live_f, live_f_fresh, tmp_path):
    d = initialised(live_f, tmp_path, 0)
    snap = state_oracle.logical_snapshot(d)
    err = refusal(start(live_f_fresh, tmp_path, 0))                                       # the same state directory, a DIFFERENT real deployment
    assert (err["code"], err["reason"]) == ("WRONG_DESTINATION", "BINDING_MISMATCH"), err
    assert state_oracle.logical_snapshot(d) == snap


def test_live_a_store_copied_into_another_witnesss_slot_is_refused_owner_mismatch_and_unchanged(live_f, tmp_path):
    initialised(live_f, tmp_path, 0)
    shutil.copytree(store_dir(tmp_path, 0), store_dir(tmp_path, 1))                         # the runner's own file copy: witness 0's store in witness 1's directory
    snap = state_oracle.logical_snapshot(store_dir(tmp_path, 1))
    err = refusal(start(live_f, tmp_path, 1))
    assert (err["code"], err["reason"]) == ("WRONG_DESTINATION", "OWNER_MISMATCH"), err
    assert state_oracle.logical_snapshot(store_dir(tmp_path, 1)) == snap


# ---- NOT refused, by design: the rollback limit ---------------------------------------------------------------------------------------------------------------

def copy_state(src_state, dst_state, index, files):
    s, d = os.path.join(src_state, "witness-%d" % index), os.path.join(dst_state, "witness-%d" % index)
    os.makedirs(d)
    os.chmod(dst_state, 0o700)                              # makedirs applies `mode` to the leaf only: the state directory itself must be private or the witness (rightly) refuses it
    os.chmod(d, 0o700)
    for name in files:
        shutil.copy2(os.path.join(s, name), os.path.join(d, name))


def test_live_f27_a_consistent_copy_keeps_the_pin_but_a_main_file_only_copy_is_an_undetected_rollback(live_f, tmp_path):
    a, b = two_checkpoints(live_f)
    original = WitnessProc(live_f, tmp_path, 3)
    try:
        sig_a = original.ask("checkpoint", a)
        assert sig_a["type"] == "signature" and sig_a["signature"] == expected_signature(live_f, 3, a)
        src = str(tmp_path / "wstate")
        live_dir = os.path.join(src, "witness-3")
        assert os.path.getsize(os.path.join(live_dir, "signing.sqlite-wal")) > 0           # the committed row lives in the write-ahead log, not (only) in the main file
        # the runner's two file copies, taken while the process is alive and idle (no writer is active at this instant)
        copy_state(src, str(tmp_path / "consistent"), 3, ["signing.sqlite", "signing.sqlite-wal", "INITIALIZED"])
        copy_state(src, str(tmp_path / "mainonly"), 3, ["signing.sqlite", "INITIALIZED"])
    finally:
        assert original.close() == (0, "")
    consistent = WitnessProc(live_f, tmp_path, 3, state="consistent")
    try:
        r = consistent.ask("checkpoint", b)
        assert r["type"] == "error" and r["reason"] == "CONFLICT_PINNED" and r["recorded"]["message"] == a, r      # the consistent copy still knows A
    finally:
        assert consistent.close() == (0, "")
    rolled_back = WitnessProc(live_f, tmp_path, 3, state="mainonly")                       # NOT refused: it starts, because an older valid store is indistinguishable from the real one
    try:
        r = rolled_back.ask("checkpoint", b)
        assert r["type"] == "signature" and r["message"] == b and r["signature"] == expected_signature(live_f, 3, b), r
    finally:
        assert rolled_back.close() == (0, "")
    # equivocation: the SAME key signed two different checkpoints for the same sequence, one in each lineage. This is the F-27 assumption violation made concrete, not a bug a refusal could fix.
    assert expected_signature(live_f, 3, a) != expected_signature(live_f, 3, b)
