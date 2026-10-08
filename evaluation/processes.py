"""Owned, bounded JSON-lines subprocess transport for the C-E1 runner.

This transport does not establish provider correctness. The runner must validate
the frozen operation response and compare native evidence independently. It logs
payload digests rather than request/response contents; worker tokens and keys do
not belong in a process transcript. Only handles created here are terminated.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import time

from evaluation.manifests import now, sha256

MAX_LINE_BYTES = 1048576


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate response key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('Non-finite response value: ' + value)


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Non-finite parsed response number')
    return result


class JsonLinesProcess:
    """Single-request-at-a-time transport; failures close a desynchronized pipe."""

    def __init__(self, argv, *, cwd, output, timeout=10.0, stop_grace=2.0, env=None):
        if not all(math.isfinite(value) and value > 0 for value in (timeout, stop_grace)):
            raise ValueError('Process time budgets must be finite and positive')
        self.argv = list(argv)
        self.cwd = Path(cwd).resolve()
        self.output = Path(output)
        self.timeout = timeout
        self.stop_grace = stop_grace
        self.env = None if env is None else dict(env)
        self._process = None
        self._stderr = None
        self._started = False
        self._record = None

    @property
    def pid(self):
        return self._process.pid if self._process is not None else None

    @property
    def returncode(self):
        return self._process.poll() if self._process is not None else None

    def _save(self):
        if self._record is not None:
            (self.output/'process.json').write_text(json.dumps(self._record, indent=2)+'\n')

    def start(self):
        if self._started:
            raise RuntimeError('Owned process cannot be restarted')
        self.output.mkdir(parents=True, exist_ok=False)
        self._started = True
        self._record = {'argv': self.argv, 'cwd': str(self.cwd), 'pid': None,
                        'startedAt': now(), 'endedAt': None, 'exitCode': None,
                        'timeoutSeconds': self.timeout, 'stopGraceSeconds': self.stop_grace,
                        'failure': None, 'exchanges': [], 'environmentSha256': None if self.env is None else
                        hashlib.sha256(json.dumps(self.env, sort_keys=True).encode()).hexdigest()}
        try:
            self._stderr = (self.output/'stderr.log').open('xb')
            self._process = subprocess.Popen(self.argv, cwd=self.cwd, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=self._stderr,
                                            bufsize=0, start_new_session=True, env=self.env)
            self._record['pid'] = self.pid
            os.set_blocking(self._process.stdin.fileno(), False)
            os.set_blocking(self._process.stdout.fileno(), False)
            self._save()
        except OSError as error:
            self._record['failure'] = type(error).__name__
            self.stop()
            raise
        return self

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, traceback):
        self.stop()

    def stop(self):
        if self._record is None or self._record['endedAt'] is not None:
            return
        process = self._process
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            try:
                process.wait(timeout=self.stop_grace)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=self.stop_grace)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=self.stop_grace)
            process.stdout.close()
            self._record['exitCode'] = process.returncode
        else:
            self._record['exitCode'] = 127
        if self._stderr is not None:
            self._stderr.close()
        self._record['endedAt'] = now()
        self._record['stderrSha256'] = sha256(self.output/'stderr.log')
        self._save()

    def exchange(self, request):
        if self._process is None or self._record['endedAt'] is not None:
            raise RuntimeError('Owned process is not running')
        # Reject malformed caller data before writing, keeping the stream usable.
        payload = json.dumps(request, allow_nan=False, separators=(',', ':')).encode()
        if len(payload)+1 > MAX_LINE_BYTES:
            raise ValueError('Request line exceeds 1 MiB')
        wire = payload+b'\n'
        row = {'startedAt': now(), 'requestSha256': hashlib.sha256(payload).hexdigest(),
               'responseSha256': None, 'endedAt': None, 'failure': None}
        self._record['exchanges'].append(row)
        try:
            response = self._roundtrip(wire)
            try:
                result = json.loads(response.decode('utf-8'), object_pairs_hook=_pairs,
                                    parse_constant=_constant, parse_float=_float)
            except RecursionError as error:
                raise ValueError('Response JSON exceeds the parser nesting limit') from error
            if not isinstance(result, dict):
                raise ValueError('Response must be an object')
            row['responseSha256'] = hashlib.sha256(response).hexdigest()
            row['endedAt'] = now()
            self._save()
            return result
        except (OSError, ValueError, TimeoutError, ChildProcessError) as error:
            row['endedAt'] = now()
            row['failure'] = type(error).__name__
            self._record['failure'] = type(error).__name__
            self.stop()
            raise

    def _roundtrip(self, wire):
        process = self._process
        deadline = time.monotonic()+self.timeout
        written = 0
        received = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, 'out')
            # An unsolicited queued frame must not become this request's answer.
            if selector.select(0):
                raise ValueError('Unsolicited adapter stdout')
            selector.register(process.stdin, selectors.EVENT_WRITE, 'in')
            while True:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('JSON-lines process exchange timed out')
                events = selector.select(remaining)
                if not events:
                    raise TimeoutError('JSON-lines process exchange timed out')
                for key, _ in events:
                    if key.data == 'in':
                        try:
                            count = os.write(key.fd, wire[written:written+65536])
                        except BlockingIOError:
                            continue
                        written += count
                        if written == len(wire):
                            selector.unregister(process.stdin)
                    else:
                        try:
                            chunk = os.read(key.fd, 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            raise ChildProcessError('Process exited without a complete response frame')
                        received.extend(chunk)
                        newline = received.find(b'\n')
                        if newline >= 0:
                            if newline+1 > MAX_LINE_BYTES:
                                raise ValueError('Response line exceeds 1 MiB')
                            if newline != len(received)-1 or written != len(wire):
                                raise ValueError('Extra or premature adapter response')
                            return bytes(received[:newline])
                        if len(received) >= MAX_LINE_BYTES:
                            raise ValueError('Response line exceeds 1 MiB')


class ServiceProcess:
    """Direct owned service with file logs and bounded readiness retries.

    Readiness probes must bound their own I/O. This class never adopts an
    existing PID or terminates a process by port. Commands must launch the
    service directly; descendant supervision is not provided.
    """

    def __init__(self, argv, *, cwd, output, stop_grace=2.0, env=None):
        if not math.isfinite(stop_grace) or stop_grace <= 0:
            raise ValueError('Process grace must be finite and positive')
        self.argv = list(argv)
        self.cwd = Path(cwd).resolve()
        self.output = Path(output)
        self.stop_grace = stop_grace
        self.env = None if env is None else dict(env)
        self._process = None
        self._record = None
        self._logs = []
        self._started = False

    @property
    def pid(self):
        return self._process.pid if self._process is not None else None

    @property
    def returncode(self):
        return self._process.poll() if self._process is not None else None

    def _save(self):
        (self.output/'process.json').write_text(json.dumps(self._record, indent=2)+'\n')

    def start(self):
        if self._started:
            raise RuntimeError('Owned process cannot be restarted')
        self.output.mkdir(parents=True, exist_ok=False)
        self._started = True
        self._record = {'argv': self.argv, 'cwd': str(self.cwd), 'pid': None,
                        'startedAt': now(), 'readyAt': None, 'endedAt': None,
                        'exitCode': None, 'stopGraceSeconds': self.stop_grace, 'failure': None,
                        'environmentSha256': None if self.env is None else hashlib.sha256(json.dumps(self.env, sort_keys=True).encode()).hexdigest()}
        try:
            for name in ('stdout.log', 'stderr.log'):
                self._logs.append((self.output/name).open('xb'))
            self._process = subprocess.Popen(self.argv, cwd=self.cwd, stdin=subprocess.DEVNULL,
                                            stdout=self._logs[0], stderr=self._logs[1],
                                            start_new_session=True, env=self.env)
            self._record['pid'] = self.pid
            self._save()
        except OSError as error:
            self._record['failure'] = type(error).__name__
            self.stop()
            raise
        return self

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, traceback):
        self.stop()

    def wait_ready(self, probe, *, timeout):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Readiness budget must be finite and positive')
        if self._process is None or self._record['endedAt'] is not None:
            raise RuntimeError('Owned service is not running')
        deadline = time.monotonic()+timeout
        try:
            while True:
                if self.returncode is not None:
                    raise ChildProcessError('Owned service exited before readiness')
                if time.monotonic() >= deadline:
                    raise TimeoutError('Owned service readiness timed out')
                ready = probe()
                if self.returncode is not None:
                    raise ChildProcessError('Owned service exited during readiness probe')
                if time.monotonic() >= deadline:
                    raise TimeoutError('Owned service readiness probe exceeded deadline')
                if ready is True:
                    self._record['readyAt'] = now()
                    self._save()
                    return
                time.sleep(min(0.02, max(0, deadline-time.monotonic())))
        except Exception as error:
            # Preserve an unexpected probe failure and terminate the owned child;
            # callers see the original exception, not a false "not ready" result.
            self._record['failure'] = type(error).__name__
            self.stop()
            raise

    def stop(self):
        if self._record is None or self._record['endedAt'] is not None:
            return
        process = self._process
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=self.stop_grace)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=self.stop_grace)
            self._record['exitCode'] = process.returncode
        else:
            self._record['exitCode'] = 127
        for stream in self._logs:
            stream.close()
        for name in ('stdout', 'stderr'):
            path = self.output/(name+'.log')
            self._record[name+'Sha256'] = sha256(path) if path.is_file() else None
        self._record['endedAt'] = now()
        self._save()
