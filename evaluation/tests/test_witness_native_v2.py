"""Raw synthetic RPC bytes, exact owner ABIs and real history signatures.

Breaks caught: ignored block identity/time/chain, death calldata or return facts,
ABI substitution, duplicate/unused captures, lost history/fault/mutant labels.
No owner runtime, RPC, service, actual chain or source-state truth is exercised.
"""
import copy
import importlib
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak
import pytest

from evaluation.tests.test_witness_history_v2 import fixture, supersede, fingerprint, observation
from evaluation.tests.test_signing_context_v2 import message, sign

ABI = Path(__file__).resolve().parents[1] / 'fixtures/f/abi'
DEATHS = [('AccessDecision', 'expiry'), ('StateCheckpoint', 'expiry'),
          ('GovernanceAction', 'expiry'), ('StateCheckpoint', 'overtaken-checkpoint'),
          ('AccessDecision', 'overtaken-decision-sequence'),
          ('GovernanceAction', 'overtaken-governance'),
          ('AccessDecision', 'overtaken-decision-grant'), ('GrantReceipt', 'executed-receipt')]


def captures(m, e):
    blocks = {}

    def add(chain, number, hash_, timestamp):
        key = chain, hash_
        raw = dict(number=hex(int(number)), hash=hash_, timestamp=hex(int(timestamp)))
        assert key not in blocks or blocks[key]['raw'] == raw
        blocks[key] = dict(chainId=chain, raw=raw)

    def ob(v):
        add(v['chainId'], v['blockNumber'], v['blockHash'], v['timestamp'])

    for v in e['observations']: ob(v)
    for row in e['superseded'] + e['conflicts']:
        for d in row['digests']: ob(d['observation'])
        if 'death' in row: ob(row['death']['observation'])
        effect = row['effect']
        if row['type'] in ('AccessDecision', 'StateCheckpoint'):
            add(m['chains']['pbc']['chainId'], effect['sourceBlockNumber'], effect['sourceBlockHash'], 900)
        elif row['type'] == 'GrantReceipt':
            add(m['chains']['dbc']['chainId'], effect['dbcBlockNumber'], effect['dbcBlockHash'], 900)
    faults = ([e['faulted']] if e['faulted'] else []) + [r['fault'] for r in e['faultLog']]
    for v in faults: ob(v['previous']); ob(v['observed'])
    for v in e['faultLog']: ob(v['clearedAgainst'])
    return list(blocks.values()), []


def add_call(m, calls, row):
    d = row['death']; kind = d['kind']; typ = row['type']
    chain = 'dbc' if typ in ('AccessDecision', 'StateCheckpoint') else 'pbc'
    name = 'Governance' if typ == 'GovernanceAction' else 'KSSC' if chain == 'dbc' else 'PSC'
    address = m['chains'][chain]['contracts'][name]
    if kind in ('overtaken-checkpoint', 'overtaken-decision-sequence'):
        signature = 'currentCheckpoint()'; args = b''
        cp = [int(d['observed']), 1, 1, 0, int(m['fixture']['witnessSet']['version']),
              int(m['chains']['pbc']['chainId']), m['chains']['pbc']['contracts']['PSC'], 1, bytes(32), 2000]
        result = encode(['bool', '(uint64,uint64,uint64,uint64,uint64,uint256,address,uint256,bytes32,uint64)'], [True, cp])
    elif kind == 'overtaken-governance':
        signature = 'governanceNonce()'; args = b''
        result = encode(['uint64'], [int(d['observed'])])
    elif kind == 'overtaken-decision-grant':
        signature = 'grantDetails(bytes32)'
        grant = keccak(encode(['bytes32', 'address', 'uint256'], [bytes.fromhex(row['keyField'][2:]), address, int(m['chains']['dbc']['chainId'])]))
        args = encode(['bytes32'], [grant])
        result = encode(['(bool,bool,bytes32,bytes32,address,uint64,uint64,bytes32,uint64)'],
                        [[True, True, bytes.fromhex(row['keyField'][2:]), bytes(32), '0x'+'11'*20, 0, 1000, bytes(32), 1000]])
    elif kind == 'executed-receipt':
        signature = 'getRequest(bytes32)'; args = encode(['bytes32'], [bytes.fromhex(row['keyField'][2:])])
        result = encode(['(uint8,address,bytes32,uint256,address,bytes32,uint64,uint64,uint256,uint256)'],
                        [[2, row['effect']['gid'], bytes.fromhex(row['effect']['dataId'][2:]),
                          int(m['chains']['dbc']['chainId']), m['chains']['dbc']['contracts']['KSSC'], bytes(32), 900, 1100, 1, 2]])
    else: return
    calls.append(dict(chainId=m['chains'][chain]['chainId'], blockHash=d['observation']['blockHash'],
                      to=address, data='0x'+(keccak(text=signature)[:4]+args).hex(), result='0x'+result.hex()))


def setup(name=None, kind='expiry', f=True, q='3'):
    m, o, e = fixture(f, q)
    if name: supersede(m, e, name, kind=kind)
    blocks, calls = captures(m, e)
    for row in e['superseded']: add_call(m, calls, row)
    return m, o, e, blocks, calls


