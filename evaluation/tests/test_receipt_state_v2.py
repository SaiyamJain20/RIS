"""Synthetic receipt state checks; raw bytes and real signatures, no node."""
import copy
import importlib

from eth_abi import encode
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.evm import AbiContract
from evaluation.tests.test_signing_context_v2 import case, message, sign

BAD = (ValueError, ValidationError)
GRANT_TYPE = '(bool,bool,bytes32,bytes32,address,uint64,uint64,bytes32,uint64)'
REQUEST_TYPE = '(uint8,address,bytes32,uint256,address,bytes32,uint64,uint64,uint256,uint256)'


def setup(q='3', late=True):
    m, o, paths = case(q=q)
    value = message(m, 'GrantReceipt')
    value['grantId'] = '0x'+keccak(encode(['bytes32','address','uint256'],
        [bytes.fromhex(value['requestDigest'][2:]),value['kssc'],int(value['dbcChainId'])])).hex()
    value.update(grantExpiresAt='1030', dbcBlockNumber='12', dbcBlockHash='0x'+'ae'*32)
    def ob(chain,n,h,ts):
        return dict(chainId=m['chains'][chain]['chainId'], blockNumber=str(n),
                    blockHash='0x'+h*32, timestamp=str(ts))
    pbc=ob('pbc',100,'ab',2000 if late else 1000)
    dbc=ob('dbc',20,'de',2001 if late else 1001)
    issued=ob('dbc',12,'ae',900)
    blocks=[dict(chainId=r['chainId'],raw=dict(number=hex(int(r['blockNumber'])),
        hash=r['blockHash'],timestamp=hex(int(r['timestamp'])))) for r in (pbc,dbc,issued)]
    grant=[True,True,bytes.fromhex(value['requestDigest'][2:]),bytes.fromhex(value['dataId'][2:]),
           value['gid'],0,1030,bytes.fromhex('cd'*32),900]
    request=[1,value['gid'],bytes.fromhex(value['dataId'][2:]),int(value['dbcChainId']),
             value['kssc'],bytes.fromhex('ef'*32),800,1050,1,0]
    calls=[]
    for chain,at,name,getter,arg,types,values in (
        ('dbc',dbc,'KSSC','grantDetails',value['grantId'],[GRANT_TYPE],[grant]),
        ('pbc',pbc,'PSC','getRequest',value['requestDigest'],[REQUEST_TYPE],[request])):
        address=m['chains'][chain]['contracts'][name]
        contract=AbiContract(paths[name],address,m['abi'][name]['abiSha256'])
        calls.append(dict(chainId=at['chainId'],blockHash=at['blockHash'],to=address,
            data=contract.calldata(getter,arg),result='0x'+encode(types,values).hex()))
    event='GrantIssued(bytes32,bytes32,address,bytes32,uint64,uint64,bytes32,bool,uint256)'
    log=dict(address=value['kssc'],removed=False,blockNumber='0xc',blockHash=issued['blockHash'],
        topics=['0x'+keccak(text=event).hex(),value['grantId'],value['requestDigest'],
                '0x'+encode(['address'],[value['gid']]).hex()],
        data='0x'+encode(['bytes32','uint64','uint64','bytes32','bool','uint256'],
                        [bytes.fromhex(value['dataId'][2:]),0,1030,bytes.fromhex('cd'*32),True,1]).hex())
    return dict(message=value,manifest=m,observations=o,abi_paths=paths,
        owner=m['fixture']['witnessSet']['witnesses'][0],compiled_max_admins='8',
        pbc_observation=pbc,dbc_observation=dbc,blocks=blocks,calls=calls,logs=[log])


def check(args, signature=None):
    if signature is None:
        signature=sign(args['manifest'],'GrantReceipt',args['message'],signers=[args['owner']])[0]
    return importlib.import_module('evaluation.receipt_state_v2').verify_receipt_signature(signature=signature,**args)


def change_tuple(args, index, field, value):
    from eth_abi import decode
    row=args['calls'][index];kind=GRANT_TYPE if index==0 else REQUEST_TYPE
    data=list(decode([kind],bytes.fromhex(row['result'][2:]))[0]);data[field]=value
    row['result']='0x'+encode([kind],[data]).hex()


@pytest.mark.parametrize('q,late',[('3',False),('3',True),('2',True)])
def test_valid_and_late_reconciliation_preserve_inputs(q,late):
    args=setup(q,late);before=copy.deepcopy(args);result=check(args)
    assert result['sourceStateChecked'] and result['declaredEventChecked']
    assert result['blocksChecked']==3 and result['callsChecked']==2
    assert result['signTimeEstablished'] is False and result['latestHeadEstablished'] is False
    assert result['logCompletenessEstablished'] is False
    assert args==before


@pytest.mark.parametrize('field,value',[(0,False),(1,False),(2,bytes.fromhex('aa'*32)),
    (3,bytes.fromhex('aa'*32)),(4,'0x'+'99'*20),(5,1),(6,1029),(7,bytes.fromhex('aa'*32)),(8,901)])
def test_signed_receipt_cannot_override_grant_state(field,value):
    args=setup();change_tuple(args,0,field,value)
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('field,value',[(0,0),(0,2),(1,'0x'+'99'*20),(2,bytes.fromhex('aa'*32)),
    (3,999),(4,'0x'+'99'*20),(7,1029)])
