"""Native capture acquisition: synthetic transports, real ABIs and signatures.

Breaks caught: number-selected calls/fork collapse, unbracketed deployment
identity, missing history/death checks, lost partial results, input/ABI drift.
No live node, owner runtime, source-state truth or timing theorem is exercised.
"""
import copy
import importlib
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from evaluation.tests.test_witness_native_v2 import setup, ABI, DEATHS, captures
from evaluation.tests.test_witness_history_v2 import fingerprint

BAD = (ValueError, ValidationError)


class Rpc:
    def __init__(self, m, o, blocks, calls, chain):
        self.chain = chain
        self.pin = m['chains'][chain]
        self.url = self.pin['rpcUrl']
        self.observed = o[chain]
        self.requests = []
        self.checkpoints = []
        self.rewrite = lambda method, params, result: result
        self.headers = {r['raw']['hash']: copy.deepcopy(r['raw']) for r in blocks if r['chainId'] == self.pin['chainId']}
        self.answers = {(r['blockHash'], r['to'], r['data']): r['result'] for r in calls if r['chainId'] == self.pin['chainId']}
        self.identities = {'0x0': {'number': '0x0', 'hash': self.observed['genesisHash']}}
        for field in ('deployBlock', 'anchor'):
            b = self.observed[field]
            self.identities[hex(int(b['number']))] = {'number': hex(int(b['number'])), 'hash': b['hash']}

    def checkpoint(self, label):
        self.checkpoints.append(label)

    def call(self, method, params=None):
        params = [] if params is None else params
        self.requests.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            assert params == []
            result = hex(int(self.pin['chainId']))
        elif method == 'eth_getBlockByNumber':
            assert params[1] is False and params[0].startswith('0x')
            result = self.identities.get(params[0])
            if result is None:
                result = next(r for r in self.headers.values() if r['number'] == params[0])
        elif method == 'eth_getBlockByHash':
            assert params[1] is False
            result = self.headers[params[0]]
        elif method == 'eth_call':
            assert set(params[0]) == {'to', 'data'}
            assert set(params[1]) == {'blockHash', 'requireCanonical'}
            assert type(params[1]['requireCanonical']) is bool
            result = self.answers[(params[1]['blockHash'], params[0]['to'], params[0]['data'])]
        else:
            raise AssertionError('Unexpected RPC method ' + method)
        return self.rewrite(method, params, copy.deepcopy(result))


def case(name='StateCheckpoint', kind='overtaken-checkpoint', f=True, q='3'):
    m, o, e, blocks, calls = setup(name, kind, f=f, q=q)
    clients = {c: Rpc(m, o, blocks, calls, c) for c in ('pbc', 'dbc')}
    return m, o, e, blocks, calls, clients


def collect(tmp_path, args, **over):
    m, o, e, _, _, clients = args
    kwargs = dict(manifest=m, observations=o, expected_owner=e['owner'],
        abi_paths={n: ABI/(n+'.json') for n in m['abi']}, rpcs=clients,
        output=tmp_path/'capture', compiled_max_admins='8' if m['profileEnum']=='3' else None)
    kwargs.update(over)
    return importlib.import_module('evaluation.history_rpc_v2').collect(e, **kwargs)


def report(tmp_path):
    return json.loads((tmp_path/'capture/transcript.json').read_text())


@pytest.mark.parametrize('name,kind', DEATHS)
def test_all_native_deaths_and_exact_rpc_receipts(tmp_path, name, kind):
    args = case(name, kind); original = copy.deepcopy(args[:5])
    result = collect(tmp_path, args)
    assert args[:5] == original
    assert result['verification']['recordsChecked'] == 5
    assert result['verification']['nativeDeathsChecked'] == 1
    assert result['verification']['nativeCallsChecked'] == (0 if kind=='expiry' else 1)
    assert {(r['chainId'],r['raw']['hash']) for r in result['blocks']} == {(r['chainId'],r['raw']['hash']) for r in args[3]}
    assert result['calls'] == args[4]
    saved = report(tmp_path)
    assert saved['status'] == 'complete' and saved['calls']
    assert json.loads((tmp_path/'capture/result.json').read_text()) == result
    for row in saved['calls']:
        assert row['status']=='returned' and row['origin']==args[0]['chains'][row['chain']]['rpcUrl']
        if row['method']=='eth_call':
            assert row['params'][1]['requireCanonical'] is True
    for client in args[-1].values():
        assert [m for m,p in client.requests].count('eth_chainId')==2
        assert client.checkpoints==['history-read-before','history-read-after']
    # Both before-identity groups precede captures; BOTH after groups follow all captures.
    indices = [i for i,r in enumerate(saved['calls']) if r['method']=='eth_getBlockByHash']
    for chain in ('pbc','dbc'):
        ids=[i for i,r in enumerate(saved['calls']) if r['chain']==chain and r['method']=='eth_chainId']
        assert ids[0] < min(indices) < max(indices) < ids[1]


