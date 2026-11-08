"""Production process transport for the witness pool (HMBC2020 successor, F task 3, Step 2).

PAPER-DERIVED RECONSTRUCTION. `WitnessSupervisor` starts the four witnesses of the F deployment as four `witness_main` OS processes ONCE (at adapter startup), and `transport_factory(kind)` hands the pool
driver (`witness_pool_driver.run_collection`, and the single-witness path of `adapter_v2_witness`) a fresh per-collection transport with the driver's contract:
  send(witness, round_no, message) -> None        write one request line to that witness
  cancel(witness, round_no) -> None               drop a write that has not been delivered
  next_event(deadline_ms) -> (t_ms, witness, round_no, reply) | None
t_ms is HOST-MONOTONIC whole milliseconds since the first send of the collection, floored; the only clock is `time.monotonic_ns` (injectable for tests, default the real one). A reply read at or after the
deadline is NOT returned (the timer wins at equal milliseconds, as the collection's rule says) and is returned by a later call with a later deadline. Single-threaded: one `selectors` loop, no thread, no
socket, no sleep. The pool is untrusted; what a witness really sent is parsed strictly HERE (an invalid reply becomes `{"type": "malformed", "detail": ...}`, the strict parse the driver doc assigns to the
transport) and judged by the collection.

EXPLICIT CHOICES where the driver, the pool and the published design are silent (reconstruction choices, not findings; each one is a test):
  * READ TIME. A reply's time is the moment this process READ it, not the moment it left the child: a pipe carries no timestamp. The error is bounded by the work the caller does between two calls
    (recovering a signature takes milliseconds); a reply is never stamped earlier than it arrived.
  * NO FAST-FORWARD. With every child dead the transport still waits out the real deadline (up to 10 s): fabricating the passage of time would make the collection's timing evidence fiction.
  * NON-BLOCKING WRITES. A child that does not read (a stopped process) can never block the adapter: the unwritten rest of a request waits in a per-child queue and is flushed when the pipe drains.
  * CANCEL drops a write only if NOT ONE BYTE of it reached the pipe. Cutting a request line in half would corrupt the child's next request, so a started write completes; a delivered write cannot be
    recalled, and its reply, if one comes, is still delivered (the virtual transport behaves the same).
  * IDS. One counter per supervisor, from 0, never reused; a request line is exactly {schemaVersion, id, round, kind, message}. A reply is matched by id AND witness. A duplicate reply to an answered id is
    delivered again (the collection counts it and keeps the first valid signature: dropping it would hide evidence). An id issued earlier but not by this transport (a late reply of an earlier collection)
    is dropped. An id never issued, a non-integer id, or an id issued to ANOTHER witness is a malformed reply, charged to the round of the latest request of the replying witness (no such request: dropped).
  * ENVELOPE. A reply line is valid only if it is strict JSON (duplicate keys and NaN refused, nesting depth survived) in valid UTF-8, at most 1 MiB, exactly {schemaVersion "hmbc-witness-rpc/v1", id, reply}
    with `reply` an object. A longer line is one malformed reply and the rest of that line is discarded unread. A line cut short by the child's death is no reply. The detail text never echoes what the child sent.
  * SUPERVISION. A child that cannot be started, exits (even with status 2 and a JSON error line on stderr) or dies is a SILENT witness: never an exception, never a respawn inside one run (the runner
    restarts the adapter; two dead witnesses must stay dead). A stopped child (SIGSTOP) is alive but silent. stderr is drained so a noisy child cannot block; a 4096-byte prefix is kept as evidence
    (see STDERR FILES) and its first line (at most 512 characters) is reported by `status()`. A child's readiness is not observable (witness_main prints nothing before its first request): a request sent during its startup waits in the pipe and the time counts against the pool window.
  * PID FILES. `<state>/witness-<i>.pid`: decimal pid and a newline, mode 0600, written by temp file and rename, replaced at each start, left in place after the process died and NEVER deleted (a
    runner must treat a pid of a dead witness as stale: pids can be reused). They live NEXT TO the witness directories: nothing is ever created inside `<state>/witness-<i>/`, which belongs to the store.
  * STDERR FILES. `<state>/witness-<i>.stderr` (coordinator decision): the first 4096 bytes a child writes to stderr, mode 0600, created empty at each start (a stale file of an earlier run is replaced),
    appended as the supervisor drains the pipe (every `next_event`, `status` and `close` call drains), outside the store directory, left in place after death and never deleted. The runner needs the
    child's single `{"error": ...}` line to explain WHY a witness is silent. The file never grows past 4096 bytes whatever the child writes; the rest is read and thrown away so the child never blocks. A
    failed disk write of this evidence is swallowed (the evidence is best-effort, the pool is not). The state directory therefore holds the four pid files and the four stderr files and nothing else
    (no file for a command that could not be executed: its `spawnError` is in `status()`).
  * COMMAND SEAM (coordinator decision). `command_for(index, default_command) -> list[str]`, keyword-only, default None = the commands exactly as given (`for_deployment`: the production
    `witness_main` invocation). It is called once per index, in order, BEFORE anything is spawned, with a copy of the default; its return value replaces that index's argv (return the default to leave
    it alone). A return value that is not a non-empty list of strings, or an exception, is a SupervisorError and nothing is spawned. This is the only place a TEST-ONLY variant of one supervised child can
    be substituted; this module contains no fault path of its own.
  * ONE COLLECTION AT A TIME. A new transport supersedes the previous one (the adapter is serial); a superseded transport refuses every call.
  * SHUTDOWN. `close()` closes every child's stdin, waits a bounded grace (real monotonic clock), then kills what is left.
  * KEY CUSTODY is the child's: each witness derives its TEST-ONLY key from its own `--key-label`; this module never sees a key.
No file is read here, nothing is written but the pid files and the stderr files, and no environment variable is read: the child environment is built from three fixed entries.
"""
from __future__ import annotations

