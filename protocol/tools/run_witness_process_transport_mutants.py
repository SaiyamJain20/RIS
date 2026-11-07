"""Mutation check of the production process transport (agent 2, F task 3, Step 2). Standard library only. Same method as the other runners: one text replacement per mutant in
hmbc_protocol/witness_process_transport.py (it must match exactly once and change the file), run the UNCHANGED tests/test_witness_process_transport.py (with its scripted stub child) in a temporary copy
that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or timeout is NOT detection; the unmutated copy runs first as a control; every anchor is validated
before any run. The live file (test_witness_process_transport_live.py) is not part of this check: it needs two Anvil nodes and is run separately.

Not listed, equivalent in outcome (each argued):
  E1 the `child.dead()` guard in `send`: without it the request is queued and the write fails with EPIPE, which marks the child broken and clears the queue: the same observable result, one syscall later.
  E2 `elapsed >= deadline` against `>`: with the real clock the next millisecond resolves it; a fake clock that does not advance would loop, and no test needs that case.
  E3 the select timeout passed to `_pump` (an exact remainder versus 0): the loop re-reads the clock, so only CPU use differs.
  E4 clearing the partial-line buffer at EOF: a buffered partial line without a newline is never parsed anyway.
  E5 `max(timeout_s, 0.0)`: a non-positive timeout is already treated as 0 by the selector.
  E6 `close_grace_s` ignored by `__exit__`: the tests would only be slower.
  E7 the `os.O_NOFOLLOW` flag on the temporary pid file and on the stderr file: the state directory is private (0700), a symlink there needs the owner.
  E8 closing the stderr file descriptors at close: a leak of four descriptors at the end of the process, not observable by the tests.
  E9 the `stderr_full` flag: once the 4096-byte prefix is full the remaining room is 0 and every later chunk is cut to nothing anyway; the flag only saves a slice.
Branches NO test provokes (listed, not claimed): a failed disk write of the stderr evidence being swallowed (it needs a full disk), and the order 'validate all four command_for answers, then spawn' (a lazy
variant cannot be written as one text replacement; the test shows only that nothing is spawned when the fourth answer is bad).

Usage (repository root):   python3 -B -I protocol/tools/run_witness_process_transport_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
TARGET = "hmbc_protocol/witness_process_transport.py"
SRC = open(os.path.join(PROTO, TARGET)).read()

M = [
    ("P1 the pid file is world-readable", "os.fchmod(fd, 0o600)\n                os.write(fd, f\"{pid}", "os.fchmod(fd, 0o644)\n                os.write(fd, f\"{pid}"),
    ("P2 the pid file has no newline", 'os.write(fd, f"{pid}\\n".encode())', 'os.write(fd, f"{pid}".encode())'),
    ("P3 the pid files are deleted at close", "        self._sel.close()\n", "        self._sel.close()\n        for i in range(len(self.children)):\n            os.unlink(self.pid_path(i))\n"),
    ("P4 the pid file is linked, never replaced (a stale one blocks, the temp file stays)", "os.replace(tmp, final)", "os.link(tmp, final)"),
    ("P5 the pid file is never moved into place", "os.replace(tmp, final)", "pass"),
    ("P6 the pid file lives inside the witness directory", 'return os.path.join(self.state_dir, f"witness-{index}.pid")', 'return os.path.join(self.state_dir, f"witness-{index}", "pid")'),
    ("G1 the child environment is inherited", '    return {"PYTHONPATH": package_dir(), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}', '    return {**os.environ, "PYTHONPATH": package_dir()}'),
    ("A1 -B is dropped from the command", 'argv = [python or sys.executable, "-B", "-m",', 'argv = [python or sys.executable, "-m",'),
    ("A2 the allow-list option is not passed", 'argv += ["--allow-governance", allow_governance]', "argv += []"),
    ("A3 a boolean index is accepted", "if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < WITNESS_COUNT:", "if not isinstance(index, int) or not 0 <= index < WITNESS_COUNT:"),
    ("A4 index 4 is accepted", "not 0 <= index < WITNESS_COUNT", "not 0 <= index <= WITNESS_COUNT"),
    ("A5 a key label is not pattern-checked in the command", "if not isinstance(key_label, str) or _LABEL.fullmatch(key_label) is None:", "if not isinstance(key_label, str):"),
    ("L1 the key labels are used in reverse order", "for i, label in enumerate(key_labels(manifest))]", "for i, label in enumerate(reversed(key_labels(manifest)))]"),
    ("L2 the number of key labels is not checked", "len(labels) != WITNESS_COUNT or not all(", "len(labels) < 1 or not all("),
    ("L3 duplicate key labels are accepted", "or len(set(labels)) != WITNESS_COUNT", "or False"),
    ("L4 the key label pattern is not checked", "all(isinstance(x, str) and _LABEL.fullmatch(x) for x in labels)", "all(isinstance(x, str) for x in labels)"),
    ("C1 fewer than four commands are accepted", "len(commands) != WITNESS_COUNT or not all(", "len(commands) < 1 or not all("),
    ("C2 an empty command is accepted", "isinstance(c, list) and c and all(isinstance(a, str) for a in c)", "isinstance(c, list) and all(isinstance(a, str) for a in c)"),
    ("S1 the state directory mode is not checked", "if st.st_mode & 0o077:", "if False:"),
    ("S2 a state path that is not a directory is accepted", "if not os.path.isdir(self.state_dir):", "if False:"),
    ("S3 a supervisor may start twice", "if self._closed or self._started:", "if self._closed:"),
    ("S4 a transport is handed out before start", "if not self._started or self._closed:", "if self._closed:"),
    ("S5 a transport is handed out after close", "if not self._started or self._closed:", "if not self._started:"),
    ("S6 an unknown collection kind is accepted", "if kind not in KINDS:", "if False:"),
    ("S7 an old transport is not superseded", "            self._current.superseded = True", "            pass"),
    ("S8 a superseded transport still works", "        if self.superseded:", "        if False:"),
    ("T1 a reply at the deadline is returned before the timer", "if self._queue[0][0] < deadline_ms:", "if self._queue[0][0] <= deadline_ms:"),
    ("T2 the time is a float", "t = (now - self._t0) // 1_000_000", "t = (now - self._t0) / 1_000_000"),
    ("T3 every send resets the time origin", "        if self._t0 is None:\n            self._t0 = self._sup._clock()\n        self._ids[ident]", "        self._t0 = self._sup._clock()\n        self._ids[ident]"),
    ("T4 nothing is read at the deadline", "self._sup._pump(0)", "pass"),
    ("V1 a negative deadline is accepted", "deadline_ms < 0:", "deadline_ms < -(10 ** 12):"),
    ("V2 a boolean deadline is accepted", "if isinstance(deadline_ms, bool) or not isinstance(deadline_ms, int) or deadline_ms < 0:", "if not isinstance(deadline_ms, int) or deadline_ms < 0:"),
    ("V3 a boolean witness is accepted", "if isinstance(witness, bool) or not isinstance(witness, int) or not 0 <= witness < WITNESS_COUNT:", "if not isinstance(witness, int) or not 0 <= witness < WITNESS_COUNT:"),
    ("V4 witness 4 is accepted", "not 0 <= witness < WITNESS_COUNT", "not 0 <= witness <= WITNESS_COUNT"),
    ("V5 a boolean round is accepted", "if isinstance(round_no, bool) or not isinstance(round_no, int) or round_no not in (1, 2):", "if not isinstance(round_no, int) or round_no not in (1, 2):"),
    ("V6 round 3 is accepted", "round_no not in (1, 2):", "round_no not in (1, 2, 3):"),
    ("V7 a message that is not an object is accepted", "if not isinstance(message, dict):", "if False:"),
    ("V8 NaN is written", "allow_nan=False", "allow_nan=True"),
    ("V9 an oversized request is written", "if len(line) - 1 > MAX_LINE_BYTES:", "if False:"),
    ("W1 the collection kind is not sent", '"kind": self.kind,', '"kind": "checkpoint",'),
    ("W2 the round is not sent", '"round": round_no, "kind"', '"round": 1, "kind"'),
    ("W3 ids are reused", "self._sup._next_id += 1", "pass"),
    ("W4 the request carries another schema version", '"schemaVersion": SCHEMA, "id": ident', '"schemaVersion": "hmbc-witness-rpc/v0", "id": ident'),
    ("R1 the reply schema version is not checked", 'if obj["schemaVersion"] != SCHEMA:', "if False:"),
    ("R2 an envelope with an extra member is accepted", 'set(obj) != {"schemaVersion", "id", "reply"}', 'not {"schemaVersion", "id", "reply"} <= set(obj)'),
    ("R3 a JSON value that is not an object is not refused as an envelope", "if not isinstance(obj, dict) or set(obj)", "if set(obj)"),
    ("R4 a reply body that is not an object is accepted", 'if not isinstance(obj["reply"], dict):', "if False:"),
    ("R5 a boolean id is accepted", "if isinstance(ident, bool) or not isinstance(ident, int):", "if not isinstance(ident, int):"),
    ("R6 invalid UTF-8 is replaced instead of refused", 'text = raw.decode("utf-8")', 'text = raw.decode("utf-8", "replace")'),
    ("R7 plain json.loads replaces the strict parser", "obj = _e.strict_loads(text)", "obj = json.loads(text)"),
    ("R8 the line buffer is not bounded", "if len(child.buf) > MAX_LINE_BYTES:", "if len(child.buf) > MAX_LINE_BYTES * 64:"),
    ("R9 the rest of an oversized line is parsed", "child.skipping = True", "child.skipping = False"),
    ("R10 a complete oversized line is accepted", "if len(line) > MAX_LINE_BYTES:", "if False:"),
    ("R11 a malformed reply is charged to round 1", "round_no = self._last_round.get(witness)", "round_no = 1"),
    ("R12 a late reply of an earlier collection is delivered as malformed", "if 0 <= ident < self._sup._next_id:\n                    return", "if 0 <= ident < self._sup._next_id:\n                    pass"),
    ("R13 an id that was never issued is dropped", '                detail = "reply id was never issued"', "                return"),
    ("R14 a reply with another witness's id is accepted", "elif info[0] != witness:", "elif False:"),
    ("R15 a duplicate reply is dropped", "                self._queue.append((t, witness, info[1], reply))\n                return",
     "                if any(q[1] == witness and q[3] == reply for q in self._queue):\n                    return\n                self._queue.append((t, witness, info[1], reply))\n                return"),
    ("R16 every reply is reported as a round-1 reply", "self._queue.append((t, witness, info[1], reply))", "self._queue.append((t, witness, 1, reply))"),
    ("R17 a line nobody asked for is delivered", "if round_no is None:\n            return", "if False:\n            return"),
    ("R18 the buffered start of a line is lost", "line = bytes(child.buf) + data[:nl]", "line = data[:nl]"),
    ("X1 cancel drops a started write", "if not (p.ident in drop and p.off == 0)", "if not (p.ident in drop)"),
    ("X2 cancel drops nothing", "child.pending = [p for p in child.pending if not (p.ident in drop and p.off == 0)]", "child.pending = list(child.pending)"),
    ("X3 cancel drops the writes of every round", "if w == witness and r == round_no}", "if w == witness}"),
    ("N1 the pipes are blocking", "            os.set_blocking(fd, False)", "            pass"),
    ("N2 a partial write is never continued", "self._want_write(child, bool(child.pending) and not child.broken)\n\n    # ---- shutdown", "self._want_write(child, False)\n\n    # ---- shutdown"),
    ("N3 a written item stays queued", "            child.pending.pop(0)", "            pass"),
    ("N4 the write offset does not advance", "item.off += n", "item.off += 0"),
    ("D1 a dead reader raises from send", "            except OSError:                                        # a dead reader", "            except KeyError:                                       # a dead reader"),
    ("D2 stderr is not drained", '        self._sel.register(child.stderr_fd, selectors.EVENT_READ, ("err", child))', "        pass"),
    ("D3 all of stderr is kept and written (the file grows past 4096 bytes)", "chunk = data[:STDERR_FILE_BYTES - len(child.stderr_kept)]", "chunk = data"),
    ("D4 more than the first stderr line is reported", 'bytes(child.stderr_kept).split(b"\\n", 1)[0].decode("utf-8", "replace")[:STDERR_KEEP]', 'bytes(child.stderr_kept).decode("utf-8", "replace")[:STDERR_KEEP]'),
    ("D5 stdout is not read", '        self._sel.register(child.stdout_fd, selectors.EVENT_READ, ("out", child))', "        pass"),
    ("D6 a command that cannot be executed raises", "        except OSError as e:\n            child.spawn_error = type(e).__name__\n            return", "        except KeyError as e:\n            child.spawn_error = type(e).__name__\n            return"),
    ("Q1 status does not drain the pipes", "        if self._started and not self._closed:\n            self._pump(0)", "        if False:\n            self._pump(0)"),
    ("Q2 a dead child is reported alive", '"alive": child.proc is not None and rc is None', '"alive": child.proc is not None'),
    ("K1 close does not close stdin", "                child.proc.stdin.close()", "                pass"),
    ("K2 close does not kill a child that ignores EOF", "                child.proc.kill()", "                pass"),
    ("K3 close gives no grace", "deadline = time.monotonic_ns() + int(grace_s * 1e9)", "deadline = time.monotonic_ns()"),
    ("K4 close is not idempotent", "        if self._closed:\n            return\n        self._closed = True", "        self._closed = True"),
    ("Z1 the stderr file is world-readable", "os.fchmod(fd, 0o600)\n        except OSError:\n            raise SupervisorError(\"cannot create the stderr file\")", "os.fchmod(fd, 0o644)\n        except OSError:\n            raise SupervisorError(\"cannot create the stderr file\")"),
    ("Z2 a stale stderr file is appended to, not replaced", "os.open(self.stderr_path(child.index), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)", "os.open(self.stderr_path(child.index), os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)"),
    ("Z3 stderr is never written to its file", "                    os.write(child.stderr_file_fd, chunk)", "                    pass"),
    ("Z4 the stderr file is never created", "        self._open_stderr_file(child)\n\n    def _open_stderr_file", "        pass\n\n    def _open_stderr_file"),
    ("Z5 the stderr file lives inside the witness directory", 'return os.path.join(self.state_dir, f"witness-{index}.stderr")', 'return os.path.join(self.state_dir, f"witness-{index}", "stderr")'),
    ("Z6 command_for is ignored", "replacement = self.command_for(i, list(default))", "replacement = list(default)"),
    ("Z7 command_for gets the live default list, not a copy", "replacement = self.command_for(i, list(default))", "replacement = self.command_for(i, default)"),
    ("Z8 a command_for answer is not validated", "if not (isinstance(replacement, list) and replacement and all(isinstance(a, str) for a in replacement)):", "if False:"),
    ("Z9 a command_for exception escapes unwrapped", "except Exception as e:  # noqa: BLE001 - a buggy hook", "except KeyError as e:  # noqa: BLE001 - a buggy hook"),
    ("Z10 command_for is not checked for being callable", 'if command_for is not None and not callable(command_for):', "if False:"),
    ("Z11 for_deployment drops command_for", "close_grace_s=close_grace_s, command_for=command_for)", "close_grace_s=close_grace_s, command_for=None)"),
    ("K5 a closed supervisor still sends", 'if self._sup._closed:\n            raise TransportError("the supervisor is closed")', "if False:\n            raise TransportError(\"the supervisor is closed\")"),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, old, _new in M if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="wpt-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", os.path.join("tests", "fixtures")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_witness_process_transport.py"), os.path.join("tests", "stub_witness_child.py"),
                    os.path.join("tests", "fixtures", "agent1-85c59f5-f-base-deployment.json")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        if text is not None:
            with open(os.path.join(p, TARGET), "w") as f:
                f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "tests/test_witness_process_transport.py"], cwd=p, capture_output=True, text=True,
                               timeout=300, env=env)
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
    only = set(sys.argv[1:])                                       # optional: run only the mutants whose id (the first word of the name) is listed, e.g. L2 S2 T1
    status, _ = run_in_copy(None)
    if status != "pass":
        print("CONTROL FAILED: the unmutated module does not pass its own tests (%s); nothing reported" % status)
        return 2
    print("control: the unmutated module passes all tests", flush=True)
    detected = 0
    selected = [m for m in M if not only or m[0].split()[0] in only]
    for name, old, new in selected:
        text = SRC.replace(old, new)
        if text == SRC:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n), flush=True)
        else:
            print("NOT-DETECTED(%s) %s" % (status, name), flush=True)
    print("detected %d of %d" % (detected, len(selected)))
    return 0 if detected == len(selected) else 1


if __name__ == "__main__":
    sys.exit(main())
