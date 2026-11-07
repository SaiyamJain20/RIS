"""Synthetic raw source-state/window checks with independently signed messages.

No RPC/node or actual sign-time attestation. Valid signatures alone are insufficient.
"""
import copy
import importlib

from eth_abi import encode
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.tests.test_signing_context_v2 import case, message, sign


def setup(q='3', current=True, same_head=False):
    m, o, paths = case(q=q)
    value = message(m, 'StateCheckpoint')
    value.update(sequence='8' if current else '1', sourceBlockNumber='100',
                 sourceBlockHash='0x'+'ab'*32, authEpoch='11', policyVersion='3',
                 keyEpoch='0', expiresAt='1030')
    def ob(chain, n, h, ts):
        return dict(chainId=m['chains'][chain]['chainId'], blockNumber=str(n),
                    blockHash='0x'+h*32, timestamp=str(ts))
    source = ob('pbc', 100, 'ab', 990)
    head = source.copy() if same_head else ob('pbc', 101, 'ac', 995)
    target = ob('dbc', 20, 'de', 1000)
    blocks = [dict(chainId=r['chainId'], raw=dict(number=hex(int(r['blockNumber'])),
                    hash=r['blockHash'], timestamp=hex(int(r['timestamp']))))
              for r in ([source,target] if same_head else [source,head,target])]
    calls = []
    def call(chain, at, name, getter, types, values):
        calls.append(dict(chainId=m['chains'][chain]['chainId'], blockHash=at['blockHash'],
            to=m['chains'][chain]['contracts'][name], data='0x'+keccak(text=getter+'()')[:4].hex(),
            result='0x'+encode(types,values).hex()))
    for at in ([source] if same_head else [source,head]):
        call('pbc', at, 'TMSC', 'authEpoch', ['uint64'], [11])
        call('pbc', at, 'PSC', 'policyVersion', ['uint64'], [3])
    call('pbc', source, 'PSC', 'witnessSetVersion', ['uint64'], [int(value['witnessSetVersion'])])
    old = [7,11,3,0,int(value['witnessSetVersion']), int(value['sourceChainId']),value['psc'],99,bytes.fromhex('aa'*32),1020]
    call('dbc',target,'KSSC','currentCheckpoint',
         ['bool','(uint64,uint64,uint64,uint64,uint64,uint256,address,uint256,bytes32,uint64)'],[current,old])
    call('dbc',target,'KSSC','maxCheckpointTtl',['uint64'],[60])
    return dict(message=value, manifest=m, observations=o, abi_paths=paths,
                pbc_head=head, dbc_observation=target, blocks=blocks, calls=calls,
                owner=m['fixture']['witnessSet']['witnesses'][0], compiled_max_admins='8')


def check(args, **over):
    args = args | over
    signature = sign(args['manifest'],'StateCheckpoint',args['message'],signers=[args['owner']])[0]
    return importlib.import_module('evaluation.checkpoint_state_v2').verify_checkpoint_signature(signature=signature, **args)


def raw_call(args, getter, at=None):
    selector='0x'+keccak(text=getter+'()')[:4].hex()
    return next(r for r in args['calls'] if r['data']==selector and (at is None or r['blockHash']==at))


@pytest.mark.parametrize('q,current,same', [('3',True,False),('2',True,False),('3',False,False),('3',True,True)])
def test_valid_checkpoint_signature_joins_exact_state_without_mutation(q,current,same):
    args=setup(q,current,same); before=copy.deepcopy(args)
    result=check(args)
    assert result['sourceStateChecked'] is True and result['suppliedWindowChecked'] is True
    assert result['callsChecked']==len(args['calls']) and result['blocksChecked']==len(args['blocks'])
    assert result['owner']==args['owner'] and args==before


@pytest.mark.parametrize('expiry,valid', [('1000',False),('999',False),('1001',True),('1060',True),('1061',False)])
def test_exact_target_window_boundaries(expiry,valid):
    args=setup();args['message']['expiresAt']=expiry
    if valid: assert check(args)['suppliedWindowChecked']
    else:
        with pytest.raises(ValueError,match='expiry'): check(args)


@pytest.mark.parametrize('getter,where,value', [('authEpoch','source',12),('policyVersion','source',4),
    ('witnessSetVersion','source',9),('authEpoch','head',12),('policyVersion','head',4)])
def test_valid_signature_does_not_make_wrong_or_stale_state_true(getter,where,value):
    args=setup(); h=args['message']['sourceBlockHash'] if where=='source' else args['pbc_head']['blockHash']
    raw_call(args,getter,h)['result']='0x'+encode(['uint64'],[value]).hex()
    with pytest.raises(ValueError,match='state|freshness'): check(args)


@pytest.mark.parametrize('sequence', ['0','7','9',str(2**64-1)])
def test_valid_signature_cannot_skip_or_repeat_current_sequence(sequence):
    args=setup();args['message']['sequence']=sequence
    with pytest.raises(ValueError,match='sequence'): check(args)


