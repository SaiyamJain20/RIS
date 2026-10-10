"""Verified never-instantiated worker observation (A1 diagnosis of the SL2 failure, S3-0008).

The production worker creates `<state>/worker/worker.sqlite` lazily on its first worker
operation. A stress that performs none may record `{instantiated: false}` only when the
pinned exporter exits 1 with exactly its "no worker.sqlite" message for that state dir
AND the runner confirms both database paths are absent. Anything else stays a failure.
"""
import importlib
import json

import pytest


def probe():
    module = importlib.import_module('evaluation.e1')
    assert hasattr(module, 'observe_worker_export'), 'worker export observation missing'
    return module.observe_worker_export


def message(state):
    return f'no worker.sqlite in {state} (looked in <dir>/worker/ and in <dir>)\n'.encode()


def test_successful_export_is_an_instantiated_observation(tmp_path):
    raw = json.dumps(dict(events=[], releases=[])).encode()
    assert probe()(0, raw, tmp_path) == dict(instantiated=True, export=raw)


def test_exact_refusal_with_both_paths_absent_is_recorded_explicitly(tmp_path):
    result = probe()(1, message(tmp_path), tmp_path)
    assert result == dict(instantiated=False, exitCode=1, message=message(tmp_path).decode(),
                          checkedAbsent=[str(tmp_path/'worker'/'worker.sqlite'), str(tmp_path/'worker.sqlite')])


@pytest.mark.parametrize('case', ['nested-exists', 'direct-exists', 'other-exit', 'other-message', 'other-dir',
                                  'trailing-text', 'empty-output', 'ambiguous'])
def test_any_other_refusal_or_present_database_stays_a_failure(tmp_path, case):
    code, raw = 1, message(tmp_path)
    if case == 'nested-exists':
        (tmp_path/'worker').mkdir(); (tmp_path/'worker'/'worker.sqlite').write_bytes(b'')
    if case == 'direct-exists': (tmp_path/'worker.sqlite').write_bytes(b'')
    if case == 'other-exit': code = 2
    if case == 'other-message': raw = b'Traceback (most recent call last):\n'
    if case == 'other-dir': raw = message(tmp_path/'other')
    if case == 'trailing-text': raw = message(tmp_path)+b'extra\n'
    if case == 'empty-output': code, raw = 0, b''
    if case == 'ambiguous':
        raw = f'ambiguous state directory: both {tmp_path}/worker/worker.sqlite and {tmp_path}/worker.sqlite exist\n'.encode()
    with pytest.raises(ValueError):
        probe()(code, raw, tmp_path)
