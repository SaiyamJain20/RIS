"""Generate draft v1 JSON Schemas; publishing these does not freeze v1."""
import json
from pathlib import Path

ROOT = Path(__file__).parent / 'v1'
DRAFT = 'https://json-schema.org/draft/2020-12/schema'
ERRORS = ['BAD_SIGNATURE','WRONG_SUBJECT','WRONG_DESTINATION','UNKNOWN_AUTHORITY','STALE_ANCHOR','STALE_STATE','EXPIRED','REPLAY','POLICY_DENIED','INSUFFICIENT_QUORUM','DUPLICATE_SIGNER','WRONG_EPOCH','NOT_COMMITTED','ADAPTER_UNAVAILABLE','NOT_IMPLEMENTED_IN_PHASE','UNAUTHORIZED_CALLER','NOT_REGISTERED','ALREADY_REGISTERED','REVOKED','MALFORMED','WRONG_PROFILE']
PROFILES = ['paper-strict','paper-minimal','repaired-e','mutant-no-destination-binding','mutant-no-state-barrier','mutant-no-record-freshness','mutant-no-nonce','mutant-no-version-monotone']


def obj(properties, optional=()):
    return {'type':'object','properties':properties,'required':[k for k in properties if k not in optional],'additionalProperties':False}


def ref(name):
    return {'$ref':'#/$defs/'+name}


def array(name, minimum=0):
    return {'type':'array','items':ref(name),'minItems':minimum}


def uint(bits):
    return {'type':'string','pattern':'^(0|[1-9][0-9]*)$','maxLength':len(str(2**bits-1)),'format':f'uint{bits}'}


def string():
    return {'type':'string','minLength':1}


def enum(*values):
    return {'enum':list(values)}


