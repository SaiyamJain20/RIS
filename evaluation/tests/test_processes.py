"""Real synthetic child-process probes; no ledger/provider integration evidence.

These tests catch missing cleanup, unbounded pipe waits and accepting a corrupt
or desynchronized JSON-lines stream. Literal probe outputs specify the expected
transport behavior independently of the implementation.
"""
import importlib
import json
import subprocess
import sys
import time

import pytest


def transport(tmp_path, program):
    # Keep RED as an assertion about the absent owned transport, not an import
    # collection error. The temporary utility is an actual external process.
    try:
        module = importlib.import_module('evaluation.processes')
    except ModuleNotFoundError:
        pytest.fail('C-E1 owned process transport is not implemented')
    return module.JsonLinesProcess(
        [sys.executable, '-u', '-c', program], cwd=tmp_path,
        output=tmp_path/'process', timeout=0.3, stop_grace=0.3,
    )


ECHO = "import sys,json\nfor line in sys.stdin:\n print(json.dumps({'seen':json.loads(line)['id']}),flush=True)\n"


def test_frozen_environment_overrides_parent_without_exposing_values(tmp_path, monkeypatch):
    monkeypatch.setenv('HMBC_TEST_FROZEN_ENV', 'ambient')
    module = importlib.import_module('evaluation.processes')
    program = "import os,sys,json\nfor _ in sys.stdin:\n print(json.dumps({'value':os.environ['HMBC_TEST_FROZEN_ENV']}),flush=True)"
    with module.JsonLinesProcess([sys.executable, '-u', '-c', program], cwd=tmp_path, output=tmp_path/'env-process',
                                 env={'HMBC_TEST_FROZEN_ENV':'pinned'}) as child:
        assert child.exchange({}) == {'value':'pinned'}
    assert 'pinned' not in (tmp_path/'env-process'/'process.json').read_text()


def test_two_calls_return_their_own_frame_and_stop_records_exit(tmp_path):
    child = transport(tmp_path, ECHO)
    with child:
        assert child.exchange({'id': 'first'}) == {'seen': 'first'}
        assert child.exchange({'id': 'second'}) == {'seen': 'second'}
        assert child.pid > 0
    record = json.loads((tmp_path/'process'/'process.json').read_text())
    assert record['pid'] == child.pid
    assert record['endedAt'] and record['exitCode'] is not None
    assert record['cwd'] == str(tmp_path)
    assert len(record['exchanges']) == 2
    assert record['exchanges'][0]['responseSha256'] != record['exchanges'][1]['responseSha256']
    assert 'first' not in json.dumps(record['exchanges'])
    child.stop()  # Cleanup is safe to repeat, using only the owned handle.


def test_stderr_flood_does_not_block_response_and_is_retained(tmp_path):
    child = transport(tmp_path, "import sys\nsys.stderr.write('z'*200000);sys.stderr.flush()\n" + ECHO)
    with child:
        assert child.exchange({'id': 'ready'}) == {'seen': 'ready'}
    assert (tmp_path/'process'/'stderr.log').read_text() == 'z'*200000


def test_response_timeout_stops_owned_child_and_preserves_unrelated_process(tmp_path):
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
    try:
        child = transport(tmp_path, 'import time;time.sleep(30)')
        with child:
            with pytest.raises(TimeoutError):
                child.exchange({'id': 'never'})
            assert child.returncode is not None
        assert unrelated.poll() is None
        record = json.loads((tmp_path/'process'/'process.json').read_text())
        assert record['failure'] == 'TimeoutError'
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=2)


def test_stdin_backpressure_obeys_timeout(tmp_path):
    child = transport(tmp_path, 'import time;time.sleep(30)')
    with child:
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            child.exchange({'blob': 'a'*300000})
        assert time.monotonic()-started < 3
        assert child.returncode is not None


@pytest.mark.parametrize('reply', [
    '{"ok":true,"ok":false}\n',
    '{"value":NaN}\n',
    '{"value":1e999}\n',
    'not-json\n',
    '{}\n{}\n',
    pytest.param('{"nested":' + '['*10000 + '0' + ']'*10000 + '}\n', id='parser-recursion'),
])
def test_corrupt_or_extra_response_poison_stream_and_stop_child(tmp_path, reply):
    program = f'import sys,time\nsys.stdin.readline()\nsys.stdout.write({reply!r});sys.stdout.flush()\ntime.sleep(30)'
    child = transport(tmp_path, program)
    with child:
        with pytest.raises(ValueError):
            child.exchange({'id': 'bad'})
        assert child.returncode is not None
        with pytest.raises(RuntimeError):
            child.exchange({'id': 'later'})


