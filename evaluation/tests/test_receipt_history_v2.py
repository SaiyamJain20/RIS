"""Synthetic declared receipt history; real signatures/raw ABI bytes, no RPC."""
import copy
import importlib

from eth_abi import encode
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.evm import AbiContract
from evaluation.tests.test_certificates_v2 import VECTORS
from evaluation.tests.test_receipt_state_v2 import setup, change_tuple
from evaluation.tests.test_signing_context_v2 import domain, sign
from evaluation.tests.test_witness_history_v2 import fixture, fingerprint, sha, observation

BAD = (ValueError, ValidationError)


def signed_row(args):
    m, msg = args['manifest'], args['message']
    typed = copy.deepcopy(next(v['typedData'] for v in VECTORS if v['name']=='GrantReceipt'))
    chain, contract = domain(m, 'GrantReceipt')
    typed['domain'].update(chainId=chain, verifyingContract=contract)
    typed['message'] = msg
    encoded = encode_typed_data(full_message=typed)
    digest = '0x'+keccak(b'\x19'+encoded.version+encoded.header+encoded.body).hex()
    effect = {k:v for k,v in msg.items() if k!='requestDigest'}
    row = dict(type='GrantReceipt', domainSeparator='0x'+encoded.header.hex(),
        witnessSetVersion=msg['witnessSetVersion'], keyField=msg['requestDigest'],
        effect=effect, vHash=sha(effect), digests=[dict(digest=digest,
            signature=sign(m,'GrantReceipt',msg,signers=[args['owner']])[0],
            observation=copy.deepcopy(args['pbc_observation']))])
    cap = dict(digest=digest, dbcObservation=copy.deepcopy(args['dbc_observation']),
        blocks=copy.deepcopy(args['blocks']), calls=copy.deepcopy(args['calls']),
        logs=copy.deepcopy(args['logs']))
    return row, cap


def history(count=2, q='3'):
    m, o, e = fixture(q=q)
    e['conflicts'] = [r for r in e['conflicts'] if r['type']!='GrantReceipt']
    captures=[]
    for index in range(count):
        args=setup(q=q)
        msg=args['message'];msg['requestDigest']='0x'+f'{index+1:064x}'
        msg['grantId']='0x'+keccak(encode(['bytes32','address','uint256'],
            [bytes.fromhex(msg['requestDigest'][2:]),msg['kssc'],int(msg['dbcChainId'])])).hex()
        change_tuple(args,0,2,bytes.fromhex(msg['requestDigest'][2:]))
        for i,chain,name,getter,arg in (
            (0,'dbc','KSSC','grantDetails',msg['grantId']),
            (1,'pbc','PSC','getRequest',msg['requestDigest'])):
            contract=AbiContract(args['abi_paths'][name],m['chains'][chain]['contracts'][name],
                                 m['abi'][name]['abiSha256'])
            args['calls'][i]['data']=contract.calldata(getter,arg)
        args['logs'][0]['topics'][1:3]=[msg['grantId'],msg['requestDigest']]
        row, cap = signed_row(args);e['conflicts'].append(row);captures.append(cap)
    order=['AccessDecision','StateCheckpoint','GrantReceipt','GovernanceAction']
    e['conflicts'].sort(key=lambda r:(order.index(r['type']),r['keyField']))
    e['observations']=sorted([observation(v['chainId'],200,3000) for v in m['chains'].values()],
                             key=lambda ob:int(ob['chainId']))
    fingerprint(e)
    return dict(evidence=e, manifest=m, observations=o, expected_owner=e['owner'],
                abi_paths=setup(q=q)['abi_paths'], captures=captures, compiled_max_admins='8')


def check(args):
    return importlib.import_module('evaluation.receipt_history_v2').verify_receipt_history(**args)


def relocate(args, cap_index=1, hash_='0x'+'af'*32, number='13'):
    """Synthetic alternative declared grant event, not a safe-ledger transition."""
    row=[r for r in args['evidence']['conflicts'] if r['type']=='GrantReceipt'][cap_index]
    cap=args['captures'][cap_index];old=row['effect']['dbcBlockHash']
    row['effect'].update(dbcBlockHash=hash_,dbcBlockNumber=number)
    for block in cap['blocks']:
        if block['raw']['hash']==old:block['raw'].update(hash=hash_,number=hex(int(number)))
    cap['logs'][0].update(blockHash=hash_,blockNumber=hex(int(number)))
    seed=setup();seed.update(message=row['effect']|{'requestDigest':row['keyField']},
        pbc_observation=row['digests'][0]['observation'], dbc_observation=cap['dbcObservation'],
        blocks=cap['blocks'],calls=cap['calls'],logs=cap['logs'])
    replacement,newcap=signed_row(seed);row.update(replacement);args['captures'][cap_index]=newcap
    fingerprint(args['evidence'])


