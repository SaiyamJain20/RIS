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

P = ROOT/'interfaces/proposals/v2-candidate2'
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
yes('LedgerAbiEntryV2',entry)
no('LedgerAbiEntryV2',entry|{'runtimeBytes':128})
no('LedgerAbiEntryV2',entry|{'immutableReferences':[[8,32]]})
bad=copy.deepcopy(entry);del bad['immutableRefsSha256'];no('LedgerAbiEntryV2',bad)
yes('ImmutableReferences',r['objectList'])
assert hashlib.sha256(json.dumps(r['objectList'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()==r['immutableRefsSha256']
no('ImmutableReferences',[[8,32]])
no('ImmutableReferences',[{'start':8,'length':'32'}])
no('ImmutableReferences',[{'start':'8','length':'31'}])
# Corrections M1-M4/P1-P7/N1-N4 and exact exporter shape mapping.
v1=json.loads((ROOT/'interfaces/v1/hmbc.schema.json').read_text())['$defs']
for name in ['LedgerAbiEntry','LedgerAbiContracts']:
    assert schema['$defs'][name]==v1[name]
    checks+=1
for name in ['LedgerDeploymentE','LedgerDeploymentF']:
    assert schema['$defs'][name]['properties']['schemaVersion']=={'const':'hmbc-ledger-deployment/v2'}
    assert schema['$defs'][name]['properties']['interfaceVersion']=={'const':'v2'}
    checks+=1
for profile,vector in owner['documents'].items():
    b=vector['document']
    bad=copy.deepcopy(b);bad['profile']['enum']='0' if b['profile']['enum']!='0' else '1'
    no('DeploymentBindingDocument',bad)
    for set_name in b['witnessSets']:
        bad=copy.deepcopy(b);bad['witnessSets'][set_name]['witnesses']*=2
        no('DeploymentBindingDocument',bad)
    if profile=='repaired-f':
        no('DeploymentBindingDocument',b|{'interfaceVersion':'v1'})
for name in ['GovernanceAction','CollectGovernanceInput']:
    no(name,gov|{'admins':['0x'+'00'*20]})
c=schema['$defs']['LedgerDeploymentF']['allOf'][0]
for threshold,mask,accept in [('2','0',True),('2','64',False),('3','0',True),('3','64',True)]:
    assert Draft202012Validator(c).is_valid({'mutations':mask,'fixture':{'witnessSet':{'threshold':threshold}}})==accept
    checks+=1
g=schema['$defs']['LedgerFixtureF']['properties']['governance']
assert Draft202012Validator(g).is_valid({'maxGovernanceTtl':'120','maxAdmins':'8'})
for invalid in [{'maxGovernanceTtl':'121','maxAdmins':'8'},{'maxGovernanceTtl':'120','maxAdmins':'9'},{}]:
    assert not Draft202012Validator(g).is_valid(invalid)
    checks+=1
import itertools
for reporters in [list(x) for n in [2,3,4] for x in itertools.combinations(['0','1','2','3'],n)]:
    yes('AdoptedCheckpoint',{'message':signing[0]['typedData']['message'],'reporters':reporters,'reproposal':'sent'})
for reporters in [['0','0'],['1','0'],['3','2','1']]:
    no('AdoptedCheckpoint',{'message':signing[0]['typedData']['message'],'reporters':reporters,'reproposal':'sent'})
for field in ['recordedReports','inconsistentReports','lateReports']:
    collection=next((r.get('result') or r.get('error'))['collection'] for r in examples if 'timing' in (r.get('result') or r.get('error')).get('collection',{}))
    no('Collection',collection|{field:[]})
layouts=json.loads((P/'export-layout-owner-vectors.json').read_text())
for b in layouts['bindingExports'].values():
    yes('BindingExport',b)
    no('BindingExport',b|{'extra':None})
    no('BindingExport',b|{'owner':'witness:0X'+'11'*20})
for name,ev in layouts['evidence'].items():
    yes('WitnessEvidence',ev)
    assert ev['evidenceSha256'] == hashlib.sha256(json.dumps({k:v for k,v in ev.items() if k!='evidenceSha256'},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')).hexdigest()
    no('WitnessEvidence',ev|{'extra':None})
    no('WitnessEvidence',ev|{'owner':'worker'})
    no('WitnessEvidence',ev|{'marker':ev['marker']|{'schema':'1'}})
    for bucket in ['conflicts','superseded']:
        for i,row in enumerate(ev[bucket]):
            bad=copy.deepcopy(ev);bad[bucket][i]['effect']['extra']=None
            no('WitnessEvidence',bad)
            bad=copy.deepcopy(ev);bad[bucket][i]['digests'][0]['extra']=None
            no('WitnessEvidence',bad)
            bad=copy.deepcopy(ev)
            digest=bad[bucket][i]['digests'][0]
            if row['type']=='GrantReceipt':digest['expiresAt']='1'
            else:del digest['expiresAt']
            no('WitnessEvidence',bad)
            if bucket=='superseded':
                bad=copy.deepcopy(ev);death=bad[bucket][i]['death']
                if 'observed' in death:del death['observed']
                else:death['observed']='1'
                no('WitnessEvidence',bad)
                if row['death']['kind']=='overtaken-decision-grant':
                    bad=copy.deepcopy(ev);bad[bucket][i]['effect']['result']='0'
                    no('WitnessEvidence',bad)
for text in layouts['refusalLines'].values():
    value=json.loads(text);yes('ExporterError',value)
    no('ExporterError',value|{'code':'REPLAY'})
    no('ExporterError',value|{'extra':None})
no('ExporterError',{'code':'STALE_STATE','reason':'WITNESS_SET_MISMATCH','message':'x'})
print(json.dumps(dict(status='OFFLINE_PROPOSAL_CHECKS_PASS',checks=checks,signingRecoveries=recoveries,
    wireExamples=len(examples),schemaDefinitions=len(schema['$defs']),
    versions={p:importlib.metadata.version(p) for p in ['jsonschema','eth-account','eth-abi']},
    limitations=['No adapter, Solidity, RPC, process timing, F implementation or RQ gate executed.',
                 'Runtime/stateful invariants in BOUNDARY.md require future owner implementations and integration.',
                 'Same-model correlated review; recovery is real secp256k1 on synthetic fixtures only.']),indent=2))
