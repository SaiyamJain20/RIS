"""Bounded public RPC calls via the pinned local Cast CLI.

Only literal loopback HTTP endpoints are accepted. Commands/raw output hashes
are retained on failure. Callers must bind receipts/views to the deployment and
classify observed errors; successful RPC output alone is not an experiment.
"""
import ipaddress
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from evaluation.manifests import record_command, sha256, canonical_hash
from evaluation.processes import _pairs, _constant, _float


class RpcClient:
    def __init__(self, url, *, cast, cast_sha256, cwd, output, timeout=5.0, env=None, hash_policy='per-call'):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('RPC budget must be finite and positive')
        # per-call: hash Cast before and after every call (original recipe).
        # checkpoint (A1-0061 D-5b): hash at construction and at every named
        # checkpoint (each read group/submit and run start/end); a mismatch
        # refuses this and every later call. Recorded per row, never implicit.
        if hash_policy not in ('per-call', 'checkpoint'):
            raise ValueError('Unknown Cast hash policy')
        self.hash_policy = hash_policy
        self.checkpoints = []
        self.tampered = False
        parsed = urlsplit(url)
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError as error:
            raise ValueError('RPC host must be a literal loopback address') from error
        if (parsed.scheme != 'http' or not loopback or parsed.port is None
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError('Only literal loopback HTTP RPC endpoints are permitted')
        self.url = url
        self.cast = Path(cast).resolve()
        self.cast_sha256 = cast_sha256
        if sha256(self.cast) != cast_sha256:
            raise ValueError('Cast hash differs from reviewed tool pin')
        self.checkpoints.append(dict(label='construct', sha256=cast_sha256, ok=True))
        self.cwd = Path(cwd).resolve()
        self.output = Path(output)
        self.timeout = timeout
        self.env = None if env is None else dict(env)
        self.commands = []
        self.output.mkdir(parents=True, exist_ok=False)
        self._save()

    def _save(self):
        (self.output/'commands.json').write_text(json.dumps(self.commands, indent=2)+'\n')
        if self.hash_policy == 'checkpoint':
            (self.output/'cast-checkpoints.json').write_text(json.dumps(self.checkpoints, indent=2)+'\n')

    def checkpoint(self, label):
        """Hash Cast at a named boundary; per-call clients already hash every call."""
        if self.hash_policy != 'checkpoint':
            return
        if not isinstance(label, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', label):
            raise ValueError('Malformed Cast checkpoint label')
        actual = sha256(self.cast)
        ok = actual == self.cast_sha256 and not self.tampered
        self.checkpoints.append(dict(label=label, sha256=actual, ok=ok))
        self.tampered = self.tampered or not ok
        self._save()
        if not ok:
            raise ValueError('Cast hash changed at checkpoint '+label)

    def call(self, method, params=None):
        if not isinstance(method, str) or not re.fullmatch(r'[a-z][A-Za-z0-9_]*', method):
            raise ValueError('Malformed RPC method')
        params = [] if params is None else params
        if not isinstance(params, list):
            raise ValueError('RPC parameters must be an array')
        encoded = json.dumps(params, allow_nan=False, separators=(',', ':'))
        if self.tampered:
            raise ValueError('Cast hash changed at an earlier checkpoint; no further RPC execution')
        before = sha256(self.cast) if self.hash_policy == 'per-call' else None
        if self.hash_policy == 'per-call' and before != self.cast_sha256:
            raise ValueError('Cast hash changed before RPC execution')
        log = self.output/f'{len(self.commands):04}.txt'
        argv = [str(self.cast), 'rpc', method, encoded, '--raw', '--rpc-url', self.url,
                '--rpc-timeout', str(math.ceil(self.timeout)), '--no-proxy', '--color', 'never']
        row = record_command(argv, self.cwd, log, timeout=self.timeout, env=self.env)
        row['environmentSha256'] = None if self.env is None else canonical_hash(self.env)
        after = sha256(self.cast) if self.hash_policy == 'per-call' else None
        row.update(castSha256Before=before, castSha256After=after, parseFailure=None)
        if self.hash_policy == 'checkpoint':
            row['hashPolicy'] = 'checkpoint'
        self.commands.append(row)
        self._save()
        if row['exitCode'] != 0:
            raise RuntimeError(f"RPC CLI failed with exit {row['exitCode']}; retained {log}")
        if row['castSha256After'] != before:
            raise ValueError('Cast hash changed during RPC execution')
        try:
            if log.stat().st_size > 4194304:
                raise ValueError('RPC reply exceeds 4 MiB parser budget')
            return json.loads(log.read_text(), object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float)
        except (ValueError, RecursionError) as error:
            row['parseFailure'] = type(error).__name__
            self._save()
            raise ValueError('Malformed public RPC CLI output; retained '+str(log)) from error