import json
import os
import re
import selectors
import subprocess
import sys
import time
from collections import deque

from . import adapter as _e

SCHEMA = "hmbc-witness-rpc/v1"
MAX_LINE_BYTES = 1 << 20
WITNESS_COUNT = 4
KINDS = ("checkpoint", "decision", "receipt", "governance")
STDERR_KEEP = 512                                                # the first stderr line reported by status(), in characters
STDERR_FILE_BYTES = 4096                                         # the stderr prefix kept in memory and written to <state>/witness-<i>.stderr
READ_CHUNK = 1 << 16
_LABEL = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")                  # the key-reference label rule of keys.py


class TransportError(ValueError):
    """A caller bug (bad argument, a call on a superseded or closed transport). Never raised for anything a witness did."""


class SupervisorError(RuntimeError):
    """The supervisor cannot exist or cannot start (bad configuration or state directory). Never raised for a child that fails or dies."""


def package_dir():
    """The directory that holds the `hmbc_protocol` package: the children's working directory and PYTHONPATH."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def child_env():
    """The scrubbed environment of a witness process: exactly three fixed entries, nothing inherited."""
    return {"PYTHONPATH": package_dir(), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def key_labels(manifest):
    """The four witness key labels of a deployment manifest, in witness-set order (`fixture.witnessSet.keyLabels`)."""
    try:
        labels = manifest["fixture"]["witnessSet"]["keyLabels"]
    except (KeyError, TypeError):
        raise SupervisorError("the manifest declares no fixture.witnessSet.keyLabels") from None
    if not isinstance(labels, list) or len(labels) != WITNESS_COUNT or not all(isinstance(x, str) and _LABEL.fullmatch(x) for x in labels) or len(set(labels)) != WITNESS_COUNT:
        raise SupervisorError("fixture.witnessSet.keyLabels must be four distinct key labels")
    return list(labels)


def witness_main_argv(*, deployment, abi_dir, state_dir, index, key_label, allow_governance=None, python=None):
    """The documented invocation of one witness process (witness_main.py): the pinned deployment file, the ABI directory, the witness index and its TEST-ONLY key label, the private state directory."""
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < WITNESS_COUNT:
        raise SupervisorError("index must be 0, 1, 2 or 3")
    if not isinstance(key_label, str) or _LABEL.fullmatch(key_label) is None:
        raise SupervisorError("key_label is not a key label")
    for name, value in (("deployment", deployment), ("abi_dir", abi_dir), ("state_dir", state_dir)):
        if not isinstance(value, str) or not value:
            raise SupervisorError(f"{name} must be a non-empty path")
    argv = [python or sys.executable, "-B", "-m", "hmbc_protocol.witness_main", "--deployment", deployment, "--abi-dir", abi_dir, "--index", str(index), "--key-label", key_label,
            "--state-dir", state_dir]
    if allow_governance is not None:
        if not isinstance(allow_governance, str) or not allow_governance:
            raise SupervisorError("allow_governance must be a non-empty path")
        argv += ["--allow-governance", allow_governance]
    return argv


class _Write:
    """One request line waiting for the pipe. `off` bytes of `data` were already written; off > 0 means it can no longer be cancelled."""
    __slots__ = ("ident", "data", "off")

    def __init__(self, ident, data):
        self.ident, self.data, self.off = ident, data, 0


class _Child:
    def __init__(self, index):
        self.index = index
        self.proc = None
        self.pid = None
        self.spawn_error = None
        self.stdin_fd = self.stdout_fd = self.stderr_fd = None
        self.pending = []
        self.buf = bytearray()
        self.skipping = False
        self.stderr_kept = bytearray()
        self.stderr_full = False
        self.stderr_file_fd = None
        self.write_registered = False
        self.broken = False

    def dead(self):
        return self.proc is None or self.broken or self.proc.poll() is not None


def _parse(raw):
    """(id, reply, None) for a well-formed envelope with an integer id; (id or None, None, detail) otherwise. The detail never contains what the child sent."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, None, "reply is not valid UTF-8"
    try:
        obj = _e.strict_loads(text)
    except _e.AdapterError:
        return None, None, "reply is not strict JSON"
    if not isinstance(obj, dict) or set(obj) != {"schemaVersion", "id", "reply"}:
        return None, None, "reply envelope is not exactly {schemaVersion, id, reply}"
    if obj["schemaVersion"] != SCHEMA:
        return None, None, "reply schemaVersion is not " + SCHEMA
    if not isinstance(obj["reply"], dict):
        return None, None, "reply body is not an object"
    ident = obj["id"]
    if isinstance(ident, bool) or not isinstance(ident, int):
        return None, None, "reply id is not an integer"
    return ident, obj["reply"], None