def fault(args, cleared=False):
    e=args['evidence'];previous=e['observations'][0]
    value=dict(previous=previous.copy(),observed=previous|{'blockNumber':'199'},reason='number-regression')
    if cleared:e['faultLog']=[dict(seq='1',fault=value,clearedAgainst=previous.copy(),note='synthetic')]
    else:e['faulted']=value
    fingerprint(e)


@pytest.mark.parametrize('count,q',[(0,'3'),(1,'3'),(3,'3'),(2,'2')])
def test_all_receipts_and_empty_subset_keep_full_history_checks_and_inputs(count,q):
    args=history(count,q);before=copy.deepcopy(args);result=check(args)
    assert result['receiptStateSignaturesChecked']==count
    assert result['signaturesChecked']==3+count
    assert result['declaredSafeLedgerInterval'] and result['excludedDeathSeqs']==[]
    for key in ('signTimeEstablished','latestHeadEstablished','logCompletenessEstablished',
                'nativeTransitionsEstablished'):
        assert result[key] is False
    assert args==before


@pytest.mark.parametrize('change',['missing','extra','duplicate','wrong-digest','target-override',
    'missing-field','nonobject','nonlist'])
def test_exact_digest_coverage_and_closed_capture_shape(change):
    args=history();cap=args['captures'][0]
    if change=='missing':args['captures'].pop()
    if change=='extra':args['captures'].append(copy.deepcopy(cap)|{'digest':'0x'+'ee'*32})
    if change=='duplicate':args['captures'].append(copy.deepcopy(cap))
    if change=='wrong-digest':cap['digest']='0x'+'ee'*32
    if change=='target-override':cap['pbcObservation']=args['evidence']['observations'][0]
    if change=='missing-field':del cap['logs']
    if change=='nonobject':args['captures'][0]=None
    if change=='nonlist':args['captures']={}
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('index',[0,1,2])
@pytest.mark.parametrize('part',['grant','request','log'])
def test_each_receipt_uses_its_own_raw_state_and_event(index,part):
    args=history(3);cap=args['captures'][index]
    if part=='grant':cap['calls'][0]['result']='0x00'
    if part=='request':cap['calls'][1]['result']='0x00'
    if part=='log':cap['logs'][0]['removed']=True
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change',['pbc-time','pbc-hash','dbc-time','owner','other-signature','fingerprint','profile'])
def test_recorded_target_observation_and_complete_history_context(change):
    args=history();e=args['evidence'];row=next(r for r in e['conflicts'] if r['type']=='GrantReceipt')
    if change=='pbc-time':row['digests'][0]['observation']['timestamp']='2001'
    if change=='pbc-hash':row['digests'][0]['observation']['blockHash']='0x'+'ee'*32
    if change=='dbc-time':args['captures'][0]['dbcObservation']['timestamp']='2002'
    if change=='owner':args['expected_owner']='witness:'+args['manifest']['fixture']['witnessSet']['witnesses'][1]
    if change=='other-signature':e['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65
    if change=='profile':args['manifest']['profileEnum']='2'
    fingerprint(e)
    if change=='fingerprint':e['evidenceSha256']='00'*32
    with pytest.raises(BAD):check(args)


def test_shared_header_facts_refuse_even_when_each_receipt_passes():
    args=history();args['captures'][1]['blocks'][2]['raw']['timestamp']='0x385'
    seed=setup();seed['calls']=args['captures'][1]['calls'];change_tuple(seed,0,8,901)
    # Each grant agrees with its own event header; the shared hash now contradicts.
    with pytest.raises(ValueError,match='conflicting block'):check(args)


def repeated_receipt():
    args=history(1);row=next(r for r in args['evidence']['conflicts'] if r['type']=='GrantReceipt')
    args['evidence']['superseded']=[copy.deepcopy(row)|dict(seq='1',death=dict(
        kind='executed-receipt',observation=row['digests'][0]['observation'].copy()))]
    args['captures'].append(copy.deepcopy(args['captures'][0]))
    # A distinct event block yields a distinct digest, with identical grant fields.
    rows=args['evidence']['conflicts'];index=rows.index(row)
    rows.insert(index,copy.deepcopy(row));relocate(args,1)
    rows.pop(index);fingerprint(args['evidence'])
    return args


@pytest.mark.parametrize('cleared',[False,True])
def test_superseded_receipt_captures_checked_with_explicit_fault_scope(cleared):
    args=repeated_receipt();fault(args,cleared)
    assert check(args)['receiptStateSignaturesChecked']==2
    assert not check(args)['declaredSafeLedgerInterval']
    args['captures'][0]['calls'][0]['result']='0x00'
    with pytest.raises(ValueError):check(args)


def test_safe_interval_refuses_two_canonical_event_locations_for_one_grant():
    with pytest.raises(ValueError,match='conflicting safe grant event'):check(repeated_receipt())


def test_same_height_cross_capture_fork_refuses_safe_but_fault_label_stays_explicit():
    args=history();relocate(args,hash_='0x'+'af'*32,number='12')
    with pytest.raises(ValueError,match='conflicting safe block'):check(args)
    fault(args)
    assert not check(args)['declaredSafeLedgerInterval']


def test_repeated_state_call_conflicts_refuse_even_in_fault_interval():
    args=repeated_receipt();fault(args)
    seed=setup();seed['calls']=args['captures'][1]['calls'];change_tuple(seed,1,7,1049)
    with pytest.raises(ValueError,match='conflicting state call'):check(args)


def test_repeated_event_bytes_conflict_even_in_fault_interval():
    args=repeated_receipt();fault(args)
    # Relocate live event back, then change unsigned event nonce and re-sign a
    # different receipt effect through a new grant expiry. Per-state checks pass.
    row=next(r for r in args['evidence']['conflicts'] if r['type']=='GrantReceipt')
    cap=args['captures'][1]
    old=cap['logs'][0]['blockHash'];new=args['captures'][0]['logs'][0]['blockHash']
    row['effect']['dbcBlockHash']=new;row['effect']['dbcBlockNumber']='12'
    cap['logs'][0].update(blockHash=new,blockNumber='0xc')
    for b in cap['blocks']:
        if b['raw']['hash']==old:b['raw'].update(hash=new,number='0xc')
    row['effect']['grantExpiresAt']='1029'
    seed=setup();seed['calls']=cap['calls'];change_tuple(seed,0,6,1029)
    from eth_abi import decode
    types=['bytes32','uint64','uint64','bytes32','bool','uint256']
    values=list(decode(types,bytes.fromhex(cap['logs'][0]['data'][2:])))
    values[2]=1029;values[-1]=2;cap['logs'][0]['data']='0x'+encode(types,values).hex()
    # Distinct target blocks avoid a state-call contradiction, isolating event bytes.
    cap['dbcObservation'].update(blockNumber='21',blockHash='0x'+'df'*32)
    cap['blocks'][1]['raw'].update(number='0x15',hash='0x'+'df'*32)
    cap['calls'][0]['blockHash']='0x'+'df'*32
    seed=setup();seed.update(message=row['effect']|{'requestDigest':row['keyField']},
        pbc_observation=row['digests'][0]['observation'],dbc_observation=cap['dbcObservation'],
        blocks=cap['blocks'],calls=cap['calls'],logs=cap['logs'])
    newrow,newcap=signed_row(seed);row.update(newrow);args['captures'][1]=newcap;fingerprint(args['evidence'])
    with pytest.raises(ValueError,match='conflicting grant event facts'):check(args)


@pytest.mark.parametrize('bit',[1,5])
def test_mutation_death_exclusions_preserved(bit):
    args=repeated_receipt();fault(args);e=args['evidence'];args['manifest']['mutations']=str(1<<bit)
    from evaluation.binding_context_v2 import reconstruct
    from evaluation.schema_v2 import _binding_digest
    for chain in args['observations'].values():
        for views in chain['views'].values():
            if 'mutations' in views:views['mutations']['value']=str(1<<bit)
    doc=reconstruct(args['manifest'],args['observations'],compiled_max_admins='8')
    e['binding']=dict(document=doc,binding_v2=_binding_digest(doc));e['marker']['binding_v2']=e['binding']['binding_v2']
    if bit==1:
        from evaluation.tests.test_witness_history_v2 import supersede
        supersede(args['manifest'],e,'StateCheckpoint',kind='overtaken-checkpoint')
    fingerprint(e)
    assert check(args)['excludedDeathSeqs']==(['2'] if bit==1 else ['1'])


def test_capture_order_does_not_select_observations():
    args=history(3);args['captures'].reverse()
    assert check(args)['receiptStateSignaturesChecked']==3
