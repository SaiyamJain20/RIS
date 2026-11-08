"""Generate synthetic candidate wire/signing vectors. No ledger or peer execution."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from eth_abi import encode

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'interfaces/proposals/v2/vectors'
OUT.mkdir(exist_ok=True)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def h(data):
    return '0x' + keccak(data).hex()


labels = ['witness-' + str(i) for i in range(1, 5)]
keys = {label: keccak(text='hmbc-e0-synthetic-key:' + label) for label in labels}
witnesses = [dict(index=str(i), label=label, address=Account.from_key(keys[label]).address.lower())
             for i, label in enumerate(labels)]
ordered = sorted(witnesses, key=lambda w: w['address'])[:3]
write('witnesses.json', dict(status='SYNTHETIC_PROPOSAL_NOT_DEPLOYED', derivation="keccak256(UTF-8('hmbc-e0-synthetic-key:' || label))",
    witnesses=witnesses, version='2', threshold='3', q2ControlThreshold='2', processIsolationMeasured=False))
old = json.loads((ROOT/'interfaces/v1/vectors/eip712-agent1.json').read_text())
typed = {v['name']: v['typedData'] for v in old['vectors'] if 'typedData' in v}
fields = [('action','uint8'),('root','address'),('admins','address[]'),('nonce','uint64'),('witnessSetVersion','uint64'),('expiresAt','uint64')]
typed['GovernanceAction'] = dict(types={'EIP712Domain':copy.deepcopy(typed['StateCheckpoint']['types']['EIP712Domain']),
    'GovernanceAction':[{'name':n,'type':t} for n,t in fields]}, primaryType='GovernanceAction',
    domain=dict(name='HMBCGovernance',version='1',chainId='18545',verifyingContract='0x'+'77'*20),
    message=dict(action='1',root='0x'+'88'*20,admins=['0x'+'11'*20,'0x'+'22'*20],nonce='1',witnessSetVersion='2',expiresAt='1800000060'))
for name in ['StateCheckpoint','AccessDecision','GrantReceipt']:
    typed[name] = copy.deepcopy(typed[name])
    typed[name]['message']['witnessSetVersion'] = '2'


def signed(name, message=None):
    td = copy.deepcopy(typed[name])
    if message is not None:
        td['message'] = copy.deepcopy(message)
    signable = encode_typed_data(full_message=td)
    signatures = [dict(witnessIndex=w['index'], signer=w['address'],
        signature='0x'+Account.sign_message(signable, keys[w['label']]).signature.hex()) for w in ordered]
    digest = h(b'\x19'+signable.version+signable.header+signable.body)
    return dict(name=name, typedData=td, digest=digest, domainSeparator='0x'+signable.header.hex(),
                structHash='0x'+signable.body.hex(), signatures=signatures)


signing = [signed(n) for n in ['StateCheckpoint','AccessDecision','GrantReceipt','GovernanceAction']]
for action, admins in [('2',[]),('3',[])]:
    msg = copy.deepcopy(typed['GovernanceAction']['message'])
    msg.update(action=action, admins=admins)
    signing.append(signed('GovernanceAction',msg))
# Independent ABI-word encoder checks GovernanceAction; not the author's Solidity.
type_string = 'GovernanceAction(uint8 action,address root,address[] admins,uint64 nonce,uint64 witnessSetVersion,uint64 expiresAt)'
for v in signing:
    if v['name'] != 'GovernanceAction':
        continue
    m = v['typedData']['message']; dom = v['typedData']['domain']
    admins_hash = keccak(b''.join(bytes.fromhex(a[2:]).rjust(32,b'\0') for a in m['admins']))
    body = keccak(encode(['bytes32','uint8','address','bytes32','uint64','uint64','uint64'],
        [keccak(text=type_string),int(m['action']),m['root'],admins_hash,int(m['nonce']),int(m['witnessSetVersion']),int(m['expiresAt'])]))
    header = keccak(encode(['bytes32','bytes32','bytes32','uint256','address'],
        [keccak(text='EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)'),
         keccak(text=dom['name']),keccak(text=dom['version']),int(dom['chainId']),dom['verifyingContract']]))
    assert '0x'+body.hex() == v['structHash'] and '0x'+header.hex() == v['domainSeparator']
    assert h(b'\x19\x01'+header+body) == v['digest']
    v['independentAbiWordEncodingMatches'] = True
    v['typeHash'] = h(type_string.encode())
write('signing.json', dict(status='SYNTHETIC_OFFLINE_VECTOR_NOT_SOLIDITY_MEASUREMENT', vectors=signing))


def outcomes():
    return [dict(witnessIndex=w['index'],witness=w['address'], status='signed' if w in ordered else 'silent',
                 replies='1' if w in ordered else '0') for w in witnesses]


successes = []
for name, operation, field in [('StateCheckpoint','collect_checkpoint','checkpoint'),
    ('AccessDecision','collect_decision','decision'),('GrantReceipt','attest_grant','receipt'),
    ('GovernanceAction','collect_governance','governanceAction')]:
    v = next(v for v in signing if v['name']==name)
    result = dict(schemaVersion='v2', adapterMode='symbolic', **{field:v['typedData']['message']},
        signatures=[s['signature'] for s in v['signatures']],
        collection=dict(quorum='3',witnessSetVersion='2',outcomes=outcomes(),submittedSigners=[w['address'] for w in ordered]))
    if name=='AccessDecision':
        result['credentialRecords'] = next(x for x in old['vectors'] if x['name']=='CredentialRecord[] credentialDigest')['records']
    successes.append(dict(operation=operation,response=dict(schemaVersion='v2',ok=True,result=result,error=None)))
write('success.json',successes)

wire = subprocess.check_output(['git','show','fe03df72a6dadb585451575c20866c57ad7c9d7f:protocol/f0/SUCCESSOR-WIRE.md'],cwd=ROOT).decode()
examples = [json.loads(x) for x in re.findall(r'```json\n(.*?)\n```',wire,re.S)]
for response in examples:
    collection=(response.get('result') or response.get('error')).get('collection')
    if collection:
        for o in collection['outcomes']:
            o['witness'] = witnesses[int(o['witnessIndex'])]['address']
        for key in ['recordedReports','lateReports']:
            for report in collection.get(key,[]):
                td=copy.deepcopy(typed['StateCheckpoint']);td['message']=report['message']
                keybytes=keys[witnesses[int(report['witnessIndex'])]['label']]
                report['signature']='0x'+Account.sign_message(encode_typed_data(full_message=td),keybytes).signature.hex()
        for item in collection.get('inconsistentReports',[]):
            for report in item['reports']:
                td=copy.deepcopy(typed['StateCheckpoint']);td['message']=report['message']
                report['signature']='0x'+Account.sign_message(encode_typed_data(full_message=td),keys[witnesses[int(item['witnessIndex'])]['label']]).signature.hex()
        if response['ok']:
            selected=sorted([witnesses[int(o['witnessIndex'])] for o in collection['outcomes'] if o['status']=='signed'],key=lambda w:w['address'])
            assert len(selected)==3
            td=copy.deepcopy(typed['StateCheckpoint']);td['message']=response['result']['checkpoint']
            response['result']['signatures']=['0x'+Account.sign_message(encode_typed_data(full_message=td),keys[w['label']]).signature.hex() for w in selected]
            collection['submittedSigners']=[w['address'] for w in selected]
    recorded=(response.get('error') or {}).get('recorded')
    if recorded:
        td=copy.deepcopy(typed['StateCheckpoint']);td['message']=recorded['message']
        recorded['signature']='0x'+Account.sign_message(encode_typed_data(full_message=td),keys[labels[0]]).signature.hex()
write('wire.json',dict(status='OWNER_ILLUSTRATIONS_REENCODED_WITH_REAL_SYNTHETIC_SIGNATURES_NOT_EXECUTION',
    sourceSha256=hashlib.sha256(wire.encode()).hexdigest(),responses=examples))
refs=[{'start':'8','length':'32'},{'start':'64','length':'32'}]
write('ledger-export-shape.json',dict(status='SYNTHETIC_SHAPE_ONLY_NO_COMPILED_ABI_OR_RUNTIME',
    entry=dict(abi='NOT-A-COMPILED-EXPORT.json',abiSha256='00'*32,runtimeBytes='128',runtimeSha256='00'*32,
        source='src/Governance.sol',immutableReferences=refs,
        immutableRefsSha256=hashlib.sha256(json.dumps(refs,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest())))
write('strict-json-expectations.json',dict(status='OWNER_D6_PARSER_TEST_INPUTS_NOT_EXECUTED_HERE',
    cases=[{'line':'{"witnessIndex":"0","witnessIndex":"1"}','expected':'MALFORMED','reason':'duplicate key'},
           {'line':'{"witnessIndex":NaN}','expected':'MALFORMED','reason':'non-finite constant'},
           {'line':'{"witnessIndex":Infinity}','expected':'MALFORMED','reason':'non-finite constant'},
           {'line':'{"witnessIndex":0}','expected':'MALFORMED','reason':'JSON number rather than decimal string'}]))
