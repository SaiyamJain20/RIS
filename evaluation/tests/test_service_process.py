"""Synthetic direct-service processes only; these are not Anvil/provider tests."""
import importlib
import json
import subprocess
import sys
import time

import pytest


def service(tmp_path, program):
    module = importlib.import_module('evaluation.processes')
    assert hasattr(module, 'ServiceProcess'), 'C-E1 service lifecycle is not implemented'
    return module.ServiceProcess([sys.executable, '-u', '-c', program], cwd=tmp_path,
                                 output=tmp_path/'service', stop_grace=0.2)


def test_stdout_stderr_flood_does_not_wedge_readiness_or_cleanup(tmp_path):
    child = service(tmp_path, "import sys,time,pathlib\nsys.stdout.write('o'*200000);sys.stdout.flush()\nsys.stderr.write('e'*200000);sys.stderr.flush()\npathlib.Path('ready').write_text('yes')\ntime.sleep(30)")
    with child:
        child.wait_ready(lambda: (tmp_path/'ready').is_file(), timeout=1)
        assert child.pid > 0 and child.returncode is None
    record = json.loads((tmp_path/'service/process.json').read_text())
    assert record['exitCode'] == -15 and record['endedAt']
    assert record['readyAt'] and record['stdoutSha256'] and record['stderrSha256']
    assert (tmp_path/'service/stdout.log').read_text() == 'o'*200000
    assert (tmp_path/'service/stderr.log').read_text() == 'e'*200000
    child.stop()


def test_direct_service_uses_explicit_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('HMBC_TEST_SERVICE_ENV','ambient')
    module=importlib.import_module('evaluation.processes')
    program="import os,pathlib,time\npathlib.Path('ready').write_text(os.environ['HMBC_TEST_SERVICE_ENV'])\ntime.sleep(30)"
    with module.ServiceProcess([sys.executable,'-u','-c',program],cwd=tmp_path,output=tmp_path/'service',
                               env={'HMBC_TEST_SERVICE_ENV':'pinned'},stop_grace=0.2) as child:
        child.wait_ready(lambda:(tmp_path/'ready').is_file(),timeout=1)
        assert (tmp_path/'ready').read_text()=='pinned'
    assert 'pinned' not in (tmp_path/'service/process.json').read_text()


def test_readiness_timeout_stops_only_owned_direct_child(tmp_path):
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
    try:
        child = service(tmp_path, 'import time;time.sleep(30)')
        with child:
            began = time.monotonic()
            with pytest.raises(TimeoutError): child.wait_ready(lambda: False, timeout=0.15)
            assert child.returncode is not None and time.monotonic()-began < 2
        assert unrelated.poll() is None
        assert json.loads((tmp_path/'service/process.json').read_text())['failure'] == 'TimeoutError'
    finally:
        unrelated.terminate();unrelated.wait(timeout=2)


def test_dead_service_cannot_be_ready_and_keeps_actual_exit(tmp_path):
    child = service(tmp_path, 'import sys;sys.exit(7)')
    with child:
        with pytest.raises(ChildProcessError):
            child.wait_ready(lambda: False, timeout=1)
    assert child.returncode == 7
    record = json.loads((tmp_path/'service/process.json').read_text())
    assert record['exitCode'] == 7 and record['failure'] == 'ChildProcessError'
    assert record['readyAt'] is None


def test_probe_error_is_propagated_and_child_is_stopped(tmp_path):
    child = service(tmp_path, 'import time;time.sleep(30)')
    def bad_probe(): raise ValueError('wrong chain identity')
    with child:
        with pytest.raises(ValueError, match='wrong chain'):child.wait_ready(bad_probe, timeout=1)
        assert child.returncode is not None
    assert json.loads((tmp_path/'service/process.json').read_text())['failure'] == 'ValueError'


def test_service_existing_output_is_never_overwritten(tmp_path):
    child = service(tmp_path, 'import time;time.sleep(30)')
    (tmp_path/'service').mkdir();(tmp_path/'service/keep').write_text('keep')
    with pytest.raises(FileExistsError):child.start()
    assert child.pid is None and (tmp_path/'service/keep').read_text() == 'keep'


def test_service_missing_executable_preserves_start_failure(tmp_path):
    child = service(tmp_path, '')
    child.argv = [str(tmp_path/'nonexistent')]
    with pytest.raises(FileNotFoundError):child.start()
    record = json.loads((tmp_path/'service/process.json').read_text())
    assert child.pid is None and record['exitCode'] == 127
    assert record['failure'] == 'FileNotFoundError' and record['endedAt']


@pytest.mark.parametrize('budget', [float('nan'), float('inf'), 0, -1])
def test_readiness_budget_is_validated_before_running_probe(tmp_path, budget):
    child = service(tmp_path, 'import time;time.sleep(30)')
    calls = []
    with child:
        with pytest.raises(ValueError):child.wait_ready(lambda: calls.append(True), timeout=budget)
        assert calls == []
        assert child.returncode is None  # Caller validation failure does not poison service.
