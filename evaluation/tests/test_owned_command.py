"""Real local process controls; never ledger/service gate evidence."""
import json
from pathlib import Path
import sys
import time

from evaluation.manifests import record_command


def test_timeout_stops_owned_script_descendant(tmp_path):
    child_file = tmp_path/'child.pid'
    script = ("import subprocess,sys,time; from pathlib import Path; "
              "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
              "Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(30)")
    row = record_command([sys.executable, '-c', script, str(child_file)], tmp_path,
                         tmp_path/'command.txt', timeout=.5, owned_process_group=True, stop_grace=.05)
    assert row['exitCode'] == 124 and row['timedOut']
    assert row['pid'] == row['processGroup'] and row['groupCleanup'] == 'TERM_THEN_KILL'
    state = json.loads((tmp_path/'command.txt.process.json').read_text())
    assert state['status'] == 'STOPPED' and state['pid'] == row['pid']
    child = int(child_file.read_text())
    deadline = time.monotonic()+2
    while time.monotonic() < deadline:
        try: state = Path(f'/proc/{child}/stat').read_text().split(') ')[1][0]
        except FileNotFoundError: break
        if state == 'Z': break  # dead, awaiting the host's orphan reaper
        time.sleep(.02)
    else: raise AssertionError('Owned descendant remained live after timeout')


def test_owned_command_retains_normal_exit_and_environment_hash(tmp_path):
    row = record_command([sys.executable, '-c', 'import os; print(os.environ["CONTROL"])'],
                         tmp_path, tmp_path/'command.txt', env={'CONTROL': 'fixture'},
                         owned_process_group=True)
    assert row['exitCode'] == 0 and not row['timedOut']
    assert (tmp_path/'command.txt').read_text() == 'fixture\n'
    assert row['environmentSha256'] and 'fixture' not in json.dumps(row)
    assert row['groupCleanup'] is None
    assert json.loads((tmp_path/'command.txt.process.json').read_text())['status'] == 'STOPPED'