def test_pending_pbc_request_and_destination_bound_expiry_required(field,value):
    args=setup();change_tuple(args,1,field,value)
    with pytest.raises(ValueError):check(args)


def test_expiry_equal_request_bound_and_event_at_observation_are_valid():
    args=setup();change_tuple(args,1,7,1030)
    args['dbc_observation'].update(blockNumber='12',blockHash=args['message']['dbcBlockHash'],timestamp='900')
    args['calls'][0]['blockHash']=args['message']['dbcBlockHash']
    args['blocks'].pop(1)
    assert check(args)['blocksChecked']==2


@pytest.mark.parametrize('field,value',[('grantId','0x'+'99'*32),('requestDigest','0x'+'99'*32),
    ('gid','0x'+'99'*20),('dataId','0x'+'99'*32),('grantExpiresAt','1031'),
    ('dbcBlockNumber','13'),('dbcBlockHash','0x'+'99'*32)])
def test_even_resigned_wrong_receipt_fields_refuse(field,value):
    args=setup();args['message'][field]=value
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change',['empty','duplicate','non-list','wrong-event','address','removed',
    'block-number','block-hash','grant-id','request-digest','gid','data','trailing','missing-removed'])
def test_unique_declared_native_event_and_full_bytes_required(change):
    args=setup();row=args['logs'][0]
    if change=='empty':args['logs']=[]
    if change=='duplicate':args['logs']*=2
    if change=='non-list':args['logs']={}
    if change=='wrong-event':row['topics'][0]='0x'+'99'*32
    if change=='address':row['address']='0x'+'99'*20
    if change=='removed':row['removed']=True
    if change=='block-number':row['blockNumber']='0xd'
    if change=='block-hash':row['blockHash']='0x'+'99'*32
    if change=='grant-id':row['topics'][1]='0x'+'99'*32
    if change=='request-digest':row['topics'][2]='0x'+'99'*32
    if change=='gid':row['topics'][3]='0x'+encode(['address'],['0x'+'99'*20]).hex()
    if change=='data':row['data']='0x00'
    if change=='trailing':row['data']+='00'*32
    if change=='missing-removed':del row['removed']
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change',['future-event','same-height-fork','time-backwards','observation-chain',
    'missing','duplicate','unused','quantity','number','timestamp','chain','non-list'])
def test_raw_headers_and_supplied_observations_join(change):
    args=setup();row=args['blocks'][2]
    if change=='future-event':args['dbc_observation']['blockNumber']='11';args['blocks'][1]['raw']['number']='0xb'
    if change=='same-height-fork':args['dbc_observation']['blockNumber']='12';args['blocks'][1]['raw']['number']='0xc'
    if change=='time-backwards':args['dbc_observation']['timestamp']='899';args['blocks'][1]['raw']['timestamp']='0x383'
    if change=='observation-chain':args['pbc_observation']['chainId']=args['dbc_observation']['chainId']
    if change=='missing':args['blocks'].pop(2)
    if change=='duplicate':args['blocks'].append(copy.deepcopy(row))
    if change=='unused':args['blocks'].append(dict(chainId=row['chainId'],raw=dict(row['raw'],hash='0x'+'99'*32)))
    if change=='quantity':row['raw']['number']='0x0c'
    if change=='number':row['raw']['number']='0xd'
    if change=='timestamp':row['raw']['timestamp']='0x385'
    if change=='chain':row['chainId']=args['pbc_observation']['chainId']
    if change=='non-list':args['blocks']={}
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change',['chain','block','to','data','missing','duplicate','unused','trailing','malformed','fields','non-list'])
def test_exact_capture_inventory(change):
    args=setup();row=args['calls'][0]
    if change=='chain':row['chainId']=args['pbc_observation']['chainId']
    if change=='block':row['blockHash']='0x'+'99'*32
    if change=='to':row['to']='0x'+'99'*20
    if change=='data':row['data']='0x12345678'
    if change=='missing':args['calls'].pop(0)
    if change=='duplicate':args['calls'].append(row.copy())
    if change=='unused':args['calls'].append(row|{'data':'0x12345678'})
    if change=='trailing':row['result']+='00'*32
    if change=='malformed':row['result']='0x00'
    if change=='fields':row['extra']=True
    if change=='non-list':args['calls']={}
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change',['signature','owner','profile','abi-inventory','context','embedded-chain','embedded-kssc'])
def test_signature_independent_context_and_f_profile_required(change):
    args=setup();signature=sign(args['manifest'],'GrantReceipt',args['message'],signers=[args['owner']])[0]
    if change=='signature':args['message']['grantExpiresAt']='1031'
    if change=='owner':args['owner']=args['manifest']['fixture']['witnessSet']['witnesses'][1]
    if change=='profile':args['manifest']['profileEnum']='2'
    if change=='abi-inventory':args['abi_paths']={}
    if change=='context':args['observations']['pbc']['chainId']='999'
    if change=='embedded-chain':args['message']['dbcChainId']='999'
    if change=='embedded-kssc':args['message']['kssc']='0x'+'99'*20
    with pytest.raises(BAD):check(args,signature)


def test_exact_abi_file_pin_required(tmp_path):
    args=setup();path=tmp_path/'KSSC.json';path.write_bytes(args['abi_paths']['KSSC'].read_bytes()+b' ')
    args['abi_paths']=args['abi_paths']|{'KSSC':path}
    with pytest.raises(ValueError,match='ABI hash'):check(args)