class WitnessSupervisor:
    def __init__(self, *, state_dir, commands, clock_ns=time.monotonic_ns, cwd=None, env=None, close_grace_s=3.0, command_for=None):
        if not isinstance(state_dir, str) or not state_dir:
            raise SupervisorError("state_dir must be a non-empty path")
        if not isinstance(commands, list) or len(commands) != WITNESS_COUNT or not all(isinstance(c, list) and c and all(isinstance(a, str) for a in c) for c in commands):
            raise SupervisorError("commands must be four non-empty argument lists")
        if not callable(clock_ns):
            raise SupervisorError("clock_ns must be callable")
        if command_for is not None and not callable(command_for):
            raise SupervisorError("command_for must be callable or None")
        self.state_dir = state_dir
        self.commands = [list(c) for c in commands]
        self.cwd = cwd if cwd is not None else package_dir()
        self.env = dict(env) if env is not None else child_env()
        self._clock = clock_ns
        self.close_grace_s = close_grace_s
        self.command_for = command_for
        self.children = []
        self._sel = None
        self._started = False
        self._closed = False
        self._next_id = 0
        self._current = None

    @classmethod
    def for_deployment(cls, *, manifest, deployment_path, abi_dir, state_dir, allow_governance=None, python=None, clock_ns=time.monotonic_ns, close_grace_s=3.0, command_for=None):
        """One `witness_main` command per witness key label of the manifest, all on the same pinned deployment file and private state directory."""
        commands = [witness_main_argv(deployment=deployment_path, abi_dir=abi_dir, state_dir=state_dir, index=i, key_label=label, allow_governance=allow_governance, python=python)
                    for i, label in enumerate(key_labels(manifest))]
        return cls(state_dir=state_dir, commands=commands, clock_ns=clock_ns, close_grace_s=close_grace_s, command_for=command_for)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_exc):
        self.close(grace_s=self.close_grace_s)

    def pid_path(self, index):
        return os.path.join(self.state_dir, f"witness-{index}.pid")

    def stderr_path(self, index):
        return os.path.join(self.state_dir, f"witness-{index}.stderr")

    # ---- start ----------------------------------------------------------------------------------------------------------------------------------------------------
    def start(self):
        if self._closed or self._started:
            raise SupervisorError("a supervisor starts once")
        try:
            st = os.stat(self.state_dir)
        except OSError:
            raise SupervisorError("the state directory does not exist") from None
        if not os.path.isdir(self.state_dir):
            raise SupervisorError("the state path is not a directory")
        if st.st_mode & 0o077:
            raise SupervisorError("the state directory must not be accessible to group or other (chmod 700)")
        commands = self._effective_commands()                          # all four, validated, before anything is spawned
        self._sel = selectors.DefaultSelector()
        self._started = True
        try:
            for i, command in enumerate(commands):
                self._spawn(i, command)
        except BaseException:
            self.close(grace_s=0.5)
            raise

    def _effective_commands(self):
        if self.command_for is None:
            return [list(c) for c in self.commands]
        out = []
        for i, default in enumerate(self.commands):
            try:
                replacement = self.command_for(i, list(default))
            except Exception as e:  # noqa: BLE001 - a buggy hook is a configuration error, reported without its traceback
                raise SupervisorError(f"command_for({i}, ...) raised {type(e).__name__}") from None
            if not (isinstance(replacement, list) and replacement and all(isinstance(a, str) for a in replacement)):
                raise SupervisorError(f"command_for({i}, ...) must return a non-empty list of strings")
            out.append(list(replacement))
        return out

    def _spawn(self, index, command):
        child = _Child(index)
        self.children.append(child)
        try:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, cwd=self.cwd, env=self.env, close_fds=True)
        except OSError as e:
            child.spawn_error = type(e).__name__
            return
        child.proc, child.pid = proc, proc.pid
        child.stdin_fd, child.stdout_fd, child.stderr_fd = proc.stdin.fileno(), proc.stdout.fileno(), proc.stderr.fileno()
        for fd in (child.stdin_fd, child.stdout_fd, child.stderr_fd):
            os.set_blocking(fd, False)
        self._sel.register(child.stdout_fd, selectors.EVENT_READ, ("out", child))
        self._sel.register(child.stderr_fd, selectors.EVENT_READ, ("err", child))
        self._write_pid(index, proc.pid)
        self._open_stderr_file(child)

    def _open_stderr_file(self, child):
        try:
            fd = os.open(self.stderr_path(child.index), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            os.fchmod(fd, 0o600)
        except OSError:
            raise SupervisorError("cannot create the stderr file") from None
        child.stderr_file_fd = fd

    def _write_pid(self, index, pid):
        final = self.pid_path(index)
        tmp = os.path.join(self.state_dir, f".witness-{index}.pid.tmp")
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, f"{pid}\n".encode())
            finally:
                os.close(fd)
            os.replace(tmp, final)
        except OSError:
            raise SupervisorError("cannot write the pid file") from None

    # ---- observation ----------------------------------------------------------------------------------------------------------------------------------------------
    def status(self):
        """One dict per witness: index, pid, alive, returncode, stderrFirstLine (at most 512 characters), spawnError. Drains what the children wrote since the last call."""
        if self._started and not self._closed:
            self._pump(0)
        out = []
        for child in self.children:
            rc = None if child.proc is None else child.proc.poll()
            first = bytes(child.stderr_kept).split(b"\n", 1)[0].decode("utf-8", "replace")[:STDERR_KEEP]
            out.append({"index": child.index, "pid": child.pid, "alive": child.proc is not None and rc is None, "returncode": rc, "stderrFirstLine": first, "spawnError": child.spawn_error})
        return out

    # ---- transports -----------------------------------------------------------------------------------------------------------------------------------------------
    def transport_factory(self, kind):
        if not self._started or self._closed:
            raise SupervisorError("the supervisor is not running")
        if kind not in KINDS:
            raise SupervisorError("kind must be one of " + ", ".join(KINDS))
        if self._current is not None:
            self._current.superseded = True
        self._current = _Transport(self, kind)
        return self._current

    # ---- the single I/O loop --------------------------------------------------------------------------------------------------------------------------------------
    def _pump(self, timeout_s):
        events = self._sel.select(max(timeout_s, 0.0))
        now = self._clock()
        for key, _mask in events:
            what, child = key.data
            if what == "out":
                self._read_out(child, now)
            elif what == "err":
                self._read_err(child)
            else:
                self._flush(child)

    def _read_out(self, child, now):
        if child.stdout_fd is None:
            return
        try:
            data = os.read(child.stdout_fd, READ_CHUNK)
        except BlockingIOError:
            return
        except OSError:
            data = b""
        if not data:
            self._sel.unregister(child.stdout_fd)
            child.stdout_fd = None
            child.buf.clear()                                      # a line cut short by the child's death is no reply
            return
        self._feed(child, data, now)

    def _read_err(self, child):
        if child.stderr_fd is None:
            return
        try:
            data = os.read(child.stderr_fd, READ_CHUNK)
        except BlockingIOError:
            return
        except OSError:
            data = b""
        if not data:
            self._sel.unregister(child.stderr_fd)
            child.stderr_fd = None
            return
        if not child.stderr_full:
            chunk = data[:STDERR_FILE_BYTES - len(child.stderr_kept)]
            child.stderr_kept += chunk
            if child.stderr_file_fd is not None:
                try:
                    os.write(child.stderr_file_fd, chunk)
                except OSError:                                    # best-effort evidence: a full disk must not take the pool down
                    pass
            if len(child.stderr_kept) >= STDERR_FILE_BYTES:
                child.stderr_full = True                           # keep draining, keep and write nothing more

    def _feed(self, child, data, now):
        while data:
            nl = data.find(b"\n")
            if child.skipping:
                if nl < 0:
                    return
                data, child.skipping = data[nl + 1:], False
                continue
            if nl < 0:
                child.buf += data
                if len(child.buf) > MAX_LINE_BYTES:
                    child.buf.clear()
                    child.skipping = True
                    self._route(child, None, None, "reply line exceeds 1 MiB", now)
                return
            line = bytes(child.buf) + data[:nl]
            child.buf.clear()
            data = data[nl + 1:]
            if len(line) > MAX_LINE_BYTES:
                self._route(child, None, None, "reply line exceeds 1 MiB", now)
            else:
                ident, reply, detail = _parse(line)
                self._route(child, ident, reply, detail, now)

    def _route(self, child, ident, reply, detail, now):
        tr = self._current
        if tr is not None and not tr.superseded:
            tr._accept(child.index, ident, reply, detail, now)

    # ---- writes ---------------------------------------------------------------------------------------------------------------------------------------------------
    def _want_write(self, child, want):
        if child.stdin_fd is None:
            return
        if want and not child.write_registered:
            self._sel.register(child.stdin_fd, selectors.EVENT_WRITE, ("in", child))
            child.write_registered = True
        elif not want and child.write_registered:
            self._sel.unregister(child.stdin_fd)
            child.write_registered = False

    def _flush(self, child):
        while child.pending and child.stdin_fd is not None:
            item = child.pending[0]
            try:
                n = os.write(child.stdin_fd, memoryview(item.data)[item.off:])
            except BlockingIOError:
                break
            except OSError:                                        # a dead reader (EPIPE and friends): the witness is silent from here on
                child.broken = True
                child.pending.clear()
                break
            item.off += n
            if item.off < len(item.data):
                break
            child.pending.pop(0)
        self._want_write(child, bool(child.pending) and not child.broken)

    # ---- shutdown -------------------------------------------------------------------------------------------------------------------------------------------------
    def close(self, grace_s=3.0):
        """Close every child's stdin, wait a bounded grace for them to exit, kill what is left. Idempotent. The pid files stay."""
        if self._closed:
            return
        self._closed = True
        if not self._started:
            return
        for child in self.children:
            if child.proc is None:
                continue
            child.pending.clear()
            self._want_write(child, False)
            try:
                child.proc.stdin.close()
            except OSError:
                pass
            child.stdin_fd = None
        deadline = time.monotonic_ns() + int(grace_s * 1e9)
        while any(c.proc is not None and c.proc.poll() is None for c in self.children) and time.monotonic_ns() < deadline:
            self._pump(0.02)                                       # draining keeps a child from blocking on a full pipe while it exits
        for child in self.children:
            if child.proc is not None and child.proc.poll() is None:
                child.proc.kill()
            if child.proc is not None:
                child.proc.wait(timeout=10)
        self._pump(0)
        for child in self.children:
            if child.stderr_file_fd is not None:
                os.close(child.stderr_file_fd)
                child.stderr_file_fd = None
            if child.proc is None:
                continue
            for fd_name, stream in (("stdout_fd", child.proc.stdout), ("stderr_fd", child.proc.stderr)):
                if getattr(child, fd_name) is not None:
                    self._sel.unregister(getattr(child, fd_name))
                    setattr(child, fd_name, None)
                stream.close()
        self._sel.close()


