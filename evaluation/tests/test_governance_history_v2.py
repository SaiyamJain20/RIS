"""Synthetic declared governance history, supplied state and approval controls."""
import copy
import importlib

from eth_abi import encode
from jsonschema import ValidationError
import pytest

from evaluation.evm import AbiContract
from evaluation.tests.test_governance_state_v2 import setup, raw_call
from evaluation.tests.test_witness_history_v2 import (
    fixture, record, resign, fingerprint, observation, supersede, fault,
)

BAD = (ValueError, ValidationError)


def history(generations=1, refinements=1, action='1', q='3'):
    manifest, observed, evidence = fixture(q=q)
    evidence['conflicts'] = [r for r in evidence['conflicts'] if r['type'] != 'GovernanceAction']
    captures, approvals = [], []
    for gen in range(generations):
        row = record(manifest, 'GovernanceAction', gen % 2)
        row['effect']['action'] = action
        if action == '2': row['effect']['admins'] = []
        row['digests'][0]['expiresAt'] = str(1050+gen*100)
        target = observation(manifest['chains']['pbc']['chainId'], 10+gen*10, 1000+gen*100)
        row['digests'] = [resign(manifest, row)]
        row['digests'][0]['observation'] = target
        for ref in range(1, refinements):
            row['digests'].append(resign(manifest, row, expires=str(1050+gen*100+ref)))
        if gen < generations-1:
            row.update(seq=str(gen+1), death=dict(kind='expiry',
                observation=observation(target['chainId'], 15+gen*10, 1060+gen*100)))
            evidence['superseded'].append(row)
        else: evidence['conflicts'].append(row)
        approvals.append({k:copy.deepcopy(row['effect'][k]) for k in ('action','root','admins')})
        for signed in row['digests']:
            state = setup(action, q=q, current=int(row['keyField'])-1)
            for call in state['calls']:
                call['blockHash'] = target['blockHash']
            for getter in ('isAuthority', 'removedAuthority'):
                if getter == 'removedAuthority' and action != '1': continue
                abi = AbiContract(state['abi_paths']['TMSC'],
                    manifest['chains']['pbc']['contracts']['TMSC'], manifest['abi']['TMSC']['abiSha256'])
                raw_call(state, getter)['data'] = abi.calldata(getter, row['effect']['root'])
            captures.append(dict(digest=signed['digest'], calls=state['calls'], blocks=[dict(
                chainId=target['chainId'], raw=dict(number=hex(int(target['blockNumber'])),
                hash=target['blockHash'], timestamp=hex(int(target['timestamp']))))]))
    evidence['observations'] = sorted([observation(v['chainId'],50,1400)
        for v in manifest['chains'].values()], key=lambda ob:int(ob['chainId']))
    fingerprint(evidence)
    return dict(evidence=evidence, manifest=manifest, observations=observed,
        expected_owner=evidence['owner'], abi_paths=state['abi_paths'], captures=captures,
        approvals=approvals, compiled_max_admins='8')


def check(args):
    return importlib.import_module('evaluation.governance_history_v2').verify_governance_history(**args)


@pytest.mark.parametrize('generations,refinements,action,q', [
    (1,1,'1','3'), (3,2,'1','3'), (1,2,'2','3'), (1,2,'3','3'), (1,1,'1','2')])
def test_all_declared_generations_refinements_and_actions(generations,refinements,action,q):
    args=history(generations,refinements,action,q); before=copy.deepcopy(args)
    result=check(args)
    assert result['governanceStateSignaturesChecked']==generations*refinements
    assert result['signaturesChecked']==3+generations*refinements
    assert result['declaredSafeLedgerInterval'] and result['excludedDeathSeqs']==[]
    assert result['signTimeEstablished'] is False and result['latestHeadEstablished'] is False
    assert result['approvalPolicyEstablished'] is False
    assert args==before


