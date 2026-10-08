"""Exercise the real codec/signature/collector/oracle over synthetic RPC facts.

Only RPC/adapter inputs are doubles: no services or integrated gate claim. Each
mutation names an evidence join whose removal would accept a false result.
"""
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest
from eth_abi import encode
from eth_utils import keccak

from evaluation.evm import AbiContract, _internal, _type
from evaluation.native import NativeReceipt
from evaluation.tests.test_access_artifacts import artifacts, sign
from evaluation.tests.test_bootstrap import inputs
from evaluation.vectors import credential_digest

ROOT = Path(__file__).resolve().parents[2]
ZERO = '0x'+'00'*32
NOW = 1791476010


def execute(model, tmp_path, label='alice'):
    assert importlib.util.find_spec('evaluation.access_execution') is not None, 'Public access execution is missing'
    return importlib.import_module('evaluation.access_execution').execute_access(
        model.pbc, model.dbc, model, deployment_bytes=json.dumps(model.dep).encode(),
        user_label=label, user=model.users[label], record=model.record, policy=model.policy,
        expected_allow=label == 'alice', worker_snapshot=model.snapshot, output=tmp_path/'access')


class Chain:
    def __init__(self, model, name):
        self.model = model; self.name = name; self.rpc = self; self.number = 350
        self.chain_id = model.dep['chains'][name]['chainId']
        pins = json.loads((ROOT/'evaluation/fixtures/e1/abi/PROVENANCE.json').read_text())['files']
        self.contracts = {role: AbiContract(ROOT/'evaluation/fixtures/e1/abi'/(role+'.json'), address, pins[role]['sha256'])
                          for role, address in model.dep['chains'][name]['contracts'].items()}
        self.hashes = {}; self.latest_block()

    def latest_block(self):
        self.hashes[self.number] = '0x'+f'{self.number:064x}'
        return dict(number=hex(self.number), hash=self.hashes[self.number], timestamp=hex(NOW))

    def call(self, method, args=None):
        assert method == 'eth_getBlockByNumber'
        if args[0] == 'pending': return self.latest_block()
        n = int(args[0], 16)
        return dict(number=hex(n), hash=self.hashes[n], timestamp=hex(NOW))

    def read(self, role, method, *args, block=None):
        m = self.model; dep = m.dep
        if method == 'profile': return [dep['profileEnum']]
        if method == 'mutations': return ['0']
        if method == 'policyVersion': return ['1']
        if method == 'authEpoch': return ['3']
        if method == 'relay' or method == 'pscRelay': return [dep['fixture']['relay']['address']]
        if method == 'witnesses': return [dep['fixture']['witnessSet']['witnesses']]
        if method in ('witnessSetVersion', 'threshold'): return ['1']
        if method == 'isRegistered': return [True]
        if method == 'recipientKeyHash': return [next(u['recipientKeyHash'] for u in m.users.values() if u['gid'] == args[0])]
        if method == 'dataEntry': return [dict(exists=True, owner=m.record['owner'], policyId='1')]
        if method == 'policy': return [m.policy['clauses']]
        if method == 'getRequest': return [copy.deepcopy(m.request_state)]
        if method == 'getLog': return m.logs[args[0]]
        if method == 'checkCredentials': return ['0', copy.deepcopy(m.records)]
        if method == 'evaluate': return [m.label == 'alice']
        if method == 'currentCheckpoint': return [m.checkpoint is not None, copy.deepcopy(m.checkpoint or m.default_cp)]
        if method == 'nonceConsumed': return [m.consumed]
        if method == 'grantDetails': return [copy.deepcopy(m.grant)]
        if method == 'getGrant':
            g=m.grant; return [g[k] for k in ('requestDigest','dataId','gid','keyEpoch','expiresAt','allowed')]
        if method == 'accessLogCount': return [str(m.access_count)]
        if method == 'ksscForChain': return [dep['chains']['dbc']['contracts']['KSSC']]
        if method == 'maxRequestTtl' or method == 'grantTtl': return ['30']
        raise AssertionError((role,method,args))

    def observe(self, role, method, *args, block=None):
        c = self.contracts[role]; block = block or self.latest_block(); specs = c._function(method)['outputs']
        values = self.read(role,method,*args,block=block)
        return dict(chainId=self.chain_id, address=c.address, blockHash=block['hash'], blockNumber=str(int(block['number'],16)),
                    calldata=c.calldata(method,*args), returnData='0x'+encode([_type(s) for s in specs],
                                                                             [_internal(s,v) for s,v in zip(specs,values,strict=True)]).hex())

    def submit(self, signer, role, method, *args, expect_success=True):
        m=self.model; self.number += 1; block=self.latest_block(); events=[]
        if method == 'requestAccess':
            req,sig,bundle=args; m.req=req; m.label=next(k for k,u in m.users.items() if u['gid']==req['gid'])
            m.records = copy.deepcopy(m.allow_records if m.label=='alice' else m.bob_records)
            digest=sign('AccessRequest',req,m.dep,m.label)[1];m.digest=digest
            m.request_state=dict(status='1',gid=req['gid'],dataId=req['dataId'],destinationChainId=req['destinationChainId'],kssc=req['kssc'],
                                 credentialDigest=credential_digest(m.records),decidedAt=str(NOW),expiresAt=req['expiresAt'],requestLogId='7',outcomeLogId='0')
            details=ZERO; entry=dict(kind='3',subject=digest,detailsHash=ZERO,blockNumber=str(self.number),timestamp=str(NOW))
            m.logs['7']=[entry, '0x']
            events=[('LSC','LogRecorded',dict(logId='7',kind='3',subject=digest,detailsHash=ZERO,details='0x')),
                    ('PSC','AccessForwarded',dict(requestDigest=digest,gid=req['gid'],dataId=req['dataId'],destinationChainId=req['destinationChainId'],
                                                 kssc=req['kssc'],credentialDigest=credential_digest(m.records),verifiedAttributes=m.records,
                                                 expiresAt=req['expiresAt'],requestLogId='7'))]
            if m.control=='request-state': m.request_state['gid']='0x'+'11'*20
        elif method == 'acceptState':
            m.checkpoint=copy.deepcopy(args[0]);f={k:m.checkpoint[k] for k in ('sequence','authEpoch','policyVersion','keyEpoch','witnessSetVersion',
                                                                          'sourceBlockNumber','sourceBlockHash','expiresAt')}
            events=[('KSSC','StateAccepted',f)]
        elif method in ('policyEnf','consumeDecision'):
            allowed=m.label=='alice'; req=m.req
            if m.control=='grant-all':allowed=True
            if m.control=='deny-all':allowed=False
            m.access_count += 1
            m.gid='0x'+keccak(encode(['bytes32','address','uint256'],[bytes.fromhex(m.digest[2:]), req['kssc'],int(req['destinationChainId'])])).hex()
            if allowed:
                repaired=m.dep['profile']=='repaired-e'; expiry=args[1]['decision']['expiresAt'] if repaired else str(NOW+30)
                m.grant=dict(exists=True,allowed=True,requestDigest=m.digest,dataId=req['dataId'],gid=req['gid'],keyEpoch='0',expiresAt=expiry,
                             recipientKeyHash=req['recipientKeyHash'] if repaired else ZERO,issuedAt=str(NOW))
                m.consumed=repaired
                events.append(('KSSC','GrantIssued',dict(grantId=m.gid,requestDigest=m.digest,gid=req['gid'],dataId=req['dataId'],keyEpoch='0',
                                                        expiresAt=expiry,recipientKeyHash=m.grant['recipientKeyHash'],nonceConsumed=repaired,nonce=req['nonce'] if repaired else '0')))
                if m.control=='grant-recipient':m.grant['recipientKeyHash']=ZERO if repaired else req['recipientKeyHash']
                if m.control=='nonce':m.consumed=not repaired
                if m.control=='grant-expiry':m.grant['expiresAt']=str(NOW)
            f=dict(accessLogId=str(m.access_count),requestRef=m.digest,gid=req['gid'],dataId=req['dataId'],allowed=allowed,code='0' if allowed else '9',
                   credentialDigest=credential_digest(m.records),grantId=m.gid if allowed else ZERO,submitter=m.dep['fixture']['relay']['address'])
            if m.control=='deny-reason':f['code']='7'
            events.append(('ACSC','AccessLog',f))
        elif method in ('reportOutcome','reportAttestedOutcome'):
            m.request_state.update(status='2',outcomeLogId='9')
            f=dict(requestDigest=m.digest,grantId=m.gid,outcomeDigest=args[1] if method=='reportAttestedOutcome' else args[2],logId='9')
            if method=='reportAttestedOutcome':f['dbcBlockNumber']=args[2]['dbcBlockNumber']
            if m.control=='outcome':f['grantId']=ZERO
            events=[('PSC','AttestedOutcomeRecorded' if method=='reportAttestedOutcome' else 'OutcomeRecorded',f)]
        else: raise AssertionError(method)
        tx='0x'+f'{self.number+1000:064x}';logs=[]
        for i,(contract,name,fields) in enumerate(events):
            c=self.contracts[contract];spec=next(x for x in c.abi if x.get('name')==name and x['type']=='event')
            topics=['0x'+keccak(text=c._signature(spec)).hex()]; data=[]
            for s in spec['inputs']:
                v=_internal(s,fields[s['name']])
                if s['indexed']:topics.append('0x'+encode([_type(s)],[v]).hex())
                else:data.append((s,v))
            logs.append(dict(address=c.address,removed=False,topics=topics,data='0x'+encode([_type(s) for s,v in data],[v for s,v in data]).hex(),
                             blockNumber=block['number'],blockHash=block['hash'],transactionHash=tx,transactionIndex='0x0',logIndex=hex(i)))
        receipt=dict(status='0x1',transactionHash=tx,blockHash=block['hash'],blockNumber=block['number'],transactionIndex='0x0',gasUsed='0x1234',logs=logs)
        return NativeReceipt(receipt=receipt,transaction=dict(hash=tx,chainId=hex(int(self.chain_id)),blockHash=block['hash'],blockNumber=block['number'],transactionIndex='0x0'),
                             block=dict(block,transactions=[tx]),chain_id=self.chain_id)


