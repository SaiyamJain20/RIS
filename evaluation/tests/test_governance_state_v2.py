"""Synthetic signed governance state/approval controls, no node/sign-time claim."""
import copy
import importlib

from eth_abi import encode
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.evm import AbiContract
from evaluation.tests.test_signing_context_v2 import case, message, sign

BAD = (ValueError, ValidationError)


def setup(action='1', q='3', current=7):
    manifest, observations, paths = case(q=q)
    value = message(manifest, 'GovernanceAction')
    value.update(action=action, nonce=str(current+1), expiresAt='1060')
    if action == '2':
        value['admins'] = []
    ob = dict(chainId=manifest['chains']['pbc']['chainId'], blockNumber='100',
              blockHash='0x'+'ab'*32, timestamp='1000')
    blocks = [dict(chainId=ob['chainId'], raw=dict(number='0x64',
                   hash=ob['blockHash'], timestamp='0x3e8'))]
    calls = []
    def call(name, getter, types, values, *args):
        address = manifest['chains']['pbc']['contracts'][name]
        abi = AbiContract(paths[name], address, manifest['abi'][name]['abiSha256'])
        calls.append(dict(chainId=ob['chainId'], blockHash=ob['blockHash'],
            to=address, data=abi.calldata(getter, *args), result='0x'+encode(types, values).hex()))
    call('Governance', 'governanceNonce', ['uint64'], [current])
    call('Governance', 'witnessSetVersion', ['uint64'], [int(value['witnessSetVersion'])])
    call('Governance', 'maxGovernanceTtl', ['uint64'], [120])
    call('TMSC', 'isAuthority', ['bool'], [action != '1'], value['root'])
    if action == '1':
        call('TMSC', 'removedAuthority', ['bool'], [False], value['root'])
    return dict(message=value, owner=manifest['fixture']['witnessSet']['witnesses'][0],
        manifest=manifest, observations=observations, abi_paths=paths,
        pbc_observation=ob, blocks=blocks, calls=calls,
        approvals=[{k:copy.deepcopy(value[k]) for k in ('action','root','admins')}],
        compiled_max_admins='8')


def check(args, signature=None):
    if signature is None:
        signature = sign(args['manifest'], 'GovernanceAction', args['message'], signers=[args['owner']])[0]
    return importlib.import_module('evaluation.governance_state_v2').verify_governance_signature(
        signature=signature, **args)


def raw_call(args, getter):
    selector = keccak(text=getter+('(address)' if getter in ('isAuthority','removedAuthority') else '()'))[:4]
    return next(row for row in args['calls'] if row['data'].startswith('0x'+selector.hex()))


@pytest.mark.parametrize('action,q', [('1','3'),('2','3'),('3','3'),('1','2')])
def test_valid_actions_match_supplied_state_and_approval_without_mutation(action,q):
    args=setup(action,q); before=copy.deepcopy(args)
    result=check(args)
    assert result['sourceStateChecked'] and result['suppliedWindowChecked']
    assert result['approvalFixtureMatched'] and result['owner']==args['owner']
    assert result['signTimeEstablished'] is False and result['latestHeadEstablished'] is False
    assert result['blocksChecked']==1 and result['callsChecked']==len(args['calls'])
    assert args==before


def test_empty_set_and_duplicate_approval_entries_are_valid():
    args=setup('3'); args['message']['admins']=[]; args['approvals'][0]['admins']=[]
    args['approvals']*=2
    assert check(args)['approvalFixtureMatched']


def test_maximum_admins_and_nonmatching_valid_approvals_preserve_legitimate_action():
    args=setup();args['message']['admins']=['0x'+f'{i:040x}' for i in range(1,9)]
    args['approvals'].append({k:copy.deepcopy(args['message'][k]) for k in ('action','root','admins')})
    assert check(args)['approvalFixtureMatched']


def test_renewal_and_retrospectively_selected_time_do_not_prove_sign_time():
    args=setup();args['message']['expiresAt']='1120'
    assert check(args)['suppliedWindowChecked']
    args['pbc_observation']['timestamp']='1001'
    args['blocks'][0]['raw']['timestamp']='0x3e9'
    # A different supplied observation can also be consistent with these bytes.
    result=check(args)
    assert result['suppliedWindowChecked'] and result['signTimeEstablished'] is False


@pytest.mark.parametrize('expiry,valid', [('999',False),('1000',False),('1001',True),('1120',True),('1121',False)])
def test_expiry_boundaries(expiry,valid):
    args=setup();args['message']['expiresAt']=expiry
    if valid: assert check(args)['suppliedWindowChecked']
    else:
        with pytest.raises(ValueError,match='expiry'):check(args)


@pytest.mark.parametrize('ttl', [0,59,60,61,500])
def test_public_ttl_is_used_instead_of_fixture_default(ttl):
    args=setup(); raw_call(args,'maxGovernanceTtl')['result']='0x'+encode(['uint64'],[ttl]).hex()
    if ttl>=60: assert check(args)['suppliedWindowChecked']
    else:
        with pytest.raises(ValueError,match='expiry'):check(args)


@pytest.mark.parametrize('nonce', ['0','7','9',str(2**64-1)])
def test_signed_nonce_must_be_exact_next(nonce):
    args=setup();args['message']['nonce']=nonce
    with pytest.raises(ValueError,match='nonce'):check(args)


