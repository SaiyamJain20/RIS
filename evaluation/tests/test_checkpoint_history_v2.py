"""Declared checkpoint coverage with synthetic captures and real signatures."""
import copy
import importlib

from eth_abi import decode, encode
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.tests.test_checkpoint_state_v2 import setup
from evaluation.tests.test_signing_context_v2 import sign, domain
from evaluation.tests.test_witness_history_v2 import fixture, fingerprint, sha, observation
from evaluation.tests.test_certificates_v2 import VECTORS

BAD = (ValueError, ValidationError)


def history(generations=1, refinements=1, q='3'):
    m, o, e = fixture(q=q)
    e['conflicts'] = [r for r in e['conflicts'] if r['type'] != 'StateCheckpoint']
    captures = []
    for gen in range(generations):
        args = setup(q=q, same_head=bool(gen % 2))
        msg = args['message']
        if gen % 2:
            msg.update(sourceBlockNumber='101', sourceBlockHash='0x'+'ac'*32)
            args['blocks'][0]['raw'].update(number='0x65', hash=msg['sourceBlockHash'], timestamp='0x3e3')
            args['pbc_head'].update(blockNumber='101', blockHash=msg['sourceBlockHash'], timestamp='995')
            for row in args['calls']:
                if row['chainId'] == m['chains']['pbc']['chainId']:
                    row['blockHash'] = msg['sourceBlockHash']
        target = observation(m['chains']['dbc']['chainId'], 20+gen*10, 1000+gen*100)
        args['blocks'][-1]['raw'].update(number=hex(int(target['blockNumber'])),
            hash=target['blockHash'], timestamp=hex(int(target['timestamp'])))
        for row in args['calls']:
            if row['chainId'] == target['chainId']: row['blockHash'] = target['blockHash']
        effect = {k:v for k,v in msg.items() if k not in ('sequence','expiresAt')}
        record = dict(type='StateCheckpoint', domainSeparator='', witnessSetVersion=msg['witnessSetVersion'],
                      keyField=msg['sequence'], effect=effect, vHash=sha(effect), digests=[])
        for refinement in range(refinements):
            msg['expiresAt'] = str(1030+gen*100+refinement)
            typed = copy.deepcopy(next(v['typedData'] for v in VECTORS if v['name']=='StateCheckpoint'))
            chain, contract = domain(m, 'StateCheckpoint')
            typed['domain'].update(chainId=chain, verifyingContract=contract);typed['message']=msg
            encoded = encode_typed_data(full_message=typed)
            digest = '0x'+keccak(b'\x19'+encoded.version+encoded.header+encoded.body).hex()
            record['domainSeparator'] = '0x'+encoded.header.hex()
            record['digests'].append(dict(digest=digest, signature=sign(m,'StateCheckpoint',msg)[0],
                expiresAt=msg['expiresAt'], observation=target.copy()))
            captures.append(dict(digest=digest, pbcHead=copy.deepcopy(args['pbc_head']),
                                 blocks=copy.deepcopy(args['blocks']), calls=copy.deepcopy(args['calls'])))
        if gen < generations-1:
            record.update(seq=str(gen+1), death=dict(kind='expiry',
                observation=observation(chain, 25+gen*10, 1040+gen*100)))
            e['superseded'].append(record)
        else: e['conflicts'].insert(1, record)
    e['observations'] = sorted([observation(v['chainId'],50,1400) for v in m['chains'].values()],
                               key=lambda ob:int(ob['chainId']))
    fingerprint(e)
    return dict(evidence=e, manifest=m, observations=o, expected_owner=e['owner'],
                abi_paths=args['abi_paths'], captures=captures, compiled_max_admins='8')


def check(args):
    return importlib.import_module('evaluation.checkpoint_history_v2').verify_checkpoint_history(**args)


@pytest.mark.parametrize('generations,refinements,q', [(1,1,'3'),(3,2,'3'),(1,2,'2')])
def test_every_checkpoint_signature_including_recurrence_and_expiry_refinements(generations,refinements,q):
    args=history(generations,refinements,q); before=copy.deepcopy(args)
    result=check(args)
    assert result['checkpointStateSignaturesChecked']==generations*refinements
    assert result['signaturesChecked']==3+generations*refinements
    assert result['declaredSafeLedgerInterval'] and result['excludedDeathSeqs']==[]
    assert args==before


