"""Offline proposal checks, not an adapter, F oracle, or execution gate."""
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.schema import FORMATS, _uint, semantics
from jsonschema import Draft202012Validator, ValidationError
from eth_account import Account
from eth_account.messages import encode_typed_data

P = ROOT/'interfaces/proposals/v2'
schema = json.loads((P/'hmbc.schema.json').read_text())
FORMATS.checks('uint32')(lambda v: _uint(v, 32))
Draft202012Validator.check_schema(schema)
checks = 0


def validate(name, value):
    doc = schema | {'$ref':'#/$defs/'+name}
    Draft202012Validator(doc,format_checker=FORMATS).validate(value)


def yes(name, value):
    global checks
    validate(name,value)
    checks += 1


def no(name, value):
    global checks
    try:
        validate(name,value)
    except ValidationError:
        checks += 1
        return
    raise AssertionError('accepted malformed '+name)


for value in ['0','1',str(2**32-1)]:
    yes('Uint32',value)
for value in [True,0,'00','01','-1',str(2**32)]:
    no('Uint32',value)
signing = json.loads((P/'vectors/signing.json').read_text())['vectors']
fixture = json.loads((P/'vectors/witnesses.json').read_text())['witnesses']
recoveries = 0
for v in signing:
    yes(v['name'], v['typedData']['message'])
    encoded = encode_typed_data(full_message=v['typedData'])
    for r in v['signatures']:
        yes('Signature',r['signature'])
        assert Account.recover_message(encoded,signature=r['signature']).lower()==r['signer']
        recoveries += 1
    if v['name']=='GovernanceAction':
        assert v['independentAbiWordEncodingMatches']
        for field,replacement in [('action','2' if v['typedData']['message']['action']!='2' else '3'),
            ('root','0x'+'99'*20),('admins',['0x'+'33'*20]),('nonce','2'),('witnessSetVersion','3'),('expiresAt','1800000061')]:
            mutated=copy.deepcopy(v['typedData']);mutated['message'][field]=replacement
            assert Account.recover_message(encode_typed_data(full_message=mutated),signature=v['signatures'][0]['signature']).lower()!=v['signatures'][0]['signer']
            checks+=1
for row in json.loads((P/'vectors/success.json').read_text()):
    yes('AdapterResponse',row['response'])
    yes({'collect_checkpoint':'CollectCheckpoint','collect_decision':'CollectDecision','attest_grant':'AttestGrant','collect_governance':'CollectGovernance'}[row['operation']]+'Response',row['response'])
    for sig in row['response']['result']['signatures']:
        yes('Signature',sig)

def recover_checkpoint(message, signature):
    global recoveries
    td=copy.deepcopy(signing[0]['typedData']);td['message']=message
    recovered=Account.recover_message(encode_typed_data(full_message=td),signature=signature).lower()
    recoveries+=1
    return recovered


examples=json.loads((P/'vectors/wire.json').read_text())['responses']
for x in examples:
    yes('AdapterResponse',x)
    extra=copy.deepcopy(x);extra['unexpected']=True
    no('AdapterResponse',extra)
    container=x.get('result') or x.get('error')
    c=container.get('collection')
    if 'recorded' in container:
        r=container['recorded']
        assert recover_checkpoint(r['message'],r['signature'])==fixture[0]['address']
    if c:
        for key in ['recordedReports','lateReports']:
            for r in c.get(key,[]):
                assert recover_checkpoint(r['message'],r['signature'])==fixture[int(r['witnessIndex'])]['address']
        for item in c.get('inconsistentReports',[]):
            for r in item['reports']:
                assert recover_checkpoint(r['message'],r['signature'])==fixture[int(item['witnessIndex'])]['address']
        if x['ok']:
            recovered=[recover_checkpoint(x['result']['checkpoint'],sig) for sig in x['result']['signatures']]
            assert recovered==sorted(set(recovered))==c['submittedSigners']
            assert set(recovered)<={o['witness'] for o in c['outcomes'] if o['status']=='signed'}
    if not c:
        continue
    assert len(c['outcomes'])==4
    bad=copy.deepcopy(c);bad['outcomes'].reverse();no('Collection',bad)
    if 'timing' in c:
        bad=copy.deepcopy(c);del bad['timing'];no('Collection',bad)
        bad=copy.deepcopy(c);bad['timing']['unknown']='0';no('Collection',bad)
        t=c['timing'];start=int(t['ledgerNowAtStart']);expiry=int(t['proposalExpiresAt'])
        deadline=min(10000,(expiry-start-2)*1000)
        assert deadline>0 and deadline==int(t['collectionDeadlineMs'])
        closed=int(t['snapshotClosedAtMs']);assert 0<=closed<=min(5000,deadline)
        if t['snapshotClosedBy']=='deadline':
            assert closed==deadline<=5000 and 'lateReports' not in c
        elif t['snapshotClosedBy']=='reply-timeout':
            assert closed==5000<deadline
        else:
            assert closed<min(5000,deadline)
        reports=c.get('recordedReports',[])
        ids=[int(r['witnessIndex']) for r in reports]
        assert ids==sorted(set(ids))
        inconsistent=c.get('inconsistentReports',[])
        iids=[int(r['witnessIndex']) for r in inconsistent]
        assert iids==sorted(set(iids)) and not set(ids)&set(iids)
        groups={}
        for r in reports:
            groups.setdefault(json.dumps(r['message'],sort_keys=True),[]).append(r['witnessIndex'])
        eligible=[(m,ws) for m,ws in groups.items() if len(ws)>=2]
        assert ('adopted' in c)==(len(eligible)==1)
        if 'adopted' in c:
            a=c['adopted'];assert a['message']==json.loads(eligible[0][0]) and a['reporters']==eligible[0][1]
            expected=('skipped_deadline' if closed>=deadline else 'skipped_validity' if int(a['message']['expiresAt'])*1000-(start*1000+closed)<=2000 else 'sent')
            assert a['reproposal']==expected
            if x['ok']:
                assert x['result']['checkpoint']==a['message']
        checks+=1

