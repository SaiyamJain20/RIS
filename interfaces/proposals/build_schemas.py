"""Generate draft v1 JSON Schemas; publishing these does not freeze v1."""
import json
from pathlib import Path

ROOT = Path(__file__).parent / 'v1'
DRAFT = 'https://json-schema.org/draft/2020-12/schema'
ERRORS = ['BAD_SIGNATURE','WRONG_SUBJECT','WRONG_DESTINATION','UNKNOWN_AUTHORITY','STALE_ANCHOR','STALE_STATE','EXPIRED','REPLAY','POLICY_DENIED','INSUFFICIENT_QUORUM','DUPLICATE_SIGNER','WRONG_EPOCH','NOT_COMMITTED','ADAPTER_UNAVAILABLE','NOT_IMPLEMENTED_IN_PHASE','UNAUTHORIZED_CALLER','NOT_REGISTERED','ALREADY_REGISTERED','REVOKED','MALFORMED','WRONG_PROFILE']
PROFILES = ['paper-strict','paper-minimal','repaired-e','mutant-no-destination-binding','mutant-no-state-barrier','mutant-no-record-freshness','mutant-no-nonce','mutant-no-version-monotone','mutant-no-receipt-binding']
# Exact encodeType strings, independent of JSON property order. Implemented signed
# types match A1-0003/A1-0008 and A1-0011 producer vectors; nested types follow.
EIP712_TYPES = {
    'Registration':'Registration(address gid,bytes32 certDigest,bytes32 recipientKeyHash,uint64 expiresAt)',
    'RoleCertificate':'RoleCertificate(address issuer,address gid,bytes32[] roles,uint64 serial,uint64 validFrom,uint64 validUntil)',
    'RevocationList':'RevocationList(address authority,uint64 version,uint64 validUntil,uint64[] revokedSerials)',
    'TempAclEntry':'TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)',
    'TemporalAcl':'TemporalAcl(address authority,uint64 version,uint64 validUntil,TempAclEntry[] entries)TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)',
    'AccessRequest':'AccessRequest(uint256 sourceChainId,uint256 destinationChainId,address psc,address kssc,address gid,bytes32 dataId,uint8 action,uint64 policyVersion,uint64 authEpoch,uint64 keyEpoch,uint256 nonce,uint64 expiresAt,bytes32 recipientKeyHash)',
    'CredentialRecord':'CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)',
    'AccessDecision':'AccessDecision(bytes32 requestDigest,uint8 result,bytes32 credentialDigest,uint64 stateSequence,uint64 witnessSetVersion,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)',
    'StateCheckpoint':'StateCheckpoint(uint64 sequence,uint64 authEpoch,uint64 policyVersion,uint64 keyEpoch,uint64 witnessSetVersion,uint256 sourceChainId,address psc,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)',
    'GrantReceipt':'GrantReceipt(bytes32 requestDigest,bytes32 grantId,address gid,bytes32 dataId,uint64 keyEpoch,uint64 grantExpiresAt,uint64 witnessSetVersion,uint256 dbcChainId,address kssc,uint256 dbcBlockNumber,bytes32 dbcBlockHash)',
}


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
    d={'Address':{'type':'string','pattern':'^0x[0-9a-f]{40}$','maxLength':42},'Hash':{'type':'string','pattern':'^0x[0-9a-f]{64}$','maxLength':66},'Signature':{'type':'string','pattern':'^0x[0-9a-f]{130}$','format':'canonical-signature'}}
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
    struct('RoleCertificate',[('issuer','Address'),('gid','Address'),('roles','Hash'),('serial','Uint64'),('validFrom','Uint64'),('validUntil','Uint64')]); d['RoleCertificate']['properties']['roles']=array('Hash',1)
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
    struct('GrantReceipt',[('requestDigest','Hash'),('grantId','Hash'),('gid','Address'),('dataId','Hash'),('keyEpoch','Uint64'),('grantExpiresAt','Uint64'),('witnessSetVersion','Uint64'),('dbcChainId','Uint256'),('kssc','Address'),('dbcBlockNumber','Uint256'),('dbcBlockHash','Hash')])
    d['GrantReceipt']['properties']['keyEpoch']={'const':'0'}
    d['GrantReceipt']['properties']['witnessSetVersion']={'const':'1'}
    d['GrantReceipt']['properties']['grantExpiresAt']={**uint(64),'pattern':'^[1-9][0-9]*$'}
    d['GrantReceipt']['x-status']='A1-0008 revision 2 capability/semantics ACKs A3-0005 and A2-0002; A1-0011 implemented. Candidate NOT frozen; past allowed grant, no delivery proof.'
    for name,type_string in EIP712_TYPES.items(): d[name]['x-eip712Type']=type_string
    d['Error']=obj({'code':enum(*ERRORS),'message':{'type':'string'}})
    # Operation-specific input/result/deployment schemas require agent-2's exact revision.
    # Opaque result is explicitly a boundary gap, not claimed strict internal validation.
    d['AdapterResponse']=obj({'schemaVersion':{'const':'v1'},'ok':{'type':'boolean'},'result':{'type':['object','null']},'error':{'anyOf':[ref('Error'),{'type':'null'}]}})
    d['AdapterResponse']['oneOf']=[{'properties':{'ok':{'const':True},'result':{'type':'object'},'error':{'type':'null'}}},{'properties':{'ok':{'const':False},'result':{'type':'null'},'error':ref('Error')}}]
    d['FileHash']={'type':'string','pattern':'^[0-9a-f]{64}$','maxLength':64}
    d['FileHashes']={'type':'object','additionalProperties':ref('FileHash')}
    # Proposed deployment wire contract from A1-0011's four current sample exports.
    # ABI runtimeBytes is compiler measurement metadata; ABI/wire uints are strings.
    d['LedgerAbiEntry']=obj({'abi':string(),'abiSha256':ref('FileHash'),'runtimeBytes':{'type':'integer','minimum':0},'runtimeSha256':ref('FileHash'),'source':string()})
    contracts=('LSC','TMSC','RSC','PSC','ACSC','KSSC')
    d['LedgerAbiContracts']=obj({name:ref('LedgerAbiEntry') for name in contracts})
    sources=('ACSC.sol','DecisionVerifier.sol','KSSC.sol','LSC.sol','PSC.sol','RSC.sol','TMSC.sol','lib/Bootstrapped.sol','lib/SigLib.sol','types/ProtocolTypes.sol')
    d['LedgerSourceHashes']=obj({'src/'+name:ref('FileHash') for name in sources})
    d['LedgerCompiler']=obj({'solc':string(),'evmVersion':string(),'optimizer':obj({'enabled':{'type':'boolean'},'runs':{'type':'integer','minimum':0}}),'viaIR':{'type':'boolean'}})
    d['LedgerAuthority']=obj({'id':enum('H1','H2','H3','H4'),'root':ref('Address'),'caAdmins':{**array('Address',1),'uniqueItems':True},'rootKeyLabel':string(),'caAdminKeyLabel':string()})
    d['LedgerWitnessSet']=obj({'version':{'const':'1'},'threshold':{'const':'1'},'witnesses':{**array('Address',1),'maxItems':1},'keyLabels':{'type':'array','items':string(),'minItems':1,'maxItems':1},'usedBy':{'const':'repaired-e only'}})
    d['LedgerFixture']=obj({
        'keyDerivation':string(),'authorities':{**array('LedgerAuthority',4),'maxItems':4},
        'relay':obj({'address':ref('Address'),'keyLabel':string(),'roles':{'type':'array','items':string(),'minItems':1}}),
        'witnessSet':ref('LedgerWitnessSet'),'policyVersion':ref('Uint64'),'keyEpoch':{'const':'0'},
        'ttlSeconds':obj({'requestMax':{'const':'30'},'decision':{'const':'30'},'checkpointMax':{'const':'60'},'paperGrant':{'const':'30'}}),
        'roles':obj({name:string() for name in ('Doctor','OnDuty','Researcher')}),
        'data':{'type':'array','minItems':1,'items':obj({'dataId':string(),'owner':ref('Address'),'ownerId':enum('H1','H2','H3','H4'),'policy':string()})}})
    for name,members in (('LedgerPbcChain',('LSC','TMSC','RSC','PSC')),('LedgerDbcChain',('ACSC','KSSC'))):
        d[name]=obj({'chainId':ref('Uint256'),'rpcUrl':{'type':'string','format':'uri'},'deployBlock':ref('Uint256'),'contracts':obj({member:ref('Address') for member in members})})
    d['LedgerDeployment']=obj({'schemaVersion':{'const':'hmbc-ledger-deployment/v0'},'interfaceVersion':{'const':'v0 proposed'},'producer':string(),'createdAt':{'type':'string','format':'date-time'},'profile':enum(*PROFILES),'profileEnum':enum('0','1','2'),'mutations':ref('Uint256'),'mutantNote':string(),'logDetailMode':enum('hash-only','complete-details'),'chains':obj({'pbc':ref('LedgerPbcChain'),'dbc':ref('LedgerDbcChain')}),'fixture':ref('LedgerFixture'),'abi':ref('LedgerAbiContracts'),'compiler':ref('LedgerCompiler'),'foundryTomlSha256':ref('FileHash'),'sources':ref('LedgerSourceHashes'),'errorCodes':obj({str(i):{'const':name} for i,name in enumerate(['NONE']+ERRORS)}),'errorEncoding':string()})
    mutation_bits={'paper-strict':('0','0'),'paper-minimal':('1','0'),'repaired-e':('2','0'),**{name:('2',str(1<<i)) for i,name in enumerate(PROFILES[3:])}}
    d['LedgerDeployment']['allOf']=[{'if':{'properties':{'profile':{'const':name}}},'then':{'properties':{'profileEnum':{'const':profile},'mutations':{'const':bits}}}} for name,(profile,bits) in mutation_bits.items()]
    d['LedgerDeployment']['x-status']='Candidate revision3 from A1-0011; exact affected-party ACK pending. Sample consistency is not a live deployment.'
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
