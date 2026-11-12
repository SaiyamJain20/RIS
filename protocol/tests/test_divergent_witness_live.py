"""The real-PROCESS divergent-view witness against the real pool and a real ledger (agent 2, F phase; gap G2; conditional rows F-16, F-17, F-18, F-31). Written BEFORE it was run. PAPER-DERIVED
RECONSTRUCTION; synthetic TEST-ONLY keys; one host; one local Anvil pair with agent 1's F ledger (85c59f5); the divergence is deliberate (H3 breaks the safe-ledger assumption by design).

The adapter is started through the TEST-ONLY alternate entry (`--witness-variant 3=view:SPEC`); witness 3 is `testtools.divergent_witness`, the other three are production witnesses. As in the G1 live test,
one HONEST witness is SIGSTOPped where the outcome must not depend on reply order, so the certificate needs the divergent witness:
  authEpoch:1       witness 3 reads authEpoch + 1 at the proposal's block: it refuses (PROPOSAL_MISMATCH), the pool has two valid signers and classifies QUORUM_UNAVAILABLE with witness 3 `refused`;
  policyVersion:1   the same with policyVersion;
  headLag:2         witness 3's PBC is two blocks behind: the proposal's block is one it cannot see: refused, the same classification;
  control           with all four running, the certificate forms from the three honest witnesses and the divergent one is never in it.
Not claimed: that any F oracle accepts these runs; anything about clocks, reorgs or independent hosts. The two no-quorum cases wait for the pool's 10 s cap."""
import os
import signal

from test_byzantine_witness_live import release, signers, witnesses  # noqa: F401
from test_faulty_adapter_v2_live import FAULTY, Adapter, evidence, fresh_blocks, statuses  # noqa: F401
from test_mutant_tree_live import wait_pid
from test_rpc_binding_view_live import f_ledger, live_f, mine  # noqa: F401  (live_f and f_ledger are fixtures)


def view_adapter(live_f, tmp_path, spec, stop=None):
    fresh_blocks(live_f)
    fresh_blocks(live_f)                                              # the PBC head must be above headLag so the lagged head is a real block
    a = Adapter(live_f, tmp_path, FAULTY, ["--witness-variant", "3=view:" + spec])
    pid = None
    if stop is not None:
        pid = wait_pid(a, stop)
        os.kill(pid, signal.SIGSTOP)
    return a, pid


def end(a, pid):
    if pid is None:
        return a.close()
    return release(a, pid)


def no_quorum(a):
    r = a.ask("collect_checkpoint", {}, timeout=90)
    assert r["ok"] is False, r
    err = r["error"]
    assert err["code"] == "ADAPTER_UNAVAILABLE" and err.get("reason") == "QUORUM_UNAVAILABLE", err
    coll = err["collection"]
    assert coll["submittedSigners"] == []
    return [o["status"] for o in coll["outcomes"]]


def test_f16_a_witness_that_reads_another_auth_epoch_refuses_and_is_classified_not_counted(live_f, tmp_path):
    a, pid = view_adapter(live_f, tmp_path, "authEpoch:1", stop=2)
    try:
        assert no_quorum(a) == ["signed", "signed", "silent", "refused"]
    finally:
        rc, err = end(a, pid)
    assert rc == 0 and err == "", (rc, err)


def test_f17_a_witness_that_reads_another_policy_version_refuses_and_is_classified_not_counted(live_f, tmp_path):
    a, pid = view_adapter(live_f, tmp_path, "policyVersion:1", stop=2)
    try:
        assert no_quorum(a) == ["signed", "signed", "silent", "refused"]
    finally:
        rc, err = end(a, pid)
    assert rc == 0 and err == "", (rc, err)


def test_f18_a_witness_whose_pbc_lags_cannot_see_the_proposals_block_and_refuses(live_f, tmp_path):
    a, pid = view_adapter(live_f, tmp_path, "headLag:2", stop=2)
    try:
        assert no_quorum(a) == ["signed", "signed", "silent", "refused"]
    finally:
        rc, err = end(a, pid)
    assert rc == 0 and err == "", (rc, err)


def test_control_with_all_four_running_the_certificate_forms_without_the_divergent_witness(live_f, tmp_path):
    a, pid = view_adapter(live_f, tmp_path, "authEpoch:1")
    try:
        r = a.ask("collect_checkpoint", {})
        assert r["ok"] is True, r
        res = r["result"]
        got = signers(live_f, res)
        assert len(res["signatures"]) == 3 and set(got) == set(witnesses(live_f)[:3]) and len(set(got)) == 3      # witnesses 0, 1, 2; witness 3 diverges and is not in it
    finally:
        rc, err = end(a, pid)
    assert rc == 0 and err == "", (rc, err)
