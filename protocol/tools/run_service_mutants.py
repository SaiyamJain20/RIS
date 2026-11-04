"""Mutation check of the witness service, StateCheckpoint path (agent 2, F task 2 slice 4a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_witness_service.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. witness_state.py is NOT mutated here (run_state_mutants.py does that).

Usage (repository root):   python3 -B -I protocol/tools/run_service_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "witness_service.py")).read()

M = [
    ("V1 the psc is not compared with the deployment's", [(' or cp["psc"] != self._psc:', ":")]),
    ("V2 the source chain id is not compared", [('if cp["sourceChainId"] != self._pbc_id or cp["psc"] != self._psc:', 'if cp["psc"] != self._psc:')]),
    ("V3 the next sequence is current plus two", [('1 if current is None else int(current["sequence"]) + 1\n', '1 if current is None else int(current["sequence"]) + 2\n')]),
    ("V4 a gap in the sequence is accepted", [('if int(cp["sequence"]) != expected:', 'if int(cp["sequence"]) < expected:')]),
    ("V5 a block after the observed head is accepted when the read succeeds", [('if block is None or n > int(head["blockNumber"]):', "if block is None:")]),
    ("V6 the block hash is not compared", [('if block["hash"] != cp["sourceBlockHash"]:', "if False:")]),
    ("V7 a block equal to the DBC current block is refused", [('n < int(current["sourceBlockNumber"])', 'n <= int(current["sourceBlockNumber"])')]),
    ("V8 the DBC current block is not a lower bound", [('if current is not None and n < int(current["sourceBlockNumber"]):', "if False:")]),
    ("V9 keyEpoch is not checked", [('if cp["keyEpoch"] != "0":', "if False:")]),
    ("V10 the configured witnessSetVersion is not compared", [('if cp["witnessSetVersion"] != self._wsv or cp["witnessSetVersion"]', 'if cp["witnessSetVersion"]')]),
    ("V11 the witnessSetVersion read at the block is not compared", [(' or cp["witnessSetVersion"] != reads["witnessSetVersion"]:', ":")]),
    ("V12 the epochs at the proposal's block are not compared", [("            if cp[f] != reads[f]:", "            if False:")]),
    ("V13 the epochs at the witness's own head are not compared (no stale-view refusal)", [("            if cp[f] != head_reads[f]:", "            if False:")]),
    ("V14 the epochs are read at the head instead of at the proposal's block", [("        reads = view.reads_at(n)", '        reads = view.reads_at(int(head["blockNumber"]))')]),
    ("V15 the freshness read repeats the block read", [('head_reads = view.reads_at(int(head["blockNumber"]))', "head_reads = reads")]),
    ("V16 an expiry equal to the observation is accepted", [("        if e <= ts:", "        if e < ts:")]),
    ("V17 an expiry exactly at the window edge is refused", [("        if e > ts + self._max_ttl:", "        if e >= ts + self._max_ttl:")]),
    ("V18 the window has no upper bound", [("        if e > ts + self._max_ttl:", "        if False:")]),
    ("V19 the window observes the PBC instead of the DBC", [('ts = int(view.observe("dbc")["timestamp"])', 'ts = int(view.observe("pbc")["timestamp"])')]),
    ("V20 the store is told no expiry", [("expires_at=cp[\"expiresAt\"],", "expires_at=None,")]),
    ("V21 the store observes the PBC", [('observe=lambda: self._view.observe("dbc"),', 'observe=lambda: self._view.observe("pbc"),')]),
    ("V22 the store gets another domain", [('domain=self._domain,', 'domain="0x" + "00" * 32,')]),
    ("V23 an unreadable ledger escapes as a raw exception", [("        except LedgerUnreachable as e:\n            raise WitnessRefusal(\"ADAPTER_UNAVAILABLE\", \"LEDGER_UNREACHABLE\", f\"the ledger could not be read: {e}\") from None\n", "")]),
    ("V24 the recorded value is dropped from a pinned refusal", [("raise WitnessRefusal(e.code, e.reason, e.message, e.recorded) from None", "raise WitnessRefusal(e.code, e.reason, e.message, None) from None")]),
    ("V25 the proposal's shape is not validated", [("return dict(wire.state_checkpoint(proposal))", "return dict(proposal)")]),
    ("V26 the proposer's sequence is current plus two", [('str(int(cur["sequence"]) + 1)', 'str(int(cur["sequence"]) + 2)')]),
    ("V27 the proposer's expiry is twice the ttl", [('str(int(dbc["timestamp"]) + ttl)', 'str(int(dbc["timestamp"]) + 2 * ttl)')]),
    ("V28 the overtaken evidence claims a far sequence", [('"0" if current is None else str(current["sequence"])', '"99"')]),
    ("V29 the maximum window default is 61 s", [("DEFAULT_MAX_TTL = 60", "DEFAULT_MAX_TTL = 61")]),
    ("V30 the proposer's default ttl is 31 s", [("DEFAULT_PROPOSER_TTL = 30", "DEFAULT_PROPOSER_TTL = 31")]),
    ("V31 the effect carries the sequence key instead of the source block hash", [('EFFECT = ("authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash")', 'EFFECT = ("authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockNumber")')]),
    ("V32 the conflict key is the block number instead of the sequence", [('key=cp["sequence"],', 'key=cp["sourceBlockNumber"],')]),
    ("V33 the proposer reads the epochs at block 0", [('reads = view.reads_at(int(head["blockNumber"]))\n    dbc = view.observe("dbc")', 'reads = view.reads_at(0)\n    dbc = view.observe("dbc")')]),
    ("V34 a non-positive max ttl is accepted", [("or max_checkpoint_ttl < 1:", "or False:")]),
]


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="service-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", os.path.join("tests", "fixtures"), os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py") and name != "witness_service.py":
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_witness_service.py"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json"), os.path.join("f0", "vectors", "d50_reference.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "witness_service.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_service.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
