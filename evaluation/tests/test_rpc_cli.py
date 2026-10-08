"""Synthetic Cast-shaped CLI processes; no chain/RPC service is started."""
import importlib
import json
import sys
from pathlib import Path

import pytest

from evaluation.manifests import sha256


def client(tmp_path, program='import json,sys;print(json.dumps(sys.argv[1:]))', url='http://127.0.0.1:18545', timeout=0.2, **kwargs):
    executable=tmp_path/'cast-probe';executable.write_text('#!'+sys.executable+'\n'+program+'\n');executable.chmod(0o700)
    try:module=importlib.import_module('evaluation.rpc')
    except ModuleNotFoundError:pytest.fail('C-E1 bounded public RPC CLI is not implemented')
    return module.RpcClient(url,cast=executable,cast_sha256=sha256(executable),cwd=tmp_path,output=tmp_path/'rpc',timeout=timeout,**kwargs)


def test_rpc_cli_uses_frozen_environment(tmp_path,monkeypatch):
    monkeypatch.setenv('HMBC_TEST_RPC_ENV','ambient')
    c=client(tmp_path,'import os,json;print(json.dumps(os.environ["HMBC_TEST_RPC_ENV"]))',env={'HMBC_TEST_RPC_ENV':'pinned'})
    assert c.call('eth_chainId')=='pinned'


def test_raw_params_are_single_json_argument_without_shell_interpretation(tmp_path):
    c=client(tmp_path);params=['$(touch must-not-exist)',{'nested':[1,True]}]
    args=c.call('eth_call',params)
    assert args[0:3]==['rpc','eth_call',json.dumps(params,separators=(',',':'))]
    assert '--raw' in args and '--no-proxy' in args and c.url in args
    assert not (tmp_path/'must-not-exist').exists()
    rows=json.loads((tmp_path/'rpc/commands.json').read_text());assert len(rows)==1 and rows[0]['exitCode']==0


@pytest.mark.parametrize('url',['https://127.0.0.1:18545','http://example.com:18545','http://127.0.0.1:18545/path','http://user@127.0.0.1:18545','http://localhost:18545'])
def test_nonliteral_or_nonlocal_rpc_endpoint_refused_before_start(tmp_path,url):
    with pytest.raises(ValueError):client(tmp_path,url=url)
    assert not (tmp_path/'rpc').exists()


def test_failed_public_cli_retains_exit_and_output_hash(tmp_path):
    c=client(tmp_path,'import sys;print("observed failure");sys.exit(7)')
    with pytest.raises(RuntimeError):c.call('eth_chainId')
    rows=json.loads((tmp_path/'rpc/commands.json').read_text());assert rows[0]['exitCode']==7 and rows[0]['outputSha256']


def test_cli_wall_timeout_is_recorded_and_reaped(tmp_path):
    c=client(tmp_path,'import time;time.sleep(30)',timeout=0.1)
    with pytest.raises(RuntimeError):c.call('eth_chainId')
    rows=json.loads((tmp_path/'rpc/commands.json').read_text());assert rows[0]['exitCode']==124 and rows[0]['timedOut'] is True


@pytest.mark.parametrize('reply',['NaN','{"value":1e999}','{"x":1,"x":2}','{}\n{}','not json'])
def test_malformed_cli_output_is_rejected_and_retained(tmp_path,reply):
    c=client(tmp_path,f'print({reply!r})')
    with pytest.raises(ValueError):c.call('eth_chainId')
    rows=json.loads((tmp_path/'rpc/commands.json').read_text());assert rows[0]['exitCode']==0 and rows[0]['outputSha256']


def test_changed_cli_pin_is_not_executed(tmp_path):
    c=client(tmp_path);c.cast.write_text('#!'+sys.executable+'\nraise SystemExit(7)\n')
    with pytest.raises(ValueError,match='hash'):c.call('eth_chainId')
    assert json.loads((tmp_path/'rpc/commands.json').read_text())==[]