class Model:
    def __init__(self, artifacts, inputs, profile):
        self.dep,_,_,cp,decision,_=artifacts;sample,_=inputs;self.users=sample['users']
        self.dep.update(profile=profile,profileEnum={'paper-strict':'0','paper-minimal':'1','repaired-e':'2'}[profile])
        self.allow_records=decision['credentialRecords'];self.bob_records=[dict(self.allow_records[0],issuer=sample['trustLists'][2]['signer'],
                                                                              role='0x'+keccak(text='HMBC.role.Researcher').hex(),serial='201')]
        self.default_cp=cp['checkpoint'];self.checkpoint=None;self.consumed=False;self.control=None;self.label='alice';self.records=self.allow_records
        self.access_count=0;self.request_state=dict(status='0');self.logs={};self.calls=[]
        self.grant=dict(exists=False,allowed=False,requestDigest=ZERO,dataId=ZERO,gid='0x'+'00'*20,keyEpoch='0',expiresAt='0',recipientKeyHash=ZERO,issuedAt='0')
        self.record=dict(dataId='0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e',owner=self.dep['fixture']['authorities'][1]['root'],payloadDigest='0x'+'55'*32)
        self.policy=dict(clauses=[[dict(role='0x'+keccak(text='HMBC.role.Doctor').hex(),kind='1',issuerMode='0'),
                                   dict(role='0x'+keccak(text='HMBC.role.OnDuty').hex(),kind='2',issuerMode='2')]])
        self.pbc=Chain(self,'pbc');self.dbc=Chain(self,'dbc');self.worker_events=[];self.releases=[]

    def exchange(self, envelope):
        op=envelope['operation'];inp=envelope['input'];self.calls.append(op)
        if op=='prepare_request':
            req=inp['request'];label=inp['signingKeyRef'].split(':')[-1];sig,digest=sign('AccessRequest',req,self.dep,label)
            result=dict(schemaVersion='v1',adapterMode='symbolic',request=req,requestDigest=digest,signature=sig,signer=req['gid'])
        elif op=='encrypt_record':
            pd='0x'+keccak(encode(['(bytes32,uint8,uint8)[][]'], [[[(bytes.fromhex(q['role'][2:]),int(q['kind']),int(q['issuerMode'])) for q in c] for c in self.policy['clauses']]])).hex()
            cd='0x'+keccak(encode(['bytes32','bytes32','address','bytes32','bytes32','uint64'],[keccak(text='HMBCSymbolicRecord/v1'),bytes.fromhex(self.record['dataId'][2:]),
                                                                                       self.record['owner'],bytes.fromhex(self.record['payloadDigest'][2:]),bytes.fromhex(pd[2:]),0])).hex()
            self.cipher=cd;result=dict(schemaVersion='v1',adapterMode='symbolic',dataId=self.record['dataId'],keyEpoch='0',ciphertextDigest=cd,policyDigest=pd)
        elif op=='collect_checkpoint':
            src=self.pbc.latest_block();cp=dict(self.default_cp,sourceBlockNumber=str(self.pbc.number),sourceBlockHash=src['hash'])
            result=dict(schemaVersion='v1',adapterMode='symbolic',checkpoint=cp,signatures=[sign('StateCheckpoint',cp,self.dep,'witness-1')[0]])
        elif op=='collect_decision':
            cp=self.checkpoint;d=dict(requestDigest=self.digest,result='1' if self.label=='alice' else '0',credentialDigest=credential_digest(self.records),
                                     stateSequence=cp['sequence'],witnessSetVersion='1',sourceBlockNumber=cp['sourceBlockNumber'],sourceBlockHash=cp['sourceBlockHash'],expiresAt=self.req['expiresAt'])
            result=dict(schemaVersion='v1',adapterMode='symbolic',decision=d,signatures=[sign('AccessDecision',d,self.dep,'witness-1')[0]],credentialRecords=self.records)
        elif op=='release':
            identity=dict(requestDigest=self.digest,grantId=self.gid,gid=self.req['gid'],dataId=self.req['dataId'])
            self.worker_events=[dict(type=t,timestamp=str(NOW),**identity) for t in ('RELEASE_INTENT','RELEASE_SENT')]
            self.releases=[dict(**identity,ciphertextDigest=self.cipher,recipientKeyHash=self.req['recipientKeyHash'],keyEpoch='0',
                                tokenDigest='0x290decd9548b62a8d60345a988386fc84ba6bc95484008f6362f93160ef3e563',grantExpiresAt=self.grant['expiresAt'],
                                createdAt=str(NOW),delivery='unknown',sendAttempts=1,completedAttempts=1)]
            if self.control=='worker-expiry':self.releases[0]['grantExpiresAt']=str(NOW+10)
            if self.control=='worker-time':
                self.releases[0]['createdAt']=str(NOW-1);self.worker_events[0]['timestamp']=str(NOW-1)
            result=dict(schemaVersion='v1',adapterMode='symbolic',**{k:identity[k] for k in ('requestDigest','grantId','dataId')},
                        ciphertextDigest=self.cipher,recipientKeyHash=self.req['recipientKeyHash'],keyEpoch='0',responseEnvelope=dict(kind='symbolic-partial/v1',token=ZERO))
        elif op=='finish_decryption':
            result=dict(schemaVersion='v1',adapterMode='symbolic',decryptable=self.control!='completion',dataId=self.req['dataId'],ciphertextDigest=self.cipher)
        elif op=='attest_grant':
            src=self.dbc.latest_block();g=self.grant
            receipt=dict(requestDigest=self.digest,grantId=self.gid,gid=self.req['gid'],dataId=self.req['dataId'],keyEpoch='0',grantExpiresAt=g['expiresAt'],
                         witnessSetVersion='1',dbcChainId=self.dbc.chain_id,kssc=self.req['kssc'],dbcBlockNumber=str(self.dbc.number),dbcBlockHash=src['hash'])
            if self.control=='receipt-block':receipt['dbcBlockHash']=ZERO
            result=dict(schemaVersion='v1',adapterMode='symbolic',receipt=receipt,signatures=[sign('GrantReceipt',receipt,self.dep,'witness-1')[0]])
        else:raise AssertionError(op)
        if self.control=='wrong-operation' and op=='prepare_request':result=dict(schemaVersion='v1',adapterMode='symbolic',dataId=self.record['dataId'],keyEpoch='0',ciphertextDigest=ZERO,policyDigest=ZERO)
        if self.control=='malformed-secret' and op=='prepare_request':result['privateKey']='TEST-SECRET-MUST-NOT-BE-LOGGED'
        if self.control=='error-secret' and op=='prepare_request':
            return dict(schemaVersion='v1',ok=False,result=None,error=dict(code='MALFORMED',message='TEST-SECRET-MUST-NOT-BE-LOGGED'))
        return dict(schemaVersion='v1',ok=True,result=result,error=None)

    def snapshot(self):
        chains=self.dep['chains'];fp=hashlib.sha256(json.dumps(dict(pbc=[chains['pbc']['chainId'],chains['pbc']['contracts']['PSC'],chains['pbc']['contracts']['RSC']],
                                                                 dbc=[chains['dbc']['chainId'],chains['dbc']['contracts']['KSSC'],chains['dbc']['contracts']['ACSC']]),sort_keys=True).encode()).hexdigest()
        return json.dumps(dict(schemaVersion='hmbc-worker-log/v0',adapterMode='symbolic',deploymentFingerprint=fp,note='synthetic unknown delivery',
                               events=self.worker_events,releases=self.releases,counts=dict(releaseIntentCount=str(len(self.releases)),releaseSentCount=str(len(self.releases))))).encode()


