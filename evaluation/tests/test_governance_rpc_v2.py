"""Synthetic RPCs, real signed history/ABI checks; no native node or service.

Breaks caught: lost old/refined digests, wrong exact hash/getter, forged approvals,
identity/header/input drift, swallowed failures and false provenance claims.
"""
import copy
import importlib
import json

from eth_abi import encode
from jsonschema import ValidationError
import pytest

from evaluation.manifests import canonical_hash
from evaluation.tests.test_governance_history_v2 import history, conflict
from evaluation.tests.test_history_rpc_v2 import Rpc
from evaluation.tests.test_witness_history_v2 import fingerprint, fault

BAD = (ValueError, ValidationError)


def case(generations=1, refinements=1, action='1', q='3', args=None):
    args = history(generations, refinements, action, q) if args is None else args
    caps = args.pop('captures')
    blocks = {(r['chainId'], r['raw']['hash']): r for c in caps for r in c['blocks']}
    calls = {tuple(r[k] for k in ('chainId','blockHash','to','data')): r for c in caps for r in c['calls']}
    args['rpcs'] = {c: Rpc(args['manifest'], args['observations'], blocks.values(), calls.values(), c)
                    for c in ('pbc','dbc')}
    args['approval_reason'] = 'synthetic caller approval fixture; no producer policy evidence'
    return args


def collect(tmp_path, args, **over):
    return importlib.import_module('evaluation.governance_rpc_v2').collect(
        **(args | dict(output=tmp_path/'capture') | over))


def report(tmp_path):
    return json.loads((tmp_path/'capture/transcript.json').read_text())


@pytest.mark.parametrize('generations,refinements,action,q', [
    (1,1,'1','3'), (3,2,'1','3'), (1,2,'2','3'), (1,2,'3','3'), (1,1,'1','2')])
def test_every_digest_exact_capture_and_unsigned_provenance(tmp_path,generations,refinements,action,q):
    args=case(generations,refinements,action,q)
    original=copy.deepcopy({k:v for k,v in args.items() if k!='rpcs'})
    result=collect(tmp_path,args)
    assert {k:v for k,v in args.items() if k!='rpcs'}==original
    assert result['verification']['governanceStateSignaturesChecked']==generations*refinements
    assert result['verification']['signaturesChecked']==3+generations*refinements
    assert result['verification']['declaredSafeLedgerInterval'] is True
    assert result['signTimeEstablished'] is False and result['latestHeadEstablished'] is False
    assert result['approvalPolicyEstablished'] is False
    assert len(result['captures'])==generations*refinements
    for cap,p in zip(result['captures'],result['provenance']):
        collection,index,digest_index=p['historyLocation']
        signed=args['evidence'][collection][index]['digests'][digest_index]
        assert signed['digest']==p['digest']==cap['digest']
        assert signed['observation']==p['pbcObservation']
        assert p['pbcObservationBasis']=='unsigned-exporter-observation'
        assert p['signatureBindsObservation'] is False
        assert set(cap)=={'digest','blocks','calls'}
        assert len(cap['blocks'])==1 and len(cap['calls'])==(5 if action=='1' else 4)
    saved=report(tmp_path)
    assert saved['status']=='complete'
    assert saved['approvalsSha256']==canonical_hash(args['approvals'])
    assert saved['approvalReason']==args['approval_reason']
    assert saved['approvalBasis']=='caller-supplied-test-only-fixture'
    assert saved['resultSha256']==canonical_hash(result)
    assert json.loads((tmp_path/'capture/result.json').read_text())==result
    rows=saved['calls'];headers=[i for i,r in enumerate(rows) if r['method']=='eth_getBlockByHash']
    for chain,client in args['rpcs'].items():
        ids=[i for i,r in enumerate(rows) if r['chain']==chain and r['method']=='eth_chainId']
        assert len(ids)==2 and ids[0]<min(headers)<max(headers)<ids[1]
        assert client.checkpoints==['governance-read-before','governance-read-after']
        assert all(p[0]!='latest' for m,p in client.requests if m=='eth_getBlockByNumber')
    calls=[r for r in rows if r['method']=='eth_call']
    assert all(r['chain']=='pbc' and r['params'][1]['requireCanonical'] is True for r in calls)
    assert len(calls)==generations*(5 if action=='1' else 4)


