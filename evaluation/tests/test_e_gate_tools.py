"""Gate tool checks refuse failed commands or changed pins before execution.

Real harmless executable probes; no services, owner changes or cryptographic
claims. Missing fail-closed checks allow sentinel side effects from a changed
binary/model. A healthy positive control prevents deny-all from passing.
"""
import hashlib
import platform
import sys

import pytest

from evaluation import e_gate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def executable(path, source):
    path.write_text('#!'+sys.executable+'\n'+source+'\n'); path.chmod(0o700)
    return dict(path=str(path), sha256=digest(path))


def versions_plan(tmp_path, failed=None):
    marker = tmp_path/'versions-executed'
    tools = {name: executable(tmp_path/name,
                 'from pathlib import Path; Path('+repr(str(marker))+').write_text("executed"); '
                 'print("synthetic version"); raise SystemExit('+str(1 if name == failed else 0)+')')
             for name, _ in e_gate.VERSION_ARGS}
    plan = dict(slices=[dict(plan=dict(tools={k:v for k,v in tools.items() if k != 'proverif'},
                                      pythonVersion=platform.python_version(), packagePins={}))],
                proverif=dict(tool=tools['proverif'], environment={}))
    return plan, marker


@pytest.mark.parametrize('failed', ['forge', 'anvil', 'cast', 'solc', 'python', 'python3', 'bash', 'proverif'])
def test_nonzero_version_command_cannot_mark_tools_verified(tmp_path, failed):
    plan, marker = versions_plan(tmp_path, failed)
    result = e_gate._versions(plan, tmp_path/'output')
    assert result['tools'][failed]['exitCode'] == 1
    assert all(row['hashOk'] for row in result['tools'].values())
    assert result['ok'] is False


def test_successful_version_commands_remain_verified(tmp_path):
    plan, _ = versions_plan(tmp_path)
    result = e_gate._versions(plan, tmp_path/'output')
    assert result['ok'] is True and all(row['exitCode'] == 0 for row in result['tools'].values())


def test_changed_version_binary_is_refused_before_execution(tmp_path):
    plan, marker = versions_plan(tmp_path)
    plan['slices'][0]['plan']['tools']['forge']['sha256'] = '00'*32
    with pytest.raises(ValueError, match='hash'):
        e_gate._versions(plan, tmp_path/'output')
    assert not marker.exists()


def proverif_plan(tmp_path):
    marker = tmp_path/'proverif-executed'
    text = 'RESULT event(Grant()) is true.\n'
    tool = executable(tmp_path/'proverif',
                      'from pathlib import Path; Path('+repr(str(marker))+').write_text("executed"); '
                      'print('+repr(text)+', end="")')
    model = tmp_path/'model.pv'; model.write_text('synthetic model input\n')
    reference = tmp_path/'reference.stdout'; reference.write_text(text)
    plan = dict(proverif=dict(tool=tool, environment={}, timeoutSeconds=2,
        models=[dict(model=str(model), sha256=digest(model), expectedVerdicts=['true'],
                     references={'checked': dict(path=str(reference), sha256=digest(reference))})]))
    return plan, marker


@pytest.mark.parametrize('changed', ['tool', 'model'])
def test_changed_proverif_input_is_refused_before_execution(tmp_path, changed):
    plan, marker = proverif_plan(tmp_path)
    if changed == 'tool': plan['proverif']['tool']['sha256'] = '00'*32
    else: plan['proverif']['models'][0]['sha256'] = '00'*32
    with pytest.raises(ValueError, match='hash'):
        e_gate.run_proverif(plan, tmp_path/'output')
    assert not marker.exists()


def test_verified_proverif_input_can_execute_and_match(tmp_path):
    plan, marker = proverif_plan(tmp_path)
    result = e_gate.run_proverif(plan, tmp_path/'output')
    assert result['matched'] is True and marker.exists()


def test_proverif_binary_change_during_execution_cannot_match(tmp_path):
    plan, _ = proverif_plan(tmp_path)
    path = tmp_path/'proverif'
    source = ('from pathlib import Path; Path('+repr(str(path))+').write_text("changed binary"); '
              'print("RESULT event(Grant()) is true.")')
    plan['proverif']['tool'] = executable(path, source)
    result = e_gate.run_proverif(plan, tmp_path/'output')
    assert result['matched'] is False and result['tool']['hashOk'] is False
