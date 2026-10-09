"""Real synthetic child pipes; no ledger, worker or integrated crash evidence.

Catch false crash acceptance from incomplete/extra frames, wrong death status,
nonempty stderr, hangs, ignored validators and token-bearing public transcripts.
"""
import hashlib
import json
import sys
import time

import pytest
from evaluation.processes import JsonLinesProcess


def child(tmp_path, program):
    # Match actual entrypoint argv: put synthetic behavior in a file. Embedding
    # a token literal in `-c` would test command logging instead of pipe logging.
    script=tmp_path/'synthetic_child.py'
    script.write_text('import sys,os,json,time\nline=sys.stdin.readline()\n'+program)
    return JsonLinesProcess([sys.executable, '-u', str(script)],
                            cwd=tmp_path, output=tmp_path/'process',timeout=.5,stop_grace=.1)


def observe(process, point, validator=lambda value: None):
    assert hasattr(process, 'exchange_crash'), 'C-E2 crash observation transport is missing'
    return process.exchange_crash({'synthetic': 'request'},point=point,validate_response=validator)


@pytest.mark.parametrize('point,program,want',[
    ('after_intent','os._exit(86)',None),
    ('after_send',"print(json.dumps({'secret':'synthetic-token'}),flush=True)\nos._exit(86)",{'secret':'synthetic-token'}),
])
def test_expected_terminal_exit_is_observed_without_token_transcript(tmp_path,point,program,want):
    calls=[]
    with child(tmp_path,program) as p:
        result=observe(p,point,lambda value:calls.append(value))
        assert result==want and p.returncode==86
    record=json.loads((tmp_path/'process/process.json').read_text())
    assert record['exitCode']==86 and record['failure'] is None
    assert record['exchanges'][0]['crashPoint']==point
    assert record['exchanges'][0]['terminalObserved'] is True
    assert record['stderrSha256']==hashlib.sha256(b'').hexdigest()
    assert calls==([] if want is None else [want])
    assert 'synthetic-token' not in (tmp_path/'process/process.json').read_text()


@pytest.mark.parametrize('point,program',[
    ('after_intent','os._exit(0)'),
    ('after_intent',"sys.stdout.write('{');sys.stdout.flush();os._exit(86)"),
    ('after_intent',"print('{}',flush=True);os._exit(86)"),
    ('after_intent',"print('error',file=sys.stderr,flush=True);os._exit(86)"),
    ('after_send','os._exit(86)'),
    ('after_send',"print('{}',flush=True);time.sleep(.02);print('{}',flush=True);os._exit(86)"),
    ('after_send',"print('{bad}',flush=True);os._exit(86)"),
    ('after_send',"print('{}',flush=True);os._exit(7)"),
    ('after_send',"print('{}',flush=True);time.sleep(30)"),
    ('after_intent','time.sleep(30)'),
])
def test_incomplete_or_wrong_terminal_observation_is_not_a_crash_pass(tmp_path,point,program):
    p=child(tmp_path,program)
    with p:
        started=time.monotonic()
        with pytest.raises((ValueError,ChildProcessError,TimeoutError)):
            observe(p,point)
        assert p.returncode is not None and time.monotonic()-started<3
    record=json.loads((tmp_path/'process/process.json').read_text())
    assert record['failure'] and not record['exchanges'][0]['terminalObserved']


def test_invalid_point_does_not_send_request_or_poison_usable_stream(tmp_path):
    with child(tmp_path,'os._exit(86)') as p:
        with pytest.raises(ValueError):observe(p,'unknown')
        assert p.returncode is None
        assert observe(p,'after_intent') is None


def test_response_validator_rejection_is_preserved_and_closes_child(tmp_path):
    def reject(value):raise ValueError('frozen response rejected')
    with child(tmp_path,"print('{}',flush=True);os._exit(86)") as p:
        with pytest.raises(ValueError,match='frozen response rejected'):
            observe(p,'after_send',reject)
        assert p.returncode is not None