def test_maximum_successor_is_representable_but_saturated_current_has_no_successor():
    args=setup(); args['message']['sequence']=str(2**64-1)
    row=raw_call(args,'currentCheckpoint')
    from eth_abi import decode
    types=['bool','(uint64,uint64,uint64,uint64,uint64,uint256,address,uint256,bytes32,uint64)']
    exists,old=decode(types,bytes.fromhex(row['result'][2:])); old=list(old);old[0]=2**64-2
    row['result']='0x'+encode(types,[exists,old]).hex()
    assert check(args)['sourceStateChecked']
    old[0]=2**64-1;row['result']='0x'+encode(types,[exists,old]).hex()
    with pytest.raises(ValueError,match='sequence'):check(args)


@pytest.mark.parametrize('change', ['future','same-height-fork','regressed-source','key-epoch','ttl-zero','ttl-too-small'])
def test_signed_but_invalid_checkpoint_rejected(change):
    args=setup()
    if change=='future': args['pbc_head']['blockNumber']='99'; args['blocks'][1]['raw']['number']='0x63'
    if change=='same-height-fork': args['pbc_head']['blockNumber']='100'; args['blocks'][1]['raw']['number']='0x64'
    if change=='regressed-source':
        from eth_abi import decode
        types=['bool','(uint64,uint64,uint64,uint64,uint64,uint256,address,uint256,bytes32,uint64)']
        row=raw_call(args,'currentCheckpoint');exists,old=decode(types,bytes.fromhex(row['result'][2:]));old=list(old);old[7]=101
        row['result']='0x'+encode(types,[exists,old]).hex()
    if change=='key-epoch':args['message']['keyEpoch']='1'
    if change.startswith('ttl-'):raw_call(args,'maxCheckpointTtl')['result']='0x'+encode(['uint64'],[0 if change=='ttl-zero' else 29]).hex()
    with pytest.raises((ValueError, ValidationError)):check(args)


@pytest.mark.parametrize('change', ['chain','block','to','data','missing','duplicate','unused','trailing','malformed'])
def test_call_selection_and_complete_canonical_bytes(change):
    args=setup(); row=args['calls'][0]
    if change=='chain':row['chainId']=args['manifest']['chains']['dbc']['chainId']
    if change=='block':row['blockHash']='0x'+'ef'*32
    if change=='to':row['to']=args['manifest']['chains']['pbc']['contracts']['PSC']
    if change=='data':row['data']='0x12345678'
    if change=='missing':args['calls'].pop(0)
    if change=='duplicate':args['calls'].append(row.copy())
    if change=='unused':args['calls'].append(row|{'data':'0x12345678'})
    if change=='trailing':row['result']+='00'*32
    if change=='malformed':row['result']='0x00'
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change', ['number','hash','timestamp','chain','duplicate','unused','missing','quantity'])
def test_raw_block_and_selected_observation_join(change):
    args=setup(); row=args['blocks'][1]
    if change=='number':row['raw']['number']='0x66'
    if change=='hash':row['raw']['hash']='0x'+'ef'*32
    if change=='timestamp':row['raw']['timestamp']='0x1'
    if change=='chain':row['chainId']=args['manifest']['chains']['dbc']['chainId']
    if change=='duplicate':args['blocks'].append(copy.deepcopy(row))
    if change=='unused':args['blocks'].append(dict(chainId=row['chainId'],raw=dict(row['raw'],hash='0x'+'ef'*32)))
    if change=='missing':args['blocks'].pop(1)
    if change=='quantity':row['raw']['number']='0x065'
    with pytest.raises(ValueError):check(args)


def test_target_observation_on_wrong_chain_refuses():
    args=setup();args['dbc_observation']['chainId']=args['manifest']['chains']['pbc']['chainId']
    with pytest.raises(ValueError):check(args)


def test_exact_abi_bytes_remain_required(tmp_path):
    args=setup(); path=tmp_path/'TMSC.json';path.write_bytes(args['abi_paths']['TMSC'].read_bytes()+b' ')
    args['abi_paths']=args['abi_paths']|{'TMSC':path}
    with pytest.raises(ValueError,match='ABI hash'):check(args)


@pytest.mark.parametrize('change', ['signature','owner','embedded-chain','embedded-psc','profile','abi-inventory','head-chain'])
def test_caller_selected_context_signature_and_profile_remain_required(change):
    args=setup(); signed=args['message'].copy()
    signature=sign(args['manifest'],'StateCheckpoint',signed,signers=[args['owner']])[0]
    if change=='signature':args['message']['expiresAt']='1031'
    if change=='owner':args['owner']=args['manifest']['fixture']['witnessSet']['witnesses'][1]
    if change=='embedded-chain':args['message']['sourceChainId']='999'
    if change=='embedded-psc':args['message']['psc']='0x'+'99'*20
    if change=='profile':args['manifest']['profileEnum']='2'
    if change=='abi-inventory':args['abi_paths']={}
    if change=='head-chain':args['pbc_head']['chainId']=args['manifest']['chains']['dbc']['chainId']
    with pytest.raises((ValueError, ValidationError)):
        importlib.import_module('evaluation.checkpoint_state_v2').verify_checkpoint_signature(signature=signature,**args)
