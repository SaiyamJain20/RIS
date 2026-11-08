"""Mutation check of the pool collection state machine (agent 2, F task 3 slice 3b). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_witness_pool.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. pool_core.py is NOT mutated here (its own runner, run_pool_core_mutants.py, does that).

Usage (repository root):   python3 -B -I protocol/tools/run_pool_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
Exit 0 only when every mutant is detected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
SRC = open(os.path.join(PROTO, "hmbc_protocol", "witness_pool.py")).read()

M = [
    ("W1 four signatures are needed", [("if len(sigs) >= core.POOL_QUORUM:", "if len(sigs) >= core.POOL_QUORUM + 1:")]),
    ("W2 two signatures are enough", [("if len(sigs) >= core.POOL_QUORUM:", "if len(sigs) >= core.POOL_QUORUM - 1:")]),
    ("W3 the signer is not compared with the replying witness's address", [('        if who != self._w[w]:\n            return self._invalid(w, "signature does not recover to the replying witness")', '        if False:\n            return self._invalid(w, "signature does not recover to the replying witness")')]),
    ("W4 a dissent is not recognised", [("        if _canon(m) != _canon(self._asked(round_no)):", "        if False:")]),
    ("W5 repeated replies add signers", [("self._sigs.setdefault(c, {}).setdefault(w, sig)", "self._sigs.setdefault(c, {})[(w, self._replies[w])] = sig")]),
    ("W6 a reply exactly at the reply timeout is still in the snapshot", [("if not self._snap_closed and self._snap_limit <= t_ms:", "if not self._snap_closed and self._snap_limit < t_ms:")]),
    ("W7 a reply exactly at the deadline is collected", [("            if self._deadline <= t_ms:", "            if self._deadline < t_ms:")]),
    ("W8 the second round has no timeout of its own", [("if self._round2 and self._r2_end <= t_ms:", "if False:")]),
    ("W9 the second-round timeout is not capped by the deadline or the close", [("min(close + core.REPLY_TIMEOUT_MS, self._deadline)", "self._deadline")]),
    ("W10 three replies are enough for all-replied", [("len(self._r1_replied) == core.WITNESS_COUNT and t <", "len(self._r1_replied) >= 3 and t <")]),
    ("W11 undelivered round-1 sends are not cancelled", [('                    actions += [{"op": "cancel", "witness": w, "round": 1} for w in range(core.WITNESS_COUNT) if w not in self._r1_replied]\n', "                    actions += []\n")]),
    ("W12 every witness gets a cancel, repliers included", [("for w in range(core.WITNESS_COUNT) if w not in self._r1_replied]", "for w in range(core.WITNESS_COUNT) if True]")]),
    ("W13 the second round skips the witnesses that reported", [('"round": 2, "message": dict(picked)} for w in range(core.WITNESS_COUNT)]', '"round": 2, "message": dict(picked)} for w in range(core.WITNESS_COUNT) if w not in {r["witness"] for r in self._snapshot}]')]),
    ("W14 the second round re-proposes the retained proposal, not the adopted value", [('"round": 2, "message": dict(picked)}', '"round": 2, "message": dict(self._P)}')]),
    ("W15 the effort gate is ignored", [('self._deadline) == "sent":', 'self._deadline) != "none":')]),
    ("W16 the final reference message is always the retained proposal", [("reference = certificate if certificate is not None else (_canon(self._adopted) if self._adopted is not None else _canon(self._P))", "reference = _canon(self._P)")]),
    ("W17 an equivocator or invalid reply is not classified invalid", [("        elif inconsistent or invalid:", "        elif False:")]),
    ("W18 a refusal always carries a reason key", [("            if reason is not None:", "            if True:")]),
    ("W19 a refusal reports the first error, not the latest", [('if k == "refused"][-1]', 'if k == "refused"][0]')]),
    ("W20 the collection does not end early when all four replied and nothing can change", [("        if len(self._r1_replied) == core.WITNESS_COUNT:\n            self._finish(close)\n", "        pass\n")]),
    ("W21 the collection does not end when all four replied in round 2", [("            if len(self._r2_replied) == core.WITNESS_COUNT:\n                self._finish(t)", "            if False:\n                self._finish(t)")]),
    ("W22 the certificate is in arrival order, not address order", [("addrs = sorted(self._w[w] for w in self._sigs[certificate])", "addrs = [self._w[w] for w in self._sigs[certificate]]")]),
    ("W23 a failure submits the signers it has", [('        coll["submittedSigners"] = []\n', '        coll["submittedSigners"] = sorted(self._w[w] for w in self._sigs.get(_canon(self._P), {}))\n')]),
    ("W24 time may go backwards", [("or t_ms < self._t:", "or False:")]),
    ("W25 a boolean witness index is accepted", [("if isinstance(witness, bool) or not isinstance(witness, int) or not 0 <= witness < core.WITNESS_COUNT:", "if not isinstance(witness, int) or not 0 <= witness < core.WITNESS_COUNT:")]),
    ("W26 witness index 4 passes the range check", [("not 0 <= witness < core.WITNESS_COUNT:", "not 0 <= witness <= core.WITNESS_COUNT:")]),
    ("W27 a recorded value is accepted with any code", [('if not (self._adoption and code == "STALE_STATE" and reason == "CONFLICT_PINNED"):', 'if not (self._adoption and reason == "CONFLICT_PINNED"):')]),
    ("W28 a recorded value is accepted outside a checkpoint collection", [('if not (self._adoption and code == "STALE_STATE" and reason == "CONFLICT_PINNED"):', 'if not (code == "STALE_STATE" and reason == "CONFLICT_PINNED"):')]),
    ("W29 the recorded value's sequence is not compared with the proposal's", [('if recorded["message"].get("sequence") != self._P["sequence"]:', "if False:")]),
    ("W30 the recorded signature may come from another witness", [("if who is None or who != self._w[w]:", "if who is None:")]),
    ("W31 late reports are put into the snapshot", [("(self._late if self._snap_closed else self._snapshot).append(report)", "self._snapshot.append(report)")]),
    ("W32 evidence is serialized before the snapshot closes", [("if not self._adoption or not self._snap_closed:", "if not self._adoption:")]),
    ("W33 the failure text confuses the deadline with the validity reserve", [('if ad is not None and ad["reproposal"] == "skipped_deadline":', 'if ad is not None and ad["reproposal"] == "skipped_validity":')]),
    ("W34 the retained proposal aliases the caller's dict", [("dict(proposal), adoption", "proposal, adoption")]),
    ("W35 a proposal with 2 s or less is not refused", [("        if deadline is None:\n            raise CollectionRefused", "        if False:\n            raise CollectionRefused")]),
    ("W36 the quorum string is 2", [('"quorum": str(core.POOL_QUORUM)', '"quorum": "2"')]),
    ("W37 the certificate message is the retained proposal", [('"message": dict(self._msgs[certificate])', '"message": dict(self._P)')]),
    ("W38 a non-dict reply crashes the pool", [('if not isinstance(reply, dict) or not isinstance(reply.get("type"), str):', 'if not isinstance(reply.get("type"), str):')]),
    ("W39 an error reply may carry extra keys", [('not set(reply) <= {"type", "code", "reason", "recorded"} or ', "")]),
    ("W40 a signature reply may carry extra keys", [('if set(reply) != {"type", "message", "signature"} or', 'if not {"type", "message", "signature"} <= set(reply) or')]),
    ("W41 a message with non-string values is accepted", [("all(isinstance(k, str) and isinstance(v, str) for k, v in m.items())", "all(isinstance(k, str) for k, v in m.items())")]),
    ("W42 a non-string refusal reason is accepted", [('(isinstance(reply["reason"], str) and reply["reason"])', "True")]),
    ("W43 an empty refusal code is accepted", [(' or not reply["code"]', "")]),
    ("W44 the snapshot timer ignores the original deadline", [("self._snap_limit = min(core.REPLY_TIMEOUT_MS, deadline)", "self._snap_limit = core.REPLY_TIMEOUT_MS")]),
    ("W45 a float round number is accepted", [("isinstance(round_no, bool) or not isinstance(round_no, int) or round_no not in (1, 2)", "isinstance(round_no, bool) or round_no not in (1, 2)")]),
    ("W46 a round-2 reply is accepted before round 2 started", [("        if round_no == 2 and not self._round2:", "        if False:")]),
    ("W47 start may be called twice", [("        if self._started:\n            raise CollectionError(\"a collection starts once\")", "        if False:\n            raise CollectionError(\"a collection starts once\")")]),
    ("W48 the collection need not be started before replies arrive", [("        if not self._started:\n            raise CollectionError(\"the collection was not started\")\n", "")]),
    ("W49 witnesses need not be distinct", [(" and len(set(witnesses)) == len(witnesses)", "")]),
    ("W50 a witness set of another size is accepted", [("len(witnesses) == core.WITNESS_COUNT and", "len(witnesses) >= 1 and")]),
    ("W51 the witness-set version is not checked", [('if not isinstance(witness_set_version, str) or _DEC.fullmatch(witness_set_version) is None:', "if False:")]),
    ("W52 a decision collection may adopt without a sequence", [('if _DEC.fullmatch(self._P.get("sequence", "")) is None:', "if False:")]),
    ("W53 a list element is not checked to be a string", [("(isinstance(v, list) and all(isinstance(x, str) for x in v))", "isinstance(v, list)")]),
    ("W54 any value is accepted in a proposal or signature reply", [("(isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v)))", "True")]),
    ("W55 a recorded report may carry a list (the adoption core sees it)", [('and _flat_message(recorded["message"])', 'and _plain_message(recorded["message"])')]),
    ("W56 an adopting collection accepts a list-valued proposal", [("        if adoption and not _flat_message(proposal):", "        if False:")]),
    ("W57 a list value is refused in a non-adopting collection", [("        if not _plain_message(proposal):", "        if not _flat_message(proposal):")]),
    ("W58 a signature reply with a list value is refused", [('not _plain_message(reply["message"]) or not isinstance(reply["signature"], str)', 'not _flat_message(reply["message"]) or not isinstance(reply["signature"], str)')]),
]


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="pool-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", os.path.join("tests", "fixtures"), os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py") and name != "witness_pool.py":
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_witness_pool.py"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json"), os.path.join("f0", "SUCCESSOR-WIRE.md"),
                    os.path.join("f0", "vectors", "pool_adoption.py"), os.path.join("f0", "vectors", "check_wire_examples.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "witness_pool.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_pool.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return "timeout", None
        m = re.search(r"(\d+) failed", r.stdout)
        if r.returncode == 0:
            return "pass", 0
        if r.returncode == 1 and m:
            return "fail", int(m.group(1))
        return "crash", None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    status, _ = run_in_copy(SRC)
    if status != "pass":
        print("CONTROL FAILED: the unmutated module does not pass its own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated module passes all tests")
    detected = 0
    for name, edits in M:
        text = SRC
        for old, new in edits:
            if text.count(old) != 1:
                print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
                return 2
            text = text.replace(old, new)
        if text == SRC:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(M)))
    return 0 if detected == len(M) else 1


if __name__ == "__main__":
    sys.exit(main())