def check(m, o, e, blocks, calls, **over):
    kw = dict(manifest=m, observations=o, expected_owner=e['owner'],
              abi_paths={n: ABI/(n+'.json') for n in m['abi']}, blocks=blocks, calls=calls,
              compiled_max_admins='8' if m['profileEnum'] == '3' else None)
    kw.update(over)
    return importlib.import_module('evaluation.witness_native_v2').verify_native_history(e, **kw)


@pytest.mark.parametrize('name,kind', DEATHS)
def test_each_native_death_kind_and_no_input_mutation(name, kind):
    args = setup(name, kind); original = copy.deepcopy(args)
    result = check(*args)
    assert result['recordsChecked'] == 5 and result['nativeDeathsChecked'] == 1
    assert result['nativeCallsChecked'] == (0 if kind == 'expiry' else 1)
    assert result['declaredSafeLedgerInterval'] is True and result['excludedDeathSeqs'] == []
    assert args == original


@pytest.mark.parametrize('f,q', [(True,'3'), (True,'2'), (False,'1')])
def test_empty_and_live_only_profiles(f,q):
    args = setup(f=f,q=q)
    assert check(*args)['nativeDeathsChecked'] == 0
    m,o,e,_,_ = args
    e['conflicts'] = []; e['observations'] = []; fingerprint(e)
    assert check(m,o,e,[],[])['recordsChecked'] == 0


@pytest.mark.parametrize('part', ['last','signed','death','source','fault','clear'])
@pytest.mark.parametrize('field', ['number','hash','timestamp','chain'])
def test_every_observation_location_is_joined(part,field):
    m,o,e,_,_ = setup('AccessDecision')
    if part == 'fault':
        prev = copy.deepcopy(e['observations'][0]); seen = copy.deepcopy(prev)
        seen['blockNumber'] = str(int(prev['blockNumber'])-1); seen['blockHash'] = '0x'+'ef'*32
        e['faulted'] = dict(reason='number-regression', previous=prev, observed=seen)
        target = seen
    elif part == 'clear':
        prev = copy.deepcopy(e['observations'][0]); seen = copy.deepcopy(prev)
        seen['blockNumber'] = str(int(prev['blockNumber'])-1); seen['blockHash'] = '0x'+'ef'*32
        baseline = observation(prev['chainId'], 5, 950)
        e['faultLog'] = [dict(seq='1', fault=dict(reason='number-regression',previous=prev,observed=seen), clearedAgainst=baseline,note='synthetic')]
        target = baseline
    elif part == 'last': target = e['observations'][0]
    elif part == 'signed': target = e['superseded'][0]['digests'][0]['observation']
    elif part == 'death': target = e['superseded'][0]['death']['observation']
    else: target = None
    fingerprint(e); blocks,calls = captures(m,e)
    if part == 'source':
        effect=e['conflicts'][0]['effect']; chain=m['chains']['pbc']['chainId']; h=effect['sourceBlockHash']
    else: chain=target['chainId']; h=target['blockHash']
    row=next(v for v in blocks if v['chainId']==chain and v['raw']['hash']==h)
    if part=='source' and field=='timestamp':
        # Embedded references carry no time; number/hash are all this API can join.
        row['raw']['timestamp']='0x1'; assert check(m,o,e,blocks,calls)['recordsChecked']==5; return
    if field=='chain': row['chainId']='999'
    elif field=='hash': row['raw']['hash']='0x'+'88'*32
    else: row['raw'][field]=hex(int(row['raw'][field],16)+1)
    with pytest.raises(ValueError): check(m,o,e,blocks,calls)


@pytest.mark.parametrize('change', ['chain','block','to','data','missing','duplicate','unused','trailing','malformed'])
def test_death_requires_exact_raw_call_selection(change):
    m,o,e,b,c=setup('StateCheckpoint','overtaken-checkpoint')
    if change=='chain': c[0]['chainId']=m['chains']['pbc']['chainId']
    if change=='block': c[0]['blockHash']='0x'+'88'*32
    if change=='to': c[0]['to']=m['chains']['dbc']['contracts']['ACSC']
    if change=='data': c[0]['data']='0x12345678'
    if change=='missing': c=[]
    if change=='duplicate': c.append(copy.deepcopy(c[0]))
    if change=='unused': c.append({**c[0],'data':'0x12345678'})
    if change=='trailing': c[0]['result']+='00'*32
    if change=='malformed': c[0]['result']='0x01'
    with pytest.raises(ValueError): check(m,o,e,b,c)


@pytest.mark.parametrize('name,kind', DEATHS[3:])
def test_fabricated_death_is_not_a_ledger_fact(name,kind):
    m,o,e,b,c=setup(name,kind)
    raw=bytearray.fromhex(c[0]['result'][2:])
    if kind=='overtaken-governance': raw[:32]=bytes(32)
    elif kind in ('overtaken-checkpoint','overtaken-decision-sequence'): raw[:32]=bytes(32)
    elif kind=='overtaken-decision-grant': raw[:32]=bytes(32)
    else: raw[:32]=(1).to_bytes(32,'big')
    c[0]['result']='0x'+raw.hex()
    with pytest.raises(ValueError): check(m,o,e,b,c)