def test_first_and_maximum_nonce_boundaries():
    assert check(setup(current=0))['sourceStateChecked']
    args=setup(current=2**64-2);assert check(args)['sourceStateChecked']
    raw_call(args,'governanceNonce')['result']='0x'+encode(['uint64'],[2**64-1]).hex()
    with pytest.raises(ValueError,match='nonce'):check(args)


@pytest.mark.parametrize('action,getter,value', [('1','isAuthority',True),('1','removedAuthority',True),
                                             ('2','isAuthority',False),('3','isAuthority',False)])
def test_signed_but_doomed_authority_action_refuses(action,getter,value):
    args=setup(action);raw_call(args,getter)['result']='0x'+encode(['bool'],[value]).hex()
    with pytest.raises(ValueError,match='authority|tombstone'):check(args)


def test_signed_version_must_match_raw_governance_state():
    args=setup();raw_call(args,'witnessSetVersion')['result']='0x'+encode(['uint64'],[9]).hex()
    with pytest.raises(ValueError,match='version'):check(args)


@pytest.mark.parametrize('change', ['empty','none','dict','action','root','admins','extra','malformed-unused'])
def test_exact_canonical_caller_approval_is_required(change):
    args=setup()
    if change=='empty':args['approvals']=[]
    if change=='none':args['approvals']=None
    if change=='dict':args['approvals']={}
    if change=='action':args['approvals'][0]['action']='3'
    if change=='root':args['approvals'][0]['root']='0x'+'99'*20
    if change=='admins':args['approvals'][0]['admins']=[]
    if change=='extra':args['approvals'][0]['approved']=True
    if change=='malformed-unused':args['approvals'].append(dict(action='4',root='0x'+'99'*20,admins=[]))
    with pytest.raises(BAD):check(args)


@pytest.mark.parametrize('change', ['action','zero-root','zero-admin','reverse','duplicate','max-admins','remove-admins','empty-add'])
def test_typed_action_rules_remain_required(change):
    args=setup();value=args['message']
    if change=='action':value['action']='4'
    if change=='zero-root':value['root']='0x'+'00'*20
    if change=='zero-admin':value['admins']=['0x'+'00'*20]
    if change=='reverse':value['admins']=['0x'+'22'*20,'0x'+'11'*20]
    if change=='duplicate':value['admins']=['0x'+'11'*20]*2
    if change=='max-admins':value['admins']=['0x'+f'{i:040x}' for i in range(1,10)]
    if change=='remove-admins':value['action']='2'
    if change=='empty-add':value['admins']=[]
    args['approvals']=[{k:copy.deepcopy(value[k]) for k in ('action','root','admins')}]
    with pytest.raises(BAD):check(args)


@pytest.mark.parametrize('change', ['chain','hash','to','data','missing','duplicate','unused','trailing','malformed','fields','non-list'])
def test_exact_canonical_capture_inventory(change):
    args=setup();row=args['calls'][0]
    if change=='chain':row['chainId']=args['manifest']['chains']['dbc']['chainId']
    if change=='hash':row['blockHash']='0x'+'ef'*32
    if change=='to':row['to']=args['manifest']['chains']['pbc']['contracts']['PSC']
    if change=='data':row['data']='0x12345678'
    if change=='missing':args['calls'].pop(0)
    if change=='duplicate':args['calls'].append(row.copy())
    if change=='unused':args['calls'].append(row|{'data':'0x12345678'})
    if change=='trailing':row['result']+='00'*32
    if change=='malformed':row['result']='0x00'
    if change=='fields':row['extra']=True
    if change=='non-list':args['calls']={}
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change', ['number','hash','timestamp','chain','duplicate','unused','missing','quantity','fields','non-list'])
def test_raw_observation_join(change):
    args=setup();row=args['blocks'][0]
    if change=='number':row['raw']['number']='0x65'
    if change=='hash':row['raw']['hash']='0x'+'ef'*32
    if change=='timestamp':row['raw']['timestamp']='0x3e9'
    if change=='chain':row['chainId']=args['manifest']['chains']['dbc']['chainId']
    if change=='duplicate':args['blocks'].append(copy.deepcopy(row))
    if change=='unused':args['blocks'].append(dict(chainId=row['chainId'],raw=dict(row['raw'],hash='0x'+'ef'*32)))
    if change=='missing':args['blocks']=[]
    if change=='quantity':row['raw']['number']='0x064'
    if change=='fields':row['extra']=True
    if change=='non-list':args['blocks']={}
    with pytest.raises(ValueError):check(args)


@pytest.mark.parametrize('change', ['signature','owner','profile','abi-inventory','observation-chain','context'])
def test_independent_context_and_signature_remain_required(change):
    args=setup();signature=sign(args['manifest'],'GovernanceAction',args['message'],signers=[args['owner']])[0]
    if change=='signature':args['message']['expiresAt']='1061'
    if change=='owner':args['owner']=args['manifest']['fixture']['witnessSet']['witnesses'][1]
    if change=='profile':args['manifest']['profileEnum']='2'
    if change=='abi-inventory':args['abi_paths']={}
    if change=='observation-chain':args['pbc_observation']['chainId']=args['manifest']['chains']['dbc']['chainId']
    if change=='context':args['observations']['pbc']['chainId']='999'
    with pytest.raises(BAD):check(args,signature)


def test_exact_abi_bytes_required(tmp_path):
    args=setup();path=tmp_path/'Governance.json';path.write_bytes(args['abi_paths']['Governance'].read_bytes()+b' ')
    args['abi_paths']=args['abi_paths']|{'Governance':path}
    with pytest.raises(ValueError,match='ABI hash'):check(args)