class _Transport:
    def __init__(self, supervisor, kind):
        self._sup = supervisor
        self.kind = kind
        self.superseded = False
        self._t0 = None
        self._ids = {}                                             # id -> (witness, round)
        self._last_round = {}
        self._queue = deque()

    def _check(self):
        if self.superseded:
            raise TransportError("this transport was superseded by a newer collection")
        if self._sup._closed:
            raise TransportError("the supervisor is closed")

    @staticmethod
    def _witness(witness):
        if isinstance(witness, bool) or not isinstance(witness, int) or not 0 <= witness < WITNESS_COUNT:
            raise TransportError("witness must be an integer 0..3")

    @staticmethod
    def _round(round_no):
        if isinstance(round_no, bool) or not isinstance(round_no, int) or round_no not in (1, 2):
            raise TransportError("round must be 1 or 2")

    def send(self, witness, round_no, message):
        self._check()
        self._witness(witness)
        self._round(round_no)
        if not isinstance(message, dict):
            raise TransportError("message must be an object")
        ident = self._sup._next_id
        try:
            line = json.dumps({"schemaVersion": SCHEMA, "id": ident, "round": round_no, "kind": self.kind, "message": message}, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        except (TypeError, ValueError):
            raise TransportError("message is not plain JSON") from None
        if len(line) - 1 > MAX_LINE_BYTES:
            raise TransportError("the request line exceeds 1 MiB")
        self._sup._next_id += 1
        if self._t0 is None:
            self._t0 = self._sup._clock()
        self._ids[ident] = (witness, round_no)
        self._last_round[witness] = round_no
        child = self._sup.children[witness]
        if child.dead():
            return                                                 # a dead witness is silent
        child.pending.append(_Write(ident, line))
        self._sup._flush(child)

    def cancel(self, witness, round_no):
        self._check()
        self._witness(witness)
        self._round(round_no)
        child = self._sup.children[witness]
        drop = {i for i, (w, r) in self._ids.items() if w == witness and r == round_no}
        child.pending = [p for p in child.pending if not (p.ident in drop and p.off == 0)]
        self._sup._want_write(child, bool(child.pending) and not child.broken)

    def next_event(self, deadline_ms):
        self._check()
        if isinstance(deadline_ms, bool) or not isinstance(deadline_ms, int) or deadline_ms < 0:
            raise TransportError("deadline_ms must be a non-negative integer")
        if self._t0 is None:
            self._t0 = self._sup._clock()
        while True:
            if self._queue:
                if self._queue[0][0] < deadline_ms:
                    return self._queue.popleft()
                return None                                        # the head was read at or after the deadline: the timer wins
            elapsed_ns = self._sup._clock() - self._t0
            if elapsed_ns // 1_000_000 >= deadline_ms:
                self._sup._pump(0)                                 # take what is already here, stamped as late as it is; the next call returns it
                return None
            self._sup._pump((deadline_ms * 1_000_000 - elapsed_ns) / 1e9)

    def _accept(self, witness, ident, reply, detail, now):
        if self._t0 is None:
            return
        t = (now - self._t0) // 1_000_000
        if detail is None:
            info = self._ids.get(ident)
            if info is None:
                if 0 <= ident < self._sup._next_id:
                    return                                         # an earlier collection's late reply
                detail = "reply id was never issued"
            elif info[0] != witness:
                detail = "reply id was issued to another witness"
            else:
                self._queue.append((t, witness, info[1], reply))
                return
        round_no = self._last_round.get(witness)
        if round_no is None:
            return
        self._queue.append((t, witness, round_no, {"type": "malformed", "detail": detail}))