def definitions():
    d={'Address':{'type':'string','pattern':'^0x[0-9a-f]{40}$'},'Hash':{'type':'string','pattern':'^0x[0-9a-f]{64}$'},'Signature':{'type':'string','pattern':'^0x[0-9a-f]{130}$','format':'canonical-signature'}}
    for bits in (8,64,256): d[f'Uint{bits}']=uint(bits)
    def struct(name, fields):
        d[name]=obj({key:ref(kind) for key,kind in fields})
    struct('AccessRequest',[('sourceChainId','Uint256'),('destinationChainId','Uint256'),('psc','Address'),('kssc','Address'),('gid','Address'),('dataId','Hash'),('action','Uint8'),('policyVersion','Uint64'),('authEpoch','Uint64'),('keyEpoch','Uint64'),('nonce','Uint256'),('expiresAt','Uint64'),('recipientKeyHash','Hash')])
    d['AccessRequest']['properties']['keyEpoch']={'const':'0'}
    struct('AccessDecision',[('requestDigest','Hash'),('result','Uint8'),('credentialDigest','Hash'),('stateSequence','Uint64'),('witnessSetVersion','Uint64'),('sourceBlockNumber','Uint256'),('sourceBlockHash','Hash'),('expiresAt','Uint64')])
    d['AccessDecision']['properties']['result']=enum('0','1');d['AccessDecision']['properties']['witnessSetVersion']={'const':'1'}
    struct('StateCheckpoint',[(k,'Uint64') for k in ('sequence','authEpoch','policyVersion','keyEpoch','witnessSetVersion')]+[('sourceChainId','Uint256'),('psc','Address'),('sourceBlockNumber','Uint256'),('sourceBlockHash','Hash'),('expiresAt','Uint64')])
    d['StateCheckpoint']['properties']['keyEpoch']={'const':'0'};d['StateCheckpoint']['properties']['witnessSetVersion']={'const':'1'}
    struct('Registration',[('gid','Address'),('certDigest','Hash'),('recipientKeyHash','Hash'),('expiresAt','Uint64')])
    struct('RoleCertificate',[('issuer','Address'),('gid','Address'),('serial','Uint64'),('validFrom','Uint64'),('validUntil','Uint64')]); d['RoleCertificate']['properties']['roles']=array('Hash',1);d['RoleCertificate']['required'].append('roles')
    d['SignedRoleCertificate']=obj({'cert':ref('RoleCertificate'),'signature':ref('Signature')})
    struct('RevocationList',[('authority','Address'),('version','Uint64'),('validUntil','Uint64')]); d['RevocationList']['properties']['revokedSerials']=array('Uint64');d['RevocationList']['required'].append('revokedSerials')
    struct('TempAclEntry',[('gid','Address'),('role','Hash'),('validFrom','Uint64'),('validUntil','Uint64')])
    struct('TemporalAcl',[('authority','Address'),('version','Uint64'),('validUntil','Uint64')]);d['TemporalAcl']['properties']['entries']=array('TempAclEntry');d['TemporalAcl']['required'].append('entries')
    struct('TemporalClaim',[('authority','Address'),('role','Hash')])
    d['CredentialBundle']=obj({'certificates':array('SignedRoleCertificate'),'temporalClaims':array('TemporalClaim')})
    struct('CredentialRecord',[('issuer','Address'),('role','Hash'),('kind','Uint8'),('serial','Uint64'),('anchorVersion','Uint64'),('validUntil','Uint64')]);d['CredentialRecord']['properties']['kind']=enum('1','2')
    d['CredentialRecords']=array('CredentialRecord')
    d['DecisionCertificate']=obj({'decision':ref('AccessDecision'),'signatures':array('Signature',1)})
    d['DecisionCertificate']['properties']['signatures']['maxItems']=1
    struct('ForwardedRequest',[('pbcRequestId','Hash'),('gid','Address'),('dataId','Hash'),('action','Uint8')])
    struct('GrantReceipt',[('requestDigest','Hash'),('grantId','Hash'),('dbcResult','Uint8'),('keyEpoch','Uint64'),('grantExpiresAt','Uint64'),('dbcChainId','Uint256'),('kssc','Address'),('dbcBlockNumber','Uint256'),('dbcBlockHash','Hash')]);d['GrantReceipt']['properties']['dbcResult']={'const':'1'};d['GrantReceipt']['properties']['keyEpoch']={'const':'0'}
    d['Error']=obj({'code':enum(*ERRORS),'message':{'type':'string'}})
    # Operation-specific input/result/deployment schemas require agent-2's exact revision.
    # Opaque result is explicitly a boundary gap, not claimed strict internal validation.
    d['AdapterResponse']=obj({'schemaVersion':{'const':'v1'},'ok':{'type':'boolean'},'result':{'type':['object','null']},'error':{'anyOf':[ref('Error'),{'type':'null'}]}})
    d['AdapterResponse']['oneOf']=[{'properties':{'ok':{'const':True},'result':{'type':'object'},'error':{'type':'null'}}},{'properties':{'ok':{'const':False},'result':{'type':'null'},'error':ref('Error')}}]
    d['FileHash']={'type':'string','pattern':'^[0-9a-f]{64}$'}
    d['FileHashes']={'type':'object','additionalProperties':ref('FileHash')}
    d['EventName']=enum('REQUEST_LOGGED','PBC_DECIDED','DBC_AUTHORIZED','RELEASE_INTENT','RELEASE_SENT','OUTCOME_RECORDED')
    d['ControlPolicy']=obj({'longTerm':{'const':'Doctor'},'temporal':{'const':'OnDuty'},'issuerMode':{'const':'SAME_AS_FIRST'},'emergencyContext':{'const':'assumed synthetic'}})
    d['ControlFixture']=obj({'actor':enum('Alice','Bob','WrongIssuerAdmin'),'requestDigest':ref('Hash'),'grantId':ref('Hash'),'gid':ref('Address'),'dataId':ref('Hash'),'kssc':ref('Address'),'destinationChainId':ref('Uint256'),'recipientKeyHash':ref('Hash'),'keyEpoch':{'const':'0'},'policy':ref('ControlPolicy')})
    d['Fault']=obj({'kind':string(),'step':ref('Uint64')})
    d['Scenario']=obj({'id':string(),'rq':{'const':'E'},'profile':enum(*PROFILES),'sourceRefs':{'type':'array','items':string(),'minItems':1},'assumptions':{'type':'array','items':string(),'minItems':1},'fixture':ref('ControlFixture'),'faultSchedule':array('Fault'),'expectedClass':enum('SUPPORTED','SPEC_GAP','RECONSTRUCTION_FAILURE','REPAIR_SUPPORTED','REFUTED','BLOCKED'),'expectedEvents':array('EventName'),'expectedError':{'anyOf':[enum(*ERRORS),{'type':'null'}]},'adapterMode':{'const':'symbolic'}})
    d['Command']=obj({'argv':{'type':'array','items':{'type':'string'},'minItems':1},'cwd':string(),'startedAt':string(),'endedAt':string(),'exitCode':{'type':'integer'},'timedOut':{'type':'boolean'},'elapsedSeconds':{'type':'number','minimum':0},'outputSha256':ref('FileHash')})
    # Numbers here are measurement metadata/exit status, not ABI/EIP-712 uint wire fields.
    d['RunManifest']=obj({'runId':string(),'rq':{'const':'E'},'profile':enum(*PROFILES),'interfaceVersion':string(),'adapterMode':{'const':'symbolic'},'executionMode':enum('preflight','provided-traces','real-integrated'),'status':enum('BLOCKED','PASS','FAIL'),'sourceManifest':ref('FileHashes'),'sourceStable':{'type':'boolean'},'toolVersions':{'type':'object','additionalProperties':{'type':'string'}},'commands':array('Command'),'inputHashes':ref('FileHashes'),'seed':{'type':['integer','null']},'startedAt':string(),'endedAt':string(),'exitCodes':{'type':'array','items':{'type':'integer'}},'resultFiles':ref('FileHashes'),'blockers':{'type':'array','items':string()},'commit':{'type':'string','pattern':'^[0-9a-f]{40}$'},'dirtyTree':{'type':'array','items':{'type':'string'}}})
    return d


def main():
    ROOT.mkdir(exist_ok=True)
    defs=definitions()
    schema={'$schema':DRAFT,'title':'HMBC v1 candidate NOT frozen','$defs':defs}
    (ROOT/'hmbc.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
    print(f'{len(defs)} candidate definitions generated')


if __name__=='__main__': main()