def test_eof_without_frame_is_failure_with_actual_exit_code(tmp_path):
    child = transport(tmp_path, 'import sys\nsys.stdin.readline()\nsys.exit(7)')
    with child:
        with pytest.raises(ChildProcessError):
            child.exchange({'id': 'failed'})
    assert child.returncode == 7
    assert json.loads((tmp_path/'process'/'process.json').read_text())['exitCode'] == 7


def test_oversize_response_is_rejected_before_unbounded_read(tmp_path):
    child = transport(tmp_path, "import sys,time\nsys.stdin.readline()\nsys.stdout.write('a'*1100000);sys.stdout.flush()\ntime.sleep(30)")
    with child:
        with pytest.raises(ValueError, match='line exceeds'):
            child.exchange({'id': 'large'})
        assert child.returncode is not None


def test_bad_request_is_rejected_without_poisoning_valid_stream(tmp_path):
    child = transport(tmp_path, ECHO)
    with child:
        with pytest.raises(ValueError):
            child.exchange({'value': float('nan')})
        with pytest.raises(ValueError, match='line exceeds'):
            child.exchange({'blob': 'a'*1100000})
        assert child.exchange({'id': 'valid'}) == {'seen': 'valid'}


def test_existing_output_is_preserved_and_child_is_not_started(tmp_path):
    child = transport(tmp_path, ECHO)
    (tmp_path/'process').mkdir()
    (tmp_path/'process'/'keep').write_text('keep')
    with pytest.raises(FileExistsError):
        child.start()
    assert child.pid is None
    assert (tmp_path/'process'/'keep').read_text() == 'keep'


def test_missing_executable_keeps_startup_failure_evidence(tmp_path):
    child = transport(tmp_path, ECHO)
    child.argv = [str(tmp_path/'nonexistent')]
    with pytest.raises(FileNotFoundError):
        child.start()
    record = json.loads((tmp_path/'process'/'process.json').read_text())
    assert child.pid is None
    assert record['failure'] == 'FileNotFoundError'
    assert record['exitCode'] == 127 and record['endedAt']


def test_uncooperative_child_is_killed_after_bounded_grace(tmp_path):
    child = transport(tmp_path, "import signal,time,sys,json\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                               "line=sys.stdin.readline()\nprint(json.dumps({'seen':json.loads(line)['id']}),flush=True)\ntime.sleep(30)")
    with child:
        assert child.exchange({'id': 'alive'}) == {'seen': 'alive'}
        started = time.monotonic()
        child.stop()
        assert child.returncode == -9
        assert time.monotonic()-started < 3


@pytest.mark.parametrize('budget', [float('nan'), float('inf'), 0, -1])
def test_nonfinite_or_nonpositive_budget_cannot_create_unbounded_process(tmp_path, budget):
    child = transport(tmp_path, ECHO)
    with pytest.raises(ValueError):
        type(child)(child.argv, cwd=tmp_path, output=tmp_path/'budget', timeout=budget)
    assert not (tmp_path/'budget').exists()


def test_request_limit_includes_line_terminator_and_preserves_stream(tmp_path):
    child = transport(tmp_path, ECHO)
    with child:
        # The compact object is exactly 1 MiB before its required newline.
        with pytest.raises(ValueError, match='line exceeds'):
            child.exchange({'blob': 'a'*(1048576-11)})
        assert child.exchange({'id': 'valid'}) == {'seen': 'valid'}


def test_response_limit_includes_line_terminator(tmp_path):
    program = "import sys,time\nsys.stdin.readline()\nsys.stdout.write('{\"blob\":\"'+'a'*(1048576-11)+'\"}\\n');sys.stdout.flush()\ntime.sleep(30)"
    child = transport(tmp_path, program)
    with child:
        with pytest.raises(ValueError, match='line exceeds'):
            child.exchange({'id': 'boundary'})
        assert child.returncode is not None
