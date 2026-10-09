"""Cast hash checkpoints (A1-0061 D-5b): fewer hashes, never an unchecked group.

Synthetic Cast-shaped scripts and controlled replies only; no chain is started.
The default per-call policy stays unchanged for strict plans.
"""
import importlib
import json
import sys

import pytest

from evaluation.manifests import sha256


def client(tmp_path, policy, program='import json,sys;print(json.dumps(sys.argv[1:]))'):
    executable = tmp_path/'cast-probe'; executable.write_text('#!'+sys.executable+'\n'+program+'\n'); executable.chmod(0o700)
    module = importlib.import_module('evaluation.rpc')
    return module.RpcClient('http://127.0.0.1:18545', cast=executable, cast_sha256=sha256(executable), cwd=tmp_path,
                            output=tmp_path/'rpc', timeout=2.0, hash_policy=policy)


def count_hashes(monkeypatch):
    rpc = importlib.import_module('evaluation.rpc'); counter = dict(n=0); real = rpc.sha256
    def counted(path):
        counter['n'] += 1; return real(path)
    monkeypatch.setattr(rpc, 'sha256', counted)
    return counter


def test_per_call_policy_is_default_and_unchanged(tmp_path, monkeypatch):
    c = client(tmp_path, 'per-call'); counter = count_hashes(monkeypatch)
    c.call('eth_chainId'); c.call('eth_chainId')
    assert counter['n'] == 4
    rows = json.loads((tmp_path/'rpc/commands.json').read_text())
    assert all(r['castSha256Before'] == r['castSha256After'] == c.cast_sha256 for r in rows)
    default = importlib.import_module('evaluation.rpc').RpcClient.__init__.__kwdefaults__['hash_policy']
    assert default == 'per-call'


def test_checkpoint_policy_hashes_only_at_named_checkpoints(tmp_path, monkeypatch):
    c = client(tmp_path, 'checkpoint'); counter = count_hashes(monkeypatch)
    c.checkpoint('group-start'); c.call('eth_chainId'); c.call('eth_chainId'); c.checkpoint('group-end')
    assert counter['n'] == 2
    rows = json.loads((tmp_path/'rpc/commands.json').read_text())
    assert [r['hashPolicy'] for r in rows] == ['checkpoint', 'checkpoint']
    assert all(r['castSha256Before'] is None and r['castSha256After'] is None for r in rows)
    checks = json.loads((tmp_path/'rpc/cast-checkpoints.json').read_text())
    assert [x['label'] for x in checks] == ['construct', 'group-start', 'group-end']
    assert all(x['sha256'] == c.cast_sha256 and x['ok'] is True for x in checks)


def test_checkpoint_detects_changed_cast_and_refuses_further_calls(tmp_path):
    c = client(tmp_path, 'checkpoint'); c.cast.write_text('#!'+sys.executable+'\nraise SystemExit(7)\n')
    with pytest.raises(ValueError, match='hash'):
        c.checkpoint('group-start')
    with pytest.raises(ValueError, match='hash'):
        c.call('eth_chainId')
    assert json.loads((tmp_path/'rpc/commands.json').read_text()) == []


def test_unknown_policy_refused(tmp_path):
    with pytest.raises(ValueError):
        client(tmp_path, 'never')


class Recording:
    def __init__(self):
        self.labels = []
    def checkpoint(self, label):
        self.labels.append(label)


def test_public_chain_checkpoints_each_read_group_and_submit(tmp_path):
    from evaluation.tests.test_chain import Replies, executor
    replies = Replies(); recording = Recording(); replies.checkpoint = recording.checkpoint
    chain = executor(tmp_path, replies)
    with chain.read_group(('TMSC',)) as group:
        group.read('TMSC', 'authEpoch')
    chain.submit('relay', 'TMSC', 'authEpoch')
    assert recording.labels == ['read-group', 'submit']