@pytest.mark.parametrize('name,kind', DEATHS[3:6])
def test_numeric_death_must_equal_decoded_observed_value(name,kind):
    m,o,e,b,c=setup(name,kind)
    e['superseded'][0]['death']['observed']=str(int(e['superseded'][0]['death']['observed'])+1); fingerprint(e)
    with pytest.raises(ValueError): check(m,o,e,b,c)


@pytest.mark.parametrize('change',['missing','substitute','extra','duplicate-block','unused-block','quantity','raw-field'])
def test_closed_capture_inventories_and_owner_abi_pins(change,tmp_path):
    m,o,e,b,c=setup()
    paths={n:ABI/(n+'.json') for n in m['abi']}
    if change=='missing': paths.pop('PSC')
    if change=='extra': paths['Extra']=paths['PSC']
    if change=='substitute':
        wrong=tmp_path/'PSC.json'; wrong.write_text('[]'); paths['PSC']=wrong
    if change=='duplicate-block': b.append(copy.deepcopy(b[0]))
    if change=='unused-block': b.append(dict(chainId=m['chains']['pbc']['chainId'],raw=dict(number='0x99',hash='0x'+'99'*32,timestamp='0x1')))
    if change=='quantity': b[0]['raw']['number']='0x00'
    if change=='raw-field': b[0]['unexpected']=True
    with pytest.raises(ValueError): check(m,o,e,b,c,abi_paths=paths)


def test_valid_raw_bytes_cannot_hide_a_bad_history_signature():
    m,o,e,b,c=setup()
    e['conflicts'][0]['digests'][0]['signature']=sign(m,'AccessDecision',message(m,'AccessDecision'))[-1]
    fingerprint(e)
    with pytest.raises(ValueError): check(m,o,e,b,c)


@pytest.mark.parametrize('bit,name,kind',[(1,'StateCheckpoint','overtaken-checkpoint'),(1,'AccessDecision','overtaken-decision-sequence'),(5,'GrantReceipt','executed-receipt')])
def test_mutant_deaths_stay_excluded_even_with_matching_raw_facts(bit,name,kind):
    m,o,e,b,c=setup(name,kind)
    m['mutations']=str(1<<bit)
    for chain in o.values():
        for view in chain['views'].values():
            if 'mutations' in view: view['mutations']['value']=m['mutations']
    from evaluation.binding_context_v2 import reconstruct
    from evaluation.schema_v2 import _binding_digest
    doc=reconstruct(m,o,compiled_max_admins='8')
    e['binding']=dict(document=doc,binding_v2=_binding_digest(doc));e['marker']['binding_v2']=_binding_digest(doc);fingerprint(e)
    assert check(m,o,e,b,c)['excludedDeathSeqs']==['1']


@pytest.mark.parametrize('clear',[False,True])
def test_same_height_fork_captures_preserve_fault_and_clear_labels(clear):
    m,o,e,_,_=setup()
    prev=copy.deepcopy(e['observations'][0]); seen=copy.deepcopy(prev)
    seen['blockHash']='0x'+'ef'*32
    fault=dict(reason='hash-changed',previous=prev,observed=seen)
    if clear:
        e['faultLog']=[dict(seq='1',fault=fault,clearedAgainst=copy.deepcopy(prev),note='synthetic clear')]
    else: e['faulted']=fault
    fingerprint(e); b,c=captures(m,e)
    assert check(m,o,e,b,c)['declaredSafeLedgerInterval'] is False


def test_grant_existence_for_another_request_does_not_kill_this_decision():
    m,o,e,b,c=setup('AccessDecision','overtaken-decision-grant')
    raw=bytearray.fromhex(c[0]['result'][2:]);raw[64:96]=bytes.fromhex('99'*32)
    c[0]['result']='0x'+raw.hex()
    with pytest.raises(ValueError,match='grant death fact'): check(m,o,e,b,c)


def test_missing_embedded_receipt_dbc_block_is_refused():
    m,o,e,b,c=setup()
    effect=e['conflicts'][2]['effect']
    b=[v for v in b if not(v['chainId']==m['chains']['dbc']['chainId'] and v['raw']['hash']==effect['dbcBlockHash'])]
    with pytest.raises(ValueError,match='missing raw block'): check(m,o,e,b,c)


def test_multiple_deaths_at_one_block_share_one_exact_call():
    m,o,e,_,_=setup('StateCheckpoint','overtaken-checkpoint')
    supersede(m,e,'AccessDecision',kind='overtaken-decision-sequence')
    e['superseded'][1]['death']['observed']=e['superseded'][0]['death']['observed']
    # The decision's stateSequence is less than this shared observed sequence.
    fingerprint(e); b,c=captures(m,e)
    add_call(m,c,e['superseded'][0])
    result=check(m,o,e,b,c)
    assert result['nativeDeathsChecked']==2 and result['nativeCallsChecked']==1
