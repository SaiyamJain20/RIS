"""Conservative isolated review selection plus native-process execution guard."""
import json
import os
from pathlib import Path
import sys

BLOCKED = []


def prohibited(name):
    return name.startswith(('ledger_chains', 'live_')) or name=='peer_root'


def audit(event, args):
    if event=='subprocess.Popen':
        executable, argv, *_ = args
        binary=Path(os.fsdecode(executable)).name
        offline_cast = binary=='cast' and len(argv)>1 and argv[1] in ('sig','calldata','abi-encode','abi-decode','keccak')
        if binary in ('anvil','forge','cast','java') and not offline_cast:
            BLOCKED.append(dict(executable=os.fsdecode(executable),argv=argv))
            raise RuntimeError('Isolated review prohibits native chain/build/model process: '+binary)


def pytest_sessionstart(session):
    sys.addaudithook(audit)


def pytest_fixture_setup(fixturedef, request):
    if prohibited(fixturedef.argname):
        raise RuntimeError('Selection missed prohibited live fixture: '+fixturedef.argname)


def pytest_collection_modifyitems(config, items):
    selected, excluded, reasons = [], [], {}
    for item in items:
        params=getattr(getattr(item,'callspec',None),'params',{})
        dynamic=params.get('fixture_name','')
        reason=None
        if Path(str(item.path)).name.endswith('_live.py'):
            reason='live test module (conservative whole-module exclusion)'
        elif any(prohibited(n) for n in item.fixturenames):
            reason='live/build fixture closure'
        elif isinstance(dynamic,str) and dynamic.startswith(('world','ledger','live_')):
            reason='dynamic live fixture_name'
        elif item.originalname=='test_zz_every_catalog_case_was_executed_exactly_once':
            reason='catalog completeness needs excluded live cases'
        if reason:
            excluded.append(item);reasons[item.nodeid]=reason
        else:selected.append(item)
    output=Path(os.environ['RIS_REVIEW_DESELECTION'])
    assert not output.exists(), 'immutable selection output'
    output.write_text(json.dumps(dict(selected=[i.nodeid for i in selected],
        excluded=[i.nodeid for i in excluded],reasons=reasons),indent=2)+'\n')
    items[:]=selected;config.hook.pytest_deselected(items=excluded)


def pytest_sessionfinish(session, exitstatus):
    output=Path(os.environ['RIS_REVIEW_PROCESS_GUARD'])
    assert not output.exists(), 'immutable guard output'
    output.write_text(json.dumps(dict(exitstatus=int(exitstatus),blocked=BLOCKED),indent=2)+'\n')
