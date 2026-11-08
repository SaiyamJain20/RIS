"""Mutation check of the worker store's D50 rows and the opt-in `worker_log --binding` flag (agent 2, F task 2 slice 5b). Standard library only. Same method as the other runners: one text replacement per
mutant in the file the mutant names (it must match exactly once and change the file), run the UNCHANGED tests/test_witness_pool_driver.py in a temporary copy that keeps the repository layout, count a mutant
DETECTED only when the tests ran and failed; a crash or timeout is NOT detection; the unmutated copy runs first as a control; every anchor is validated before any run. witness_state.py is NOT mutated here
(run_state_mutants.py does that).

Usage (repository root):   python3 -B -I protocol/tools/run_pool_driver_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
FILES = {n: open(os.path.join(PROTO, n)).read() for n in ("hmbc_protocol/witness_pool_driver.py", "testtools/virtual_transport.py")}

# Not listed, equivalent by construction (recorded in the README): D3 (the collection finishes at the timer's own time, so a timer driven one millisecond late changes nothing observable),
# T2 (a delivery and a reply at the same millisecond only differ in the order of two events that do not interact) and T5 (the queue pops in time order, so the max() is defence in depth).
M = [
    ("D1 a cancel action is not performed", ("hmbc_protocol/witness_pool_driver.py", '        elif a["op"] == "cancel":\n            transport.cancel(a["witness"], a["round"])', '        elif a["op"] == "cancel":\n            pass')),
    ("D2 a send action is not performed", ("hmbc_protocol/witness_pool_driver.py", '            transport.send(a["witness"], a["round"], a["message"])', "            pass")),
    ("D4 every reply is reported as a round-1 reply", ("hmbc_protocol/witness_pool_driver.py", "collection.on_reply(t, witness, reply, round_no)", "collection.on_reply(t, witness, reply, 1)")),
    ("D5 the driver returns nothing", ("hmbc_protocol/witness_pool_driver.py", "    return collection.result", "    return None")),
    ("D6 the driver waits for the wrong deadline", ("hmbc_protocol/witness_pool_driver.py", "event = transport.next_event(timer)", "event = transport.next_event(timer + 5000)")),
    ("D7 the collection is not started", ("hmbc_protocol/witness_pool_driver.py", "    _perform(collection.start(), transport)", "    pass")),
    ("T1 a reply at the deadline is returned before the timer", ("testtools/virtual_transport.py", '            if kind == "reply" and when >= deadline_ms:', '            if kind == "reply" and when > deadline_ms:')),
    ("T3 a cancel drops nothing", ("testtools/virtual_transport.py", '        self._q = [e for e in self._q if not (e[3] == "deliver" and e[4][0] == witness and e[4][1] == round_no)]', "        pass")),
    ("T4 a cancel drops the replies as well", ("testtools/virtual_transport.py", 'if not (e[3] == "deliver" and e[4][0] == witness and e[4][1] == round_no)', 'if not (e[4][0] == witness and e[4][1] == round_no)')),
    ("T6 the clock does not reach the deadline", ("testtools/virtual_transport.py", "        self.t = max(self.t, deadline_ms)\n        return None", "        return None")),
    ("T7 the held delay is ignored", ("testtools/virtual_transport.py", 'self.t + self.endpoints[witness].send_delay(round_no), "deliver"', 'self.t, "deliver"')),
    ("T8 the recorded value is not returned with a refusal", ("testtools/virtual_transport.py", '"recorded": e.recorded}', '"recorded": None}')),
    ("T9 a muted witness replies", ("testtools/virtual_transport.py", "        if self.muted:\n            return []", "        if False:\n            return []")),
    ("T10 deliveries are not recorded", ("testtools/virtual_transport.py", "        self.deliveries.append((round_no, dict(message)))\n", "")),
    ("T11 the reply delay is ignored", ("testtools/virtual_transport.py", "return [(self._knob(self.reply_delay, round_no), reply)]", "return [(0, reply)]")),
]


def validate_anchors():
    bad = [(name, FILES[f].count(old)) for name, (f, old, _new) in M if FILES[f].count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(overrides):
    d = tempfile.mkdtemp(prefix="wbind-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("tests", "fixtures"), os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        tt = os.path.join(PROTO, "testtools")
        for name in os.listdir(tt):
            if name.endswith(".py"):
                shutil.copy(os.path.join(tt, name), os.path.join(p, "testtools", name))
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_witness_pool_driver.py"), os.path.join("tests", "test_witness_service.py"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json"),
                    os.path.join("f0", "vectors", "d50_reference.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        for name, text in overrides.items():
            with open(os.path.join(p, name), "w") as f:
                f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_pool_driver.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
    if not validate_anchors():
        return 2
    status, _ = run_in_copy({})
    if status != "pass":
        print("CONTROL FAILED: the unmutated modules do not pass their own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated modules pass all tests")
    detected = 0
    for name, (fname, old, new) in M:
        text = FILES[fname].replace(old, new)
        if text == FILES[fname]:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy({fname: text})
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(M)))
    return 0 if detected == len(M) else 1


if __name__ == "__main__":
    sys.exit(main())
