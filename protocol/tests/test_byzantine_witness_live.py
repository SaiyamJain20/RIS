"""The real-PROCESS Byzantine witness against the real pool and a real ledger (agent 2, F phase; gap G1; rows FL-4, FL-5/F-22, FL-7, F-12). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys; one host; one trial
each; the adversary is deliberate, not an observed behaviour.

The adapter is started through the TEST-ONLY alternate entry (`--witness-variant 3=byz:SPEC`) as a real long-running process on a real Anvil pair with agent 1's F ledger (85c59f5); witness 3 is
`testtools.byzantine_witness`, the other three are the production witnesses. Where the pool would otherwise return as soon as three honest signatures arrive (so the Byzantine reply might never be heard),
one HONEST witness is SIGSTOPped so the outcome does not depend on reply order:
  FL-4  `repeat:3` with witness 0 stopped: the certificate needs witness 3, which answers three times; it counts ONCE (three distinct signers, each once).
  F-12  `equivocate` with witness 0 stopped: witness 3 signs the asked value and then a second value; the second value never joins the certificate and the store of witness 3 holds one pin.
  FL-5  `impersonate:0` with witness 2 stopped: witness 3's valid signature recovers to witness 0, not to the sender, so it is `invalid`, only two valid signers remain and the pool classifies QUORUM_UNAVAILABLE.
  FL-7  `poison:authEpoch` with witness 2 stopped: witness 3 signs a different checkpoint, which is `dissent`; the same classified QUORUM_UNAVAILABLE.
The live fixture is the one of test_rpc_binding_view_live.py (a module-scoped Anvil pair, honouring HMBC_FOUNDRY_DIR). The two no-quorum cases wait for the pool's 10 s cap. Not claimed: that any oracle accepts
these runs; anything about consensus or timing."""
import os
import signal

from hmbc_protocol import eip712, messages
from test_faulty_adapter_v2_live import FAULTY, Adapter, evidence, fresh_blocks, statuses  # noqa: F401
from test_mutant_tree_live import wait_pid
from test_rpc_binding_view_live import f_ledger, live_f, mine  # noqa: F401  (live_f and f_ledger are fixtures)


def witnesses(live):
    return list(live.dep["fixture"]["witnessSet"]["witnesses"])


def signers(live, result):
    cp = result["checkpoint"]
    digest = messages.digest_of("StateCheckpoint", cp, messages.domain_for("StateCheckpoint", cp, live.dep))
    return [eip712.recover(digest, sig) for sig in result["signatures"]]


def stopped_adapter(live_f, tmp_path, variant, stop):
    """An adapter whose witness 3 is the Byzantine variant and whose honest witness `stop` is SIGSTOPped; returns (adapter, pid of the stopped witness)."""
    fresh_blocks(live_f)
    a = Adapter(live_f, tmp_path, FAULTY, ["--witness-variant", "3=byz:" + variant])
    pid = wait_pid(a, stop)
    os.kill(pid, signal.SIGSTOP)
    return a, pid


def release(a, pid):
    try:
        os.kill(pid, signal.SIGCONT)
    finally:
        return a.close()


def test_fl4_a_witness_that_repeats_its_reply_counts_once_in_the_certificate(live_f, tmp_path):
    a, pid = stopped_adapter(live_f, tmp_path, "repeat:3", 0)
    try:
        r = a.ask("collect_checkpoint", {})
        assert r["ok"] is True, r
        res = r["result"]
        got = signers(live_f, res)
        assert len(res["signatures"]) == 3 and len(set(got)) == 3 and set(got) == set(witnesses(live_f)[1:])            # witnesses 1, 2 and 3, each exactly once
        assert statuses(res) == ["silent", "signed", "signed", "signed"], statuses(res)
        assert len(evidence(a.state_dir, 3)["conflicts"]) == 1                                                        # the real service behind the repeater recorded ONE pin
    finally:
        rc, err = release(a, pid)
    assert rc == 0 and err == "", (rc, err)


def test_f12_an_equivocating_witness_signs_two_values_but_only_the_asked_one_joins_the_certificate(live_f, tmp_path):
    a, pid = stopped_adapter(live_f, tmp_path, "equivocate", 0)
    try:
        r = a.ask("collect_checkpoint", {})
        assert r["ok"] is True, r
        res = r["result"]
        got = signers(live_f, res)
        assert len(res["signatures"]) == 3 and len(set(got)) == 3 and set(got) == set(witnesses(live_f)[1:])
        assert statuses(res)[3] == "signed"
        assert len(evidence(a.state_dir, 3)["conflicts"]) == 1                                                        # one pin: the second signed value never touched the store
    finally:
        rc, err = release(a, pid)
    assert rc == 0 and err == "", (rc, err)


def no_quorum(a):
    r = a.ask("collect_checkpoint", {}, timeout=90)
    assert r["ok"] is False, r
    err = r["error"]
    assert err["code"] == "ADAPTER_UNAVAILABLE" and err.get("reason") == "QUORUM_UNAVAILABLE", err                    # classified, never a denial
    coll = err["collection"]
    assert [o["witnessIndex"] for o in coll["outcomes"]] == ["0", "1", "2", "3"] and coll["submittedSigners"] == []
    return [o["status"] for o in coll["outcomes"]]


def test_fl5_a_signature_that_recovers_to_another_witness_is_invalid_and_leaves_two_valid_signers(live_f, tmp_path):
    a, pid = stopped_adapter(live_f, tmp_path, "impersonate:0", 2)
    try:
        assert no_quorum(a) == ["signed", "signed", "silent", "invalid"]
    finally:
        rc, err = release(a, pid)
    assert rc == 0 and err == "", (rc, err)


def test_fl7_a_witness_that_signs_a_different_checkpoint_is_a_dissent_and_never_counted(live_f, tmp_path):
    a, pid = stopped_adapter(live_f, tmp_path, "poison:authEpoch", 2)
    try:
        assert no_quorum(a) == ["signed", "signed", "silent", "dissent"]
    finally:
        rc, err = release(a, pid)
    assert rc == 0 and err == "", (rc, err)