def test_empty_subset_still_checks_other_history_and_does_not_claim_approval_policy():
    args=history();args['evidence']['conflicts'].pop();args['captures']=[];args['approvals']=[]
    fingerprint(args['evidence'])
    assert check(args)['governanceStateSignaturesChecked']==0
    args['evidence']['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65
    fingerprint(args['evidence'])
    with pytest.raises(BAD):check(args)


@pytest.mark.parametrize('change', ['old','refinement','extra','duplicate','wrong-digest',
    'observation-override','missing-field','not-list','nonobject','nonstring-digest'])
def test_closed_capture_inventory_and_exact_digest_coverage(change):
    args=history(3,2);caps=args['captures']
    if change=='old':caps.pop(0)
    if change=='refinement':caps.pop()
    if change=='extra':caps.append(copy.deepcopy(caps[0])|{'digest':'0x'+'ef'*32})
    if change=='duplicate':caps.append(copy.deepcopy(caps[0]))
    if change=='wrong-digest':caps[0]['digest']='0x'+'ef'*32
    if change=='observation-override':caps[0]['pbcObservation']=args['evidence']['observations'][0]
    if change=='missing-field':del caps[0]['calls']
    if change=='not-list':args['captures']={}
    if change=='nonobject':caps[0]=None
    if change=='nonstring-digest':caps[0]['digest']=[]
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('where', range(6))
def test_every_live_and_superseded_digest_checks_raw_state(where):
    args=history(3,2)
    args['captures'][where]['calls'][0]['result']='0x'+encode(['uint64'],[99]).hex()
    with pytest.raises(ValueError,match='nonce'):check(args)


@pytest.mark.parametrize('change', ['none','omit','wrong-admins','extra-field','malformed-unused'])
def test_caller_approvals_remain_separate_and_exact(change):
    args=history(2)
    if change=='none':args['approvals']=None
    if change=='omit':args['approvals'].pop(0)
    if change=='wrong-admins':args['approvals'][0]['admins']=[]
    if change=='extra-field':args['approvals'][0]['approved']=True
    if change=='malformed-unused':args['approvals'].append({'action':'4','root':'0x'+'99'*20,'admins':[]})
    with pytest.raises(BAD):check(args)


def test_duplicate_approvals_and_capture_order_do_not_inflate_counts():
    args=history(3,2);args['captures'].reverse();args['approvals']*=2
    assert check(args)['governanceStateSignaturesChecked']==6


@pytest.mark.parametrize('change', ['time','hash','owner','other-signature','fingerprint','profile'])
def test_export_observation_and_full_history_context_are_required(change):
    args=history();e=args['evidence']
    if change=='time':e['conflicts'][-1]['digests'][0]['observation']['timestamp']='1001'
    if change=='hash':e['conflicts'][-1]['digests'][0]['observation']['blockHash']='0x'+'ee'*32
    if change=='owner':args['expected_owner']='witness:'+args['manifest']['fixture']['witnessSet']['witnesses'][1]
    if change=='other-signature':e['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65
    if change=='profile':args['manifest']['profileEnum']='2'
    fingerprint(e)
    if change=='fingerprint':e['evidenceSha256']='00'*32
    with pytest.raises(BAD):check(args)


def conflict(fact):
    args=history(1,2);cap=args['captures'][1]
    signed=args['evidence']['conflicts'][-1]['digests'][1]
    if fact=='header':
        signed['observation']['timestamp']='1001';cap['blocks'][0]['raw']['timestamp']='0x3e9'
        fingerprint(args['evidence'])
    else:
        call=next(c for c in cap['calls'] if c['data']==
            raw_call(setup(),'maxGovernanceTtl')['data'])
        call['result']='0x'+encode(['uint64'],[119]).hex()
    return args


@pytest.mark.parametrize('fact', ['header','getter'])
def test_contradictory_immutable_facts_refuse_even_when_each_signature_passes(fact):
    args=conflict(fact)
    from evaluation.governance_state_v2 import verify_governance_signature
    row=args['evidence']['conflicts'][-1]
    for signed,cap in zip(row['digests'],args['captures']):
        msg=row['effect']|dict(nonce=row['keyField'],expiresAt=signed['expiresAt'])
        assert verify_governance_signature(msg,signed['signature'],
            owner=args['expected_owner'].removeprefix('witness:'), manifest=args['manifest'],
            observations=args['observations'],abi_paths=args['abi_paths'],
            pbc_observation=signed['observation'],blocks=cap['blocks'],calls=cap['calls'],
            approvals=args['approvals'],compiled_max_admins='8')['sourceStateChecked']
    with pytest.raises(ValueError,match='conflicting'):check(args)


@pytest.mark.parametrize('cleared', [False,True])
def test_fault_or_clear_remains_outside_declared_safe_interval(cleared):
    args=history();e=args['evidence'];f=fault(e)
    if cleared:e['faultLog']=[dict(seq='1',fault=f,clearedAgainst=f['previous'].copy(),note='synthetic')]
    else:e['faulted']=f
    fingerprint(e)
    assert check(args)['declaredSafeLedgerInterval'] is False


@pytest.mark.parametrize('faulted', [False,True])
def test_equal_height_forks_refuse_only_in_safe_interval(faulted):
    args=history(1,2);signed=args['evidence']['conflicts'][-1]['digests'][1];cap=args['captures'][1]
    new='0x'+'ef'*32;signed['observation']['blockHash']=new;cap['blocks'][0]['raw']['hash']=new
    for call in cap['calls']:call['blockHash']=new
    if faulted:args['evidence']['faulted']=fault(args['evidence'])
    fingerprint(args['evidence'])
    if faulted:assert not check(args)['declaredSafeLedgerInterval']
    else:
        with pytest.raises(ValueError,match='conflicting safe'):check(args)


@pytest.mark.parametrize('bit,name,kind', [(1,'StateCheckpoint','overtaken-checkpoint'),
                                        (5,'GrantReceipt','executed-receipt')])
def test_unrelated_mutation_death_exclusions_are_preserved(bit,name,kind):
    args=history();e=args['evidence'];args['manifest']['mutations']=str(1<<bit)
    from evaluation.binding_context_v2 import reconstruct
    from evaluation.schema_v2 import _binding_digest
    for chain in args['observations'].values():
        for views in chain['views'].values():
            if 'mutations' in views:views['mutations']['value']=str(1<<bit)
    doc=reconstruct(args['manifest'],args['observations'],compiled_max_admins='8')
    e['binding']=dict(document=doc,binding_v2=_binding_digest(doc));e['marker']['binding_v2']=e['binding']['binding_v2']
    supersede(args['manifest'],e,name,kind=kind)
    assert check(args)['excludedDeathSeqs']==['1']