@pytest.mark.parametrize('f,q',[(True,'3'),(True,'2'),(False,'1')])
def test_empty_history_is_still_bound_to_both_deployment_identities(tmp_path,f,q):
    args=case(name=None,f=f,q=q)
    args[2].update(conflicts=[],observations=[]);fingerprint(args[2])
    result=collect(tmp_path,args)
    assert result['blocks']==[] and result['calls']==[] and result['verification']['recordsChecked']==0
    assert all([m for m,p in c.requests].count('eth_chainId')==2 for c in args[-1].values())


@pytest.mark.parametrize('chain',['pbc','dbc'])
@pytest.mark.parametrize('field',['chainId','genesis','deploy','anchor'])
@pytest.mark.parametrize('when',['before','after'])
def test_wrong_deployment_identity_at_either_boundary_refuses(tmp_path,chain,field,when):
    args=case();rpc=args[-1][chain];hits=0
    target={'genesis':'0x0','deploy':hex(int(rpc.pin['deployBlock'])),'anchor':hex(int(rpc.observed['anchor']['number']))}.get(field)
    def rewrite(method,params,result):
        nonlocal hits
        selected=method=='eth_chainId' if field=='chainId' else method=='eth_getBlockByNumber' and params[0]==target
        if selected:
            hits+=1
            if hits==(1 if when=='before' else 2):
                return '0x999' if field=='chainId' else {**result,'hash':'0x'+'ff'*32}
        return result
    rpc.rewrite=rewrite
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed' and not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('method',['eth_chainId','eth_getBlockByNumber','eth_getBlockByHash','eth_call'])
def test_rpc_exception_survives_as_failed_partial_transcript(tmp_path,method):
    args=case()
    def fail(m,p,r):
        if m==method:raise RuntimeError('synthetic failure')
        return r
    for c in args[-1].values():c.rewrite=fail
    with pytest.raises(RuntimeError):collect(tmp_path,args)
    saved=report(tmp_path)
    assert saved['status']=='failed' and saved['calls'][-1]['status']=='failed'
    assert saved['calls'][-1]['method']==method and not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('field',['number','timestamp','hash','null','quantity'])
def test_raw_header_errors_are_not_normalized_away(tmp_path,field):
    args=case()
    def corrupt(m,p,r):
        if m!='eth_getBlockByHash':return r
        if field=='null':return None
        if field=='quantity':return {**r,'number':'0x00'}
        return {**r,field:('0x'+'ff'*32 if field=='hash' else hex(int(r[field],16)+1))}
    for c in args[-1].values():c.rewrite=corrupt
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('value',['0x01','0x'+'00'*128])
def test_real_abi_decoder_refuses_false_or_malformed_death(tmp_path,value):
    args=case();args[-1]['dbc'].rewrite=lambda m,p,r:value if m=='eth_call' else r
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed'


@pytest.mark.parametrize('what',['manifest','history','observations','ABI','RPC-inventory'])
def test_transport_cannot_replace_pins_during_collection(tmp_path,what):
    args=case();m,o,e,_,_,clients=args
    paths={n:ABI/(n+'.json') for n in m['abi']}
    if what=='ABI':
        p=tmp_path/'KSSC.json';p.write_bytes(paths['KSSC'].read_bytes());paths['KSSC']=p
    changed=False
    def mutate(method,params,result):
        nonlocal changed
        if not changed:
            changed=True
            if what=='manifest':m['mutantNote']='changed'
            elif what=='history':e['marker']['schema']='1'
            elif what=='observations':o['pbc']['genesisHash']='0x'+'ff'*32
            elif what=='ABI':paths['KSSC'].write_text('[]')
            else:clients['dbc']=clients['pbc']
        return result
    clients['pbc'].rewrite=mutate
    with pytest.raises(ValueError):collect(tmp_path,args,abi_paths=paths)
    assert report(tmp_path)['status']=='failed' and not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('what',['signature','owner','ABI','RPC','origin','timeout','budget'])
def test_invalid_selection_refuses_before_io(tmp_path,what):
    args=case();over={}
    if what=='signature':args[2]['conflicts'][0]['digests'][0]['digest']='0x'+'ff'*32;fingerprint(args[2])
    elif what=='owner':over['expected_owner']='worker'
    elif what=='ABI':over['abi_paths']={}
    elif what=='RPC':over['rpcs']={'pbc':args[-1]['pbc']}
    elif what=='origin':args[-1]['pbc'].url='http://127.0.0.1:19999'
    elif what=='timeout':over['timeout']=float('nan')
    else:over['max_calls']=True
    with pytest.raises(BAD):collect(tmp_path,args,**over)
    assert not (tmp_path/'capture').exists() and all(not c.requests for c in args[-1].values())


