"""Synthetic native receipt/body mutations; no live chain evidence."""
import importlib
import json
from pathlib import Path

import pytest

from evaluation.evm import AbiContract

ROOT=Path(__file__).resolve().parents[2]
ABI=ROOT/'evaluation/fixtures/e1/abi'
TX='0x'+'99'*32
BLOCK='0x'+'88'*32
ADDRESS='0x'+'33'*20
GID='0x'+'11'*20
REQUEST='0x'+'bb'*32
GRANT='0x'+'aa'*32
DATA='0x'+'44'*32
ZERO='0x'+'00'*32


def word(n): return f'{n:064x}'


def contract(role):
    pins=json.loads((ABI/'PROVENANCE.json').read_text())['files']
    return AbiContract(ABI/(role+'.json'),ADDRESS,pins[role]['sha256'])


def packet(role='KSSC'):
    topic='0x05227b04f749c38d58a5b2fb3e53db12197f13fad4723d789bb040abe60dab58'
    log={'address':ADDRESS,'removed':False,'topics':[topic,GRANT,REQUEST,'0x'+'00'*12+GID[2:]],
         'data':'0x'+DATA[2:]+word(0)+word(2000000000)+ZERO[2:]+word(1)+word(7),
         'blockNumber':'0x5','blockHash':BLOCK,'transactionHash':TX,'transactionIndex':'0x0','logIndex':'0x0'}
    return {'receipt':{'status':'0x1','transactionHash':TX,'blockHash':BLOCK,'blockNumber':'0x5',
                       'transactionIndex':'0x0','gasUsed':'0x1234','logs':[log]},
            'transaction':{'hash':TX,'chainId':'0x7a6a','blockHash':BLOCK,'blockNumber':'0x5','transactionIndex':'0x0'},
            'block':{'hash':BLOCK,'number':'0x5','timestamp':'0x65','transactions':[TX]},'chain_id':'31338'}


def native(p=None):
    try:module=importlib.import_module('evaluation.native')
    except ModuleNotFoundError:pytest.fail('C-E1 native receipt collector is not implemented')
    return module.NativeReceipt(**(p or packet()))


def test_grant_uses_native_zero_recipient_and_verified_dbc_chain():
    n=native();events=n.normalized(contract('KSSC'),'KSSC')
    assert events==[{'type':'DBC_AUTHORIZED','requestDigest':REQUEST,'timestamp':'101','grantId':GRANT,
                    'gid':GID,'dataId':DATA,'kssc':ADDRESS,'destinationChainId':'31338',
                    'recipientKeyHash':ZERO,'keyEpoch':'0'}]
    assert n.gas_used=='4660' and n.block_number=='5'


@pytest.mark.parametrize('part,key,value', [
 ('receipt','transactionHash','0x'+'01'*32),('receipt','blockHash','0x'+'01'*32),
 ('receipt','blockNumber','0x6'),('receipt','transactionIndex','0x1'),
 ('transaction','chainId','0x7a69'),('transaction','blockHash','0x'+'01'*32),
 ('transaction','blockNumber','0x6'),('transaction','transactionIndex','0x1'),
 ('block','transactions',[]),('block','timestamp','0x065'),('receipt','status','0x2')])
def test_identity_or_noncanonical_quantity_mismatch_cannot_be_evidence(part,key,value):
    p=packet();p[part][key]=value
    with pytest.raises(ValueError):native(p)


@pytest.mark.parametrize('key,value', [('blockHash','0x'+'01'*32),('blockNumber','0x6'),
 ('transactionHash','0x'+'01'*32),('transactionIndex','0x1'),('removed',True)])
def test_every_native_log_is_bound_to_the_receipt(key,value):
    p=packet();p['receipt']['logs'][0][key]=value
    with pytest.raises(ValueError):native(p)


def test_duplicate_native_log_index_cannot_double_count_a_grant():
    p=packet();p['receipt']['logs']*=2
    with pytest.raises(ValueError):native(p)


def test_reverted_transaction_retains_gas_and_cannot_have_native_success_events():
    p=packet();p['receipt']['status']='0x0'
    with pytest.raises(ValueError):native(p)
    p['receipt']['logs']=[];n=native(p)
    assert n.success is False and n.gas_used=='4660'
    assert n.normalized(contract('KSSC'),'KSSC')==[]


def test_outcome_gid_data_are_joined_from_bound_psc_view_not_relay_fields():
    c=contract('PSC')
    from eth_utils import keccak
    topic='0x'+keccak(text='OutcomeRecorded(bytes32,bytes32,bytes32,uint256)').hex()
    p=packet();log=p['receipt']['logs'][0];log['topics']=[topic,REQUEST,GRANT];log['data']='0x'+ZERO[2:]+word(9)
    # PSC getRequest is a static ten-field tuple. These are native return words.
    result='0x'+word(2)+'00'*12+GID[2:]+DATA[2:]+word(31339)+'00'*12+ADDRESS[2:]+ZERO[2:]+word(100)+word(2000000000)+word(1)+word(9)
    view={'chainId':'31338','blockHash':BLOCK,'blockNumber':'5','address':ADDRESS,
          'calldata':c.calldata('getRequest',REQUEST),'returnData':result}
    n=native(p)
    with pytest.raises(ValueError,match='view'):n.normalized(c,'PSC')
    events=n.normalized(c,'PSC',view_reader=lambda *args:view)
    assert events==[{'type':'OUTCOME_RECORDED','requestDigest':REQUEST,'timestamp':'101',
                    'grantId':GRANT,'gid':GID,'dataId':DATA}]
    for key,value in [('blockHash','0x'+'00'*32),('calldata',c.calldata('getRequest',ZERO)),('chainId','1')]:
        altered={**view,key:value}
        with pytest.raises(ValueError):n.normalized(c,'PSC',view_reader=lambda *args:altered)


def test_request_log_timestamp_is_checked_against_lsc_getlog():
    from eth_abi import encode
    from eth_utils import keccak
    c=contract('LSC');p=packet();log=p['receipt']['logs'][0]
    log['topics']=['0x'+keccak(text='LogRecorded(uint256,uint8,bytes32,bytes32,bytes)').hex(),'0x'+word(3),'0x'+word(3),REQUEST]
    log['data']='0x'+encode(['bytes32','bytes'],[bytes(32),b'']).hex()
    result='0x'+encode(['(uint8,bytes32,bytes32,uint64,uint64)','bytes'],[(3,bytes.fromhex(REQUEST[2:]),bytes(32),5,101),b'']).hex()
    view={'chainId':'31338','blockHash':BLOCK,'blockNumber':'5','address':ADDRESS,
          'calldata':c.calldata('getLog','3'),'returnData':result}
    n=native(p)
    assert n.normalized(c,'LSC',view_reader=lambda *args:view)==[{'type':'REQUEST_LOGGED','requestDigest':REQUEST,'timestamp':'101'}]
    bad='0x'+encode(['(uint8,bytes32,bytes32,uint64,uint64)','bytes'],[(3,bytes.fromhex(REQUEST[2:]),bytes(32),5,999),b'']).hex()
    with pytest.raises(ValueError):n.normalized(c,'LSC',view_reader=lambda *args:{**view,'returnData':bad})
