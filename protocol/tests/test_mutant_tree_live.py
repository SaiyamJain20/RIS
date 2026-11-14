"""F-plan source mutants M1 and M2 as REAL supervised witness PROCESSES against a real ledger (agent 2, F phase; gap G3; rows F-12 and F-13). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys; one host;
process death by SIGKILL only; one trial each. The mutants are DELIBERATE single-site source edits of the F plan, not observed vulnerabilities.

The adapter is started through the TEST-ONLY alternate entry (`--witness-variant I=mutant:ID --mutant-tree ID=DIR`) as a real long-running process on a real Anvil pair with agent 1's F ledger (85c59f5): witness I
is `testtools.mutant_run` -> exec -> `hmbc_protocol.witness_main` from the mutated tree, the other three are the production witnesses. What each test shows, with its production control in the SAME run:
  M1 (no durable conflict record, F-12): a mutant witness signs checkpoint A and then a DIFFERENT checkpoint B for the same sequence (two valid signed values from one witness, no refusal) and its evidence holds
     no pin; the production witness 2 refuses B as CONFLICT_PINNED with the recorded A.
  M2 (signature emitted before the durable commit, F-12/F-13): witness 1 replies, but its record is NOT in its store (witnesses 2 and 3 have theirs); killed after the reply it comes back with no memory and signs a
     DIFFERENT checkpoint for the same sequence. The production variant of the same row (F-13, `crash:after_commit`, in test_faulty_adapter_v2_live.py) keeps the pin durable and refuses B.
The live fixture is the one of test_rpc_binding_view_live.py (a module-scoped Anvil pair, honouring HMBC_FOUNDRY_DIR). Not claimed: that any oracle accepts these runs; anything about consensus or timing."""
import os
import signal
import time

from test_faulty_adapter_v2_live import FAULTY, PRODUCTION, Adapter, evidence, fresh_blocks, statuses, wait_dead  # noqa: F401
from test_rpc_binding_view_live import f_ledger, live_f, mine  # noqa: F401  (live_f and f_ledger are fixtures)

from testtools import mutant_tree


def wait_pid(adapter, index, seconds=60):
    """The pid of witness `index`, once the adapter has started its children (the pid file appears after the adapter's own start-up validation, not when the process is spawned)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            return adapter.pid(index)
        except (OSError, AssertionError):
            time.sleep(0.2)
    raise TimeoutError("witness %d was never started" % index)


def built(tmp_path, mid):
    dest = str(tmp_path / ("tree-" + mid))
    mutant_tree.build(mid, dest)
    return dest


def test_m1_a_witness_without_a_durable_conflict_record_signs_two_checkpoints_for_one_sequence_where_the_production_witness_refuses(live_f, tmp_path):
    fresh_blocks(live_f)
    a = Adapter(live_f, tmp_path, FAULTY, ["--witness-variant", "1=mutant:M1", "--mutant-tree", "M1=" + built(tmp_path, "M1")])
    try:
        first1 = a.ask("collect_checkpoint", {"witnessIndex": "1"})
        first2 = a.ask("collect_checkpoint", {"witnessIndex": "2"})                              # the production control signs the same first proposal
        assert first1["ok"] is True and first2["ok"] is True and first1["result"]["checkpoint"] == first2["result"]["checkpoint"]
        assert evidence(a.state_dir, 1)["conflicts"] == [] and len(evidence(a.state_dir, 2)["conflicts"]) == 1          # M1 never wrote the pin; the production witness did
        mine(live_f, "pbc")                                                                      # a DIFFERENT proposal for the same sequence (a newer source block)
        second1 = a.ask("collect_checkpoint", {"witnessIndex": "1"})
        assert second1["ok"] is True, second1                                                    # the mutant signs it: no refusal
        c1, c2 = first1["result"]["checkpoint"], second1["result"]["checkpoint"]
        assert c2["sequence"] == c1["sequence"] and c2 != c1                                     # two different signed values for ONE sequence from ONE witness
        assert second1["result"]["signatures"] != first1["result"]["signatures"]
        control = a.ask("collect_checkpoint", {"witnessIndex": "2"})                             # the production witness refuses the same different proposal
        assert control["ok"] is False and control["error"]["code"] == "STALE_STATE" and control["error"]["reason"] == "CONFLICT_PINNED", control
        assert control["error"]["recorded"] == {"message": c1, "signature": first2["result"]["signatures"][0]}
        assert evidence(a.state_dir, 1)["conflicts"] == [] and len(evidence(a.state_dir, 2)["conflicts"]) == 1
    finally:
        rc, err = a.close()
    assert rc == 0 and err == "", (rc, err)


def test_m2_a_witness_that_replies_before_its_commit_has_no_pin_after_being_killed_and_then_signs_a_conflicting_checkpoint(live_f, tmp_path):
    fresh_blocks(live_f)
    a = Adapter(live_f, tmp_path, FAULTY, ["--witness-variant", "1=mutant:M2", "--mutant-tree", "M2=" + built(tmp_path, "M2")])
    pid0 = None
    try:
        pid0 = wait_pid(a, 0)
        os.kill(pid0, signal.SIGSTOP)                                                            # witness 0 is stopped, so the quorum NEEDS witness 1's reply
        first = a.ask("collect_checkpoint", {})
        assert first["ok"] is True, first
        res = first["result"]
        assert statuses(res) == ["silent", "signed", "signed", "signed"], statuses(res)          # the reply of the M2 witness LEFT the process
        assert len(set(res["signatures"])) == 3
        assert evidence(a.state_dir, 1)["conflicts"] == []                                       # ...but its record is not in its store: the transaction is still open
        assert len(evidence(a.state_dir, 2)["conflicts"]) == 1 and len(evidence(a.state_dir, 3)["conflicts"]) == 1
        pid1 = a.pid(1)
        os.kill(pid1, signal.SIGKILL)
        assert wait_dead(pid1), "witness 1 did not die"
        assert evidence(a.state_dir, 1)["conflicts"] == []                                       # and nothing was committed by the death either
        os.kill(pid0, signal.SIGCONT)
        pid0 = None
    finally:
        if pid0 is not None:
            os.kill(pid0, signal.SIGCONT)
        rc, err = a.close()
    assert rc == 0 and err == "", (rc, err)

    prod = Adapter(live_f, tmp_path, PRODUCTION)                                                 # the PRODUCTION entry on the same state directory: every witness restarts
    try:
        mine(live_f, "pbc")                                                                      # a DIFFERENT proposal for the same sequence (a newer source block)
        again = prod.ask("collect_checkpoint", {"witnessIndex": "1"})
        assert again["ok"] is True, again                                                        # witness 1 has no memory of its first signature, so it signs the conflicting value
        assert again["result"]["checkpoint"]["sequence"] == res["checkpoint"]["sequence"] and again["result"]["checkpoint"] != res["checkpoint"]
        control = prod.ask("collect_checkpoint", {"witnessIndex": "2"})                          # the production control (a durable pin) refuses it
        assert control["ok"] is False and control["error"]["code"] == "STALE_STATE" and control["error"]["reason"] == "CONFLICT_PINNED", control
        assert control["error"]["recorded"]["message"] == res["checkpoint"]
        assert len(evidence(prod.state_dir, 1)["conflicts"]) == 1                                # the pin of witness 1 is now the NEW value, not the one it already signed
    finally:
        rc, err = prod.close()
    assert rc == 0 and err == "", (rc, err)