def test_call_budget_and_elapsed_deadline_keep_partial_failure(tmp_path,monkeypatch):
    args=case()
    with pytest.raises(ValueError,match='budget'):collect(tmp_path,args,max_calls=1)
    assert len(report(tmp_path)['calls'])==1 and report(tmp_path)['status']=='failed'
    mod=importlib.import_module('evaluation.history_rpc_v2')
    ticks=iter([0,0,0,2,2,2,2,2])
    monkeypatch.setattr(mod.time,'monotonic',lambda:next(ticks))
    other=tmp_path/'timeout';other.mkdir()
    with pytest.raises(TimeoutError):collect(other,case(),timeout=1)
    assert report(other)['status']=='failed' and not (other/'capture/result.json').exists()


@pytest.mark.parametrize('clear',[False,True])
def test_same_height_forks_are_retained_only_as_labelled_fault_captures(tmp_path,clear):
    args=case();m,o,e,_,_,_=args
    previous=copy.deepcopy(e['observations'][0]);seen={**previous,'blockHash':'0x'+'ef'*32}
    fault=dict(reason='hash-changed',previous=previous,observed=seen)
    if clear:e['faultLog']=[dict(seq='1',fault=fault,clearedAgainst=copy.deepcopy(previous),note='synthetic')]
    else:e['faulted']=fault
    fingerprint(e);b,c=captures(m,e)
    from evaluation.tests.test_witness_native_v2 import add_call
    for row in e['superseded']:add_call(m,c,row)
    args=m,o,e,b,c,{n:Rpc(m,o,b,c,n) for n in ('pbc','dbc')}
    result=collect(tmp_path,args)
    assert result['verification']['declaredSafeLedgerInterval'] is False
    assert {r['raw']['hash'] for r in result['blocks']} >= {previous['blockHash'],seen['blockHash']}
    assert all(r['params'][1]['requireCanonical'] is False for r in report(tmp_path)['calls'] if r['method']=='eth_call')


def test_existing_output_is_never_overwritten(tmp_path):
    (tmp_path/'capture').mkdir();(tmp_path/'capture/retained').write_text('original')
    with pytest.raises(FileExistsError):collect(tmp_path,case())
    assert (tmp_path/'capture/retained').read_text()=='original'


def test_later_dbc_reads_cannot_hide_a_changed_pbc_identity(tmp_path):
    args=case();pbc=args[-1]['pbc'];dbc=args[-1]['dbc']
    def alter(m,p,r):
        pbc.identities['0x0']['hash']='0x'+'ff'*32
        return r
    dbc.rewrite=alter
    with pytest.raises(ValueError,match='identity'):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed'


def test_same_hash_header_time_must_remain_stable_after_death_calls(tmp_path):
    args=case();rpc=args[-1]['dbc'];seen={}
    def alter(m,p,r):
        if m=='eth_getBlockByHash':
            seen[p[0]]=seen.get(p[0],0)+1
            if seen[p[0]]==2:
                r['timestamp']=hex(int(r['timestamp'],16)+1)
                rpc.headers[p[0]]=copy.deepcopy(r)  # make the canonical read agree too
        return r
    rpc.rewrite=alter
    with pytest.raises(ValueError,match='changed after capture'):collect(tmp_path,args)
    assert not (tmp_path/'capture/result.json').exists()


def test_declared_safe_history_must_be_canonical_at_collection(tmp_path):
    args=case();rpc=args[-1]['pbc']
    rpc.rewrite=lambda m,p,r:{**r,'hash':'0x'+'ef'*32} if m=='eth_getBlockByNumber' and p[0] not in rpc.identities else r
    with pytest.raises(ValueError,match='canonical'):collect(tmp_path,args)


def test_hash_call_unsupported_is_a_retained_failure_without_numeric_fallback(tmp_path):
    args=case()
    def unsupported(m,p,r):
        if m=='eth_call':raise RuntimeError('hash selector unsupported')
        return r
    args[-1]['dbc'].rewrite=unsupported
    with pytest.raises(RuntimeError,match='unsupported'):collect(tmp_path,args)
    rows=[r for r in report(tmp_path)['calls'] if r['method']=='eth_call']
    assert len(rows)==1 and rows[0]['params'][1]['requireCanonical'] is True and rows[0]['status']=='failed'


def test_transcript_retains_original_params_when_transport_edits_its_argument(tmp_path):
    args=case()
    def mutate(m,p,r):
        if m=='eth_call':p[1]['blockHash']='0x'+'ff'*32
        return r
    args[-1]['dbc'].rewrite=mutate
    result=collect(tmp_path,args)
    row=next(r for r in report(tmp_path)['calls'] if r['method']=='eth_call')
    assert row['params'][1]['blockHash']==result['calls'][0]['blockHash']