reasons=json.loads((P/'reason-codes.json').read_text())
for reason,code in reasons.items():
    if reason=='QUORUM_UNAVAILABLE':
        continue
    e=dict(code=code,reason=reason,message='synthetic shape check')
    yes('Error',e)
    no('Error',e|{'code':'REPLAY'})
no('Error',dict(code='ADAPTER_UNAVAILABLE',reason='UNKNOWN_REASON',message='x'))
no('Error',dict(code='EXPIRED',message='x',recorded=examples[6]['error']['recorded']))
gov=next(v['typedData']['message'] for v in signing if v['name']=='GovernanceAction')
no('GovernanceAction',gov|{'root':'0x'+'00'*20})
no('GovernanceAction',gov|{'action':'2'})
no('GovernanceAction',gov|{'admins':[gov['admins'][0],gov['admins'][0]]})
yes('FMutationMask','511');no('FMutationMask','512');no('FMutationMask','01')
for name in ['CollectDecisionInput','CollectCheckpointInput','AttestGrantInput']:
    value=({'requestDigest':'0x'+'00'*32} if name=='CollectDecisionInput' else {'grantId':'0x'+'00'*32} if name=='AttestGrantInput' else {})
    for i in ['0','1','2','3']:
        yes(name,value|{'witnessIndex':i})
    for k,v in [('witnessIndex','4'),('witnessIndex',0),('sequence','1'),('sourceBlockNumber','1')]:
        no(name,value|{k:v})

owner=json.loads((P/'d50-owner-vectors.json').read_text())
for v in owner['documents'].values():
    yes('DeploymentBindingDocument',v['document'])
    text=json.dumps(v['document'],sort_keys=True,separators=(',',':'),ensure_ascii=True)
    assert text==v['canonicalJson']
    assert hashlib.sha256(b'hmbc-deployment-binding/v2\n'+text.encode('ascii')).hexdigest()==v['bindingV2']
    no('DeploymentBindingDocument',v['document']|{'owner':'worker'})
    mutated=copy.deepcopy(v['document']);del mutated['chains']['pbc']['contracts']['LSC']['immutableRefsSha256']
    no('DeploymentBindingDocument',mutated)
    checks+=1
r=owner['immutableRefs']
entry=json.loads((P/'vectors/ledger-export-shape.json').read_text())['entry']
yes('LedgerAbiEntry',entry)
no('LedgerAbiEntry',entry|{'runtimeBytes':128})
no('LedgerAbiEntry',entry|{'immutableReferences':[[8,32]]})
bad=copy.deepcopy(entry);del bad['immutableRefsSha256'];no('LedgerAbiEntry',bad)
yes('ImmutableReferences',r['objectList'])
assert hashlib.sha256(json.dumps(r['objectList'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()==r['immutableRefsSha256']
no('ImmutableReferences',[[8,32]])
no('ImmutableReferences',[{'start':8,'length':'32'}])
no('ImmutableReferences',[{'start':'8','length':'31'}])
print(json.dumps(dict(status='OFFLINE_PROPOSAL_CHECKS_PASS',checks=checks,signingRecoveries=recoveries,
    wireExamples=len(examples),schemaDefinitions=len(schema['$defs']),
    versions={p:importlib.metadata.version(p) for p in ['jsonschema','eth-account','eth-abi']},
    limitations=['No adapter, Solidity, RPC, process timing, F implementation or RQ gate executed.',
                 'Runtime/stateful invariants in BOUNDARY.md require future owner implementations and integration.',
                 'Same-model correlated review; recovery is real secp256k1 on synthetic fixtures only.']),indent=2))