@pytest.mark.parametrize('change', ['owner','signature','fingerprint','profile','ABI','RPC','origin',
    'reason-empty','reason-type','timeout-inf','timeout-nan','timeout-zero','timeout-bool','budget'])
def test_bad_context_and_configuration_refuse_before_output_and_rpc(tmp_path,change):
    args=case();over={}
    if change=='owner':args['expected_owner']='worker'
    elif change=='signature':args['evidence']['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65;fingerprint(args['evidence'])
    elif change=='fingerprint':args['evidence']['evidenceSha256']='00'*32
    elif change=='profile':args['manifest']['profileEnum']='2'
    elif change=='ABI':args['abi_paths']={}
    elif change=='RPC':args['rpcs'].pop('dbc')
    elif change=='origin':args['rpcs']['pbc'].url='http://127.0.0.1:19999'
    elif change=='reason-empty':args['approval_reason']='  '
    elif change=='reason-type':args['approval_reason']=None
    elif change=='timeout-inf':over['timeout']=float('inf')
    elif change=='timeout-nan':over['timeout']=float('nan')
    elif change=='timeout-zero':over['timeout']=0
    elif change=='timeout-bool':over['timeout']=True
    else:over['max_calls']=True
    with pytest.raises(BAD):collect(tmp_path,args,**over)
    assert not (tmp_path/'capture').exists()
    assert all(not c.requests for c in args['rpcs'].values())


@pytest.mark.parametrize('chain',['pbc','dbc'])
@pytest.mark.parametrize('field',['chainId','genesis','deploy','anchor'])
@pytest.mark.parametrize('when',[1,2])
def test_both_endpoint_identities_bracket_capture(tmp_path,chain,field,when):
    args=case();client=args['rpcs'][chain];hits=0
    target={'genesis':'0x0','deploy':hex(int(client.pin['deployBlock'])),
            'anchor':hex(int(client.observed['anchor']['number']))}.get(field)
    def change(m,p,r):
        nonlocal hits
        selected=m=='eth_chainId' if field=='chainId' else m=='eth_getBlockByNumber' and p[0]==target
        if selected:
            hits+=1
            if hits==when:return '0x999' if field=='chainId' else r|{'hash':'0x'+'ef'*32}
        return r
    client.rewrite=change
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed' and not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('where',range(3))
def test_old_and_live_getter_results_are_checked(tmp_path,where):
    args=case(3,2);client=args['rpcs']['pbc']
    at=list(client.headers)[where]
    data=next(iter(client.answers))[2]
    client.rewrite=lambda m,p,r:'0x'+encode(['uint64'],[999]).hex() if m=='eth_call' and p[1]['blockHash']==at and p[0]['data']==data else r
    with pytest.raises(ValueError,match='nonce'):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed' and not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('change',['missing','wrong','extra','malformed-unused'])
def test_separate_caller_approval_is_checked(tmp_path,change):
    args=case()
    if change=='missing':args['approvals']=[]
    elif change=='wrong':args['approvals'][0]['admins']=[]
    elif change=='extra':args['approvals'][0]['approved']=True
    else:args['approvals'].append(dict(action='4',root='0x'+'99'*20,admins=[]))
    with pytest.raises(BAD):collect(tmp_path,args)
    assert not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('method',['eth_chainId','eth_getBlockByNumber','eth_getBlockByHash','eth_call'])
def test_transport_failure_keeps_partial_transcript_without_fallback(tmp_path,method):
    args=case()
    def fail(m,p,r):
        if m==method:raise RuntimeError('synthetic RPC refusal')
        return r
    for c in args['rpcs'].values():c.rewrite=fail
    with pytest.raises(RuntimeError):collect(tmp_path,args)
    saved=report(tmp_path)
    assert saved['status']=='failed' and saved['calls'][-1]['status']=='failed'
    assert saved['calls'][-1]['method']==method and not (tmp_path/'capture/result.json').exists()
    if method=='eth_call':
        calls=[r for r in saved['calls'] if r['method']=='eth_call']
        assert len(calls)==1 and set(calls[0]['params'][1])=={'blockHash','requireCanonical'}


@pytest.mark.parametrize('change',['manifest','observations','evidence','approvals','ABI','RPC-inventory','ABI-paths'])
def test_mutated_capture_inputs_refuse(tmp_path,change):
    args=case();changed=False
    if change=='ABI':
        path=tmp_path/'Governance.json';path.write_bytes(args['abi_paths']['Governance'].read_bytes());args['abi_paths']['Governance']=path
    def mutate(m,p,r):
        nonlocal changed
        if not changed:
            changed=True
            if change=='manifest':args['manifest']['mutantNote']='changed'
            elif change=='observations':args['observations']['pbc']['genesisHash']='0x'+'ef'*32
            elif change=='evidence':args['evidence']['marker']['schema']='1'
            elif change=='approvals':args['approvals'].clear()
            elif change=='ABI':args['abi_paths']['Governance'].write_text('[]')
            elif change=='ABI-paths':args['abi_paths'].clear()
            else:args['rpcs']['dbc']=args['rpcs']['pbc']
        return r
    args['rpcs']['pbc'].rewrite=mutate
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed' and not (tmp_path/'capture/result.json').exists()


@pytest.mark.parametrize('field',['number','hash','timestamp','null','quantity'])
def test_malformed_or_wrong_raw_headers_refuse(tmp_path,field):
    args=case()
    def corrupt(m,p,r):
        if m!='eth_getBlockByHash':return r
        if field=='null':return None
        if field=='quantity':return r|{'number':'0x00'}
        return r|{field:'0x'+'ef'*32 if field=='hash' else hex(int(r[field],16)+1)}
    args['rpcs']['pbc'].rewrite=corrupt
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed' and not (tmp_path/'capture/result.json').exists()


def test_safe_capture_requires_canonical_hash(tmp_path):
    args=case();rpc=args['rpcs']['pbc']
    rpc.rewrite=lambda m,p,r:r|{'hash':'0x'+'ef'*32} if m=='eth_getBlockByNumber' and p[0] not in rpc.identities else r
    with pytest.raises(ValueError,match='canonical'):collect(tmp_path,args)


@pytest.mark.parametrize('clear',[False,True])
def test_faulted_forks_do_not_collapse_or_gain_safe_label(tmp_path,clear):
    h=history(1,2);signed=h['evidence']['conflicts'][-1]['digests'][1];cap=h['captures'][1]
    other='0x'+'ef'*32;signed['observation']['blockHash']=other;cap['blocks'][0]['raw']['hash']=other
    for call in cap['calls']:call['blockHash']=other
    e=h['evidence'];f=fault(e)
    if clear:e['faultLog']=[dict(seq='1',fault=f,clearedAgainst=f['previous'].copy(),note='synthetic')]
    else:e['faulted']=f
    fingerprint(e)
    result=collect(tmp_path,case(args=h))
    assert result['verification']['declaredSafeLedgerInterval'] is False
    assert len(result['captures'])==2
    assert len({p['pbcObservation']['blockHash'] for p in result['provenance']})==2
    assert all(r['params'][1]['requireCanonical'] is False for r in report(tmp_path)['calls'] if r['method']=='eth_call')


def test_empty_subset_still_verifies_other_signatures_and_both_endpoints(tmp_path):
    args=case();args['evidence']['conflicts'].pop();fingerprint(args['evidence'])
    result=collect(tmp_path,args)
    assert result['captures']==[] and result['provenance']==[]
    assert result['verification']['governanceStateSignaturesChecked']==0
    assert result['verification']['signaturesChecked']==3
    assert all(sum(m=='eth_chainId' for m,p in c.requests)==2 for c in args['rpcs'].values())


def test_budget_and_deadline_keep_failure(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='budget'):collect(tmp_path,case(),max_calls=1)
    assert len(report(tmp_path)['calls'])==1 and report(tmp_path)['status']=='failed'
    mod=importlib.import_module('evaluation.governance_rpc_v2');ticks=iter([0,0,0,2,2,2,2])
    monkeypatch.setattr(mod.time,'monotonic',lambda:next(ticks))
    other=tmp_path/'timeout';other.mkdir()
    with pytest.raises(TimeoutError):collect(other,case(),timeout=1)
    assert report(other)['status']=='failed'


def test_existing_output_is_preserved(tmp_path):
    (tmp_path/'capture').mkdir();(tmp_path/'capture/retained').write_text('original')
    with pytest.raises(FileExistsError):collect(tmp_path,case())
    assert (tmp_path/'capture/retained').read_text()=='original'


def test_block_changes_after_state_reads_refuse(tmp_path):
    args=case();rpc=args['rpcs']['pbc'];hits=0
    def alter(m,p,r):
        nonlocal hits
        if m=='eth_getBlockByHash':
            hits+=1
            if hits==2:
                r['timestamp']=hex(int(r['timestamp'],16)+1);rpc.headers[p[0]]=copy.deepcopy(r)
        return r
    rpc.rewrite=alter
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert report(tmp_path)['status']=='failed'


@pytest.mark.parametrize('field',['blockNumber','timestamp'])
def test_contradictory_observations_refuse_before_io(tmp_path,field):
    h=conflict('header');h['evidence']['conflicts'][-1]['digests'][1]['observation'][field]='999'
    fingerprint(h['evidence']);args=case(args=h)
    with pytest.raises(ValueError):collect(tmp_path,args)
    assert not (tmp_path/'capture').exists() and all(not c.requests for c in args['rpcs'].values())


def test_cross_chain_replacement_is_not_hidden(tmp_path):
    args=case()
    def alter(m,p,r):
        args['rpcs']['pbc'].identities['0x0']['hash']='0x'+'ef'*32
        return r
    args['rpcs']['dbc'].rewrite=alter
    with pytest.raises(ValueError,match='identity'):collect(tmp_path,args)


def test_transport_argument_mutation_cannot_rewrite_receipt(tmp_path):
    args=case()
    def mutate(m,p,r):
        if m=='eth_call':p[1]['blockHash']='0x'+'ef'*32
        return r
    args['rpcs']['pbc'].rewrite=mutate
    result=collect(tmp_path,args)
    row=next(r for r in report(tmp_path)['calls'] if r['method']=='eth_call')
    assert row['params'][1]['blockHash']==result['provenance'][0]['pbcObservation']['blockHash']


@pytest.mark.parametrize('bit,name,kind',[(1,'StateCheckpoint','overtaken-checkpoint'),(5,'GrantReceipt','executed-receipt')])
def test_deliberate_death_scope_exclusions_are_retained(tmp_path,bit,name,kind):
    from evaluation.binding_context_v2 import reconstruct
    from evaluation.schema_v2 import _binding_digest
    from evaluation.tests.test_witness_history_v2 import supersede
    args=case();m,o,e=(args[k] for k in ('manifest','observations','evidence'))
    m['mutations']=str(1<<bit)
    for chain in o.values():
        for views in chain['views'].values():
            if 'mutations' in views:views['mutations']['value']=m['mutations']
    doc=reconstruct(m,o,compiled_max_admins='8')
    e['binding']=dict(document=doc,binding_v2=_binding_digest(doc));e['marker']['binding_v2']=e['binding']['binding_v2']
    supersede(m,e,name,kind=kind)
    assert collect(tmp_path,args)['verification']['excludedDeathSeqs']==['1']