@pytest.mark.parametrize('profile',['paper-strict','paper-minimal','repaired-e'])
@pytest.mark.parametrize('label',['alice','bob'])
def test_real_checks_accept_legitimate_and_reject_registered_bob(artifacts, inputs, tmp_path, profile, label):
    result=execute(Model(artifacts,inputs,profile),tmp_path,label)
    assert result['ok'] is True and result['observed']['error']==(None if label=='alice' else 'POLICY_DENIED')
    assert [e['type'] for e in result['observed']['events']]==(['REQUEST_LOGGED','PBC_DECIDED','DBC_AUTHORIZED','RELEASE_INTENT','RELEASE_SENT','OUTCOME_RECORDED'] if label=='alice' else ['REQUEST_LOGGED','PBC_DECIDED'])
    raw=(tmp_path/'access'/'exchanges.json').read_text()
    assert '"token"' not in raw


@pytest.mark.parametrize('control',['deny-all,alice','grant-all,bob','request-state,alice','grant-recipient,alice','nonce,alice',
                                         'grant-expiry,alice','deny-reason,bob','worker-expiry,alice','worker-time,alice','completion,alice',
                                         'receipt-block,alice','outcome,alice','wrong-operation,alice'])
def test_native_and_worker_join_mutations_cannot_pass(artifacts,inputs,tmp_path,control):
    # Parameter strings keep each offered fault/expected actor visible in IDs.
    control,label=control.split(',')
    model=Model(artifacts,inputs,'repaired-e');model.control=control
    with pytest.raises(ValueError):execute(model,tmp_path,label)


@pytest.mark.parametrize('control',['malformed-secret','error-secret'])
def test_malformed_reply_is_retained_as_digest_without_unknown_secret_fields(artifacts,inputs,tmp_path,control):
    model=Model(artifacts,inputs,'repaired-e');model.control=control
    with pytest.raises(ValueError):execute(model,tmp_path)
    assert 'TEST-SECRET-MUST-NOT-BE-LOGGED' not in (tmp_path/'access'/'exchanges.json').read_text()