def test_empty_checkpoint_subset_keeps_other_history_checks():
    args=history();args['evidence']['conflicts'].pop(1);args['captures']=[];fingerprint(args['evidence'])
    assert check(args)['checkpointStateSignaturesChecked']==0
    args['evidence']['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65
    fingerprint(args['evidence'])
    with pytest.raises(BAD):check(args)


@pytest.mark.parametrize('change', ['missing-old','missing-refinement','extra','duplicate','wrong-digest',
    'target-override','missing-field','not-list','nonobject'])
def test_exact_capture_coverage_and_closed_capture_fields(change):
    args=history(3,2); captures=args['captures']
    if change=='missing-old':captures.pop(0)
    if change=='missing-refinement':captures.pop()
    if change=='extra':captures.append(copy.deepcopy(captures[0])|{'digest':'0x'+'ef'*32})
    if change=='duplicate':captures.append(copy.deepcopy(captures[0]))
    if change=='wrong-digest':captures[0]['digest']='0x'+'ef'*32
    if change=='target-override':captures[0]['dbcObservation']=args['evidence']['observations'][0]
    if change=='missing-field':del captures[0]['pbcHead']
    if change=='not-list':args['captures']={}
    if change=='nonobject':captures[0]=None
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('where', [0,1,2,3,4,5])
def test_each_live_and_superseded_digest_checks_exact_state(where):
    args=history(3,2)
    args['captures'][where]['calls'][-1]['result']='0x'+encode(['uint64'],[1]).hex()
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change', ['time','hash','owner','other-signature','fingerprint','profile'])
def test_recorded_observation_and_full_history_context_are_required(change):
    args=history(); e=args['evidence']
    if change=='time':e['conflicts'][1]['digests'][0]['observation']['timestamp']='1001'
    if change=='hash':e['conflicts'][1]['digests'][0]['observation']['blockHash']='0x'+'ee'*32
    if change=='owner':args['expected_owner']='witness:'+args['manifest']['fixture']['witnessSet']['witnesses'][1]
    if change=='other-signature':e['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65
    if change=='profile':args['manifest']['profileEnum']='2'
    fingerprint(e)
    if change=='fingerprint':e['evidenceSha256']='00'*32
    with pytest.raises(BAD):check(args)


@pytest.mark.parametrize('fact', ['source-time','source-state','target-current'])
def test_contradictory_reused_raw_facts_refuse_even_if_each_signature_passes(fact):
    args=history(1,2); cap=args['captures'][1]
    if fact=='source-time':cap['blocks'][0]['raw']['timestamp']='0x3dc'
    if fact=='source-state':
        # TTL can vary only with target blocks; at the same key both still satisfy each expiry.
        cap['calls'][-1]['result']='0x'+encode(['uint64'],[59]).hex()
    if fact=='target-current':
        row=cap['calls'][-2]
        types=['bool','(uint64,uint64,uint64,uint64,uint64,uint256,address,uint256,bytes32,uint64)']
        exists,current=decode(types,bytes.fromhex(row['result'][2:]));current=list(current);current[7]=98
        row['result']='0x'+encode(types,[exists,current]).hex()
    with pytest.raises(ValueError,match='conflicting'):check(args)


@pytest.mark.parametrize('cleared', [False,True])
def test_fault_and_clear_labels_never_become_safe(cleared):
    args=history();e=args['evidence'];previous=e['observations'][0]
    fault=dict(previous=previous.copy(), observed=previous|{'blockNumber':'49'}, reason='number-regression')
    if cleared:e['faultLog']=[dict(seq='1',fault=fault,clearedAgainst=previous.copy(),note='synthetic recovery')]
    else:e['faulted']=fault
    fingerprint(e)
    assert check(args)['declaredSafeLedgerInterval'] is False


@pytest.mark.parametrize('bit', [1,5])
def test_mutation_death_exclusions_survive_checkpoint_composition(bit):
    args=history(2);e=args['evidence'];args['manifest']['mutations']=str(1<<bit)
    # The immutable manifest and observed deployment must agree on mutation bits.
    from evaluation.binding_context_v2 import reconstruct
    from evaluation.schema_v2 import _binding_digest
    for chain in args['observations'].values():
        for views in chain['views'].values():
            if 'mutations' in views:views['mutations']['value']=str(1<<bit)
    doc=reconstruct(args['manifest'],args['observations'],compiled_max_admins='8')
    e['binding']=dict(document=doc,binding_v2=_binding_digest(doc));e['marker']['binding_v2']=e['binding']['binding_v2']
    if bit==1:
        e['superseded'][0]['death'].update(kind='overtaken-checkpoint',observed='8')
    else:
        from evaluation.tests.test_witness_history_v2 import supersede
        supersede(args['manifest'],e,'GrantReceipt',kind='executed-receipt')
    fingerprint(e)
    assert check(args)['excludedDeathSeqs']==['1' if bit==1 else '2']


def forked_heads(faulted=False):
    args=history(1,2);cap=args['captures'][1];old=cap['pbcHead']['blockHash'];new='0x'+'ef'*32
    cap['pbcHead']['blockHash']=new
    next(r for r in cap['blocks'] if r['raw']['hash']==old)['raw']['hash']=new
    for row in cap['calls']:
        if row['blockHash']==old:row['blockHash']=new
    if faulted:
        e=args['evidence'];previous=e['observations'][0]
        e['faulted']=dict(previous=previous.copy(),observed=previous|{'blockNumber':'49'},reason='number-regression')
        fingerprint(e)
    return args


def test_same_height_forks_refuse_safe_intervals_and_retain_fault_scope():
    with pytest.raises(ValueError,match='conflicting safe'):check(forked_heads())
    result=check(forked_heads(True))
    assert result['checkpointStateSignaturesChecked']==2 and not result['declaredSafeLedgerInterval']


def test_capture_list_order_has_no_effect_on_exact_digest_selection():
    args=history(3,2);args['captures'].reverse()
    assert check(args)['checkpointStateSignaturesChecked']==6
