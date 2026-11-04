"""Reproducible planning audit and schema proposal; never imports peer code."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PROPOSAL = ROOT / 'interfaces/proposals/v2'
PROPOSAL.mkdir(parents=True, exist_ok=True)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


refs = {r: git('rev-parse', r).decode().strip() for r in
        ['HEAD', 'origin/agent-1', 'origin/agent-2', 'origin/agent-3']}
expected_refs = {'origin/agent-1': '6d6ffcbb437eebb7ccb0713a96f322ffd8fdfef2',
                 'origin/agent-2': 'fe03df72a6dadb585451575c20866c57ad7c9d7f'}
assert all(refs[k] == v for k, v in expected_refs.items())
candidate = ROOT / 'evaluation/evidence/reviews/f0-revision8-20261104'
candidate_files = {p.name: sha(p.read_bytes()) for p in
                   [candidate / n for n in ['SOURCE-INTERFACE-PLAN.md', 'f_matrix.json',
                                            'fault-model.csv', 'review-manifest.json']]}
old_manifest = json.loads((candidate / 'review-manifest.json').read_text())
for p, h in old_manifest['files'].items():
    assert sha((ROOT / p).read_bytes()) == h, p
acks = []
for ref, path, mid, scope in [
    ('origin/agent-1', 'communication/agent-1/outbox/0104-ack-f0-candidate8-ledger-scope.md', 'A1-0104', 'ledger'),
    ('origin/agent-2', 'communication/agent-2/outbox/0053-ack-f0-candidate8-protocol-scope.md', 'A2-0053', 'protocol')]:
    blob = git('show', refs[ref] + ':' + path)
    text = blob.decode()
    assert 'Type: ACK' in text and all(h in text for h in candidate_files.values())
    acks.append(dict(messageId=mid, scope=scope, commit=refs[ref], path=path,
                     fileChangingCommit=git('log', '-1', '--format=%H', refs[ref], '--', path).decode().strip(),
                     sha256=sha(blob), covers=candidate_files, mappingAck=False, freezeAck=False))
pins = {}
for ref, p in [('origin/agent-1', 'ledger/f0/A-F1-DESIGN.md')]+[
    ('origin/agent-2', 'protocol/f0/' + p) for p in
    ['D50-DEPLOYMENT-BINDING.md', 'SIGNING-RULES.md', 'SUCCESSOR-WIRE.md', 'MANIFEST.sha256']]:
    pins[p] = sha(git('show', refs[ref] + ':' + p))
assert pins['ledger/f0/A-F1-DESIGN.md'] == '7eed1b29e79144d88d6b5bba33a414e4fcb6dc8fa8cb31262c0742e3baaebfd0'
owner_entries = 0
for line in git('show', refs['origin/agent-2'] + ':protocol/f0/MANIFEST.sha256').decode().splitlines():
    h, p = line.split(maxsplit=1)
    assert sha(git('show', refs['origin/agent-2'] + ':' + p.lstrip('*'))) == h
    owner_entries += 1
assert owner_entries == 36
# Latest communication is selected by changing-commit ancestry, never by timestamp.
communications = {}
for ref in refs.values():
    for p in git('ls-tree', '-r', '--name-only', ref, '--', 'communication').decode().splitlines():
        change = git('log', '-1', '--format=%H', ref, '--', p).decode().strip()
        blobhash = sha(git('show', ref + ':' + p))
        old = communications.get(p)
        if old and old['sha256'] != blobhash:
            if subprocess.run(['git', 'merge-base', '--is-ancestor', change, old['fileChangingCommit']], cwd=ROOT).returncode == 0:
                continue
            assert subprocess.run(['git', 'merge-base', '--is-ancestor', old['fileChangingCommit'], change], cwd=ROOT).returncode == 0, p
        communications[p] = dict(commit=ref, fileChangingCommit=change, sha256=blobhash)
for ref, prefix in [('origin/agent-1', 'ledger'), ('origin/agent-2', 'protocol')]:
    diff = git('diff', '--name-only', '376347d', refs[ref], '--', prefix).decode().splitlines()
    if prefix == 'protocol':
        assert all(p.startswith('protocol/f0/') for p in diff), diff
    else:
        assert not git('diff', '--name-only', '933d2a7', refs[ref], '--', 'ledger/src', 'ledger/script', 'ledger/foundry.toml')
write(OUT / 'input-provenance.json', dict(capturedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      refs=refs, exactCandidate8Acks=acks, intendedDesignPins=pins, ownerF0EntriesVerified=owner_entries,
      priorCandidate8FilesVerified=len(old_manifest['files']), latestCommunication=communications,
      productionUnchanged=True, executionAuthorized=False))

s = json.loads((ROOT / 'interfaces/v1/hmbc.schema.json').read_text())
s['title'] = 'HMBC2020 successor v2 candidate 1 — NOT FROZEN'
s['x-status'] = 'DRAFT_FOR_MAPPING_ACK; no runtime implementation or execution authorization'
d = s['$defs']


def ref(n):
    return {'$ref': '#/$defs/' + n}


def obj(props, optional=()):
    return dict(type='object', properties=props, required=[k for k in props if k not in optional], additionalProperties=False)


def arr(item, low=0, high=None):
    a = dict(type='array', items=item, minItems=low)
    if high is not None:
        a['maxItems'] = high
    return a


def version(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == 'const' and v == 'v1':
                value[k] = 'v2'
            else:
                version(v)
    elif isinstance(value, list):
        for v in value:
            version(v)


version(s)
for name in ['StateCheckpoint', 'AccessDecision', 'GrantReceipt']:
    d[name]['properties']['witnessSetVersion'] = {'enum': ['1', '2']}
d['Uint32'] = dict(type='string', pattern='^(0|[1-9][0-9]*)$', format='uint32')
d['FMutationMask'] = dict(type='string', pattern='^(0|[1-9]|[1-9][0-9]|[1-4][0-9]{2}|50[0-9]|51[01])$')
d['WitnessIndex'] = {'enum': ['0', '1', '2', '3']}
d['ImmutableReference'] = obj({'start': ref('Uint32'), 'length': {'const': '32'}})
d['ImmutableReferences'] = arr(ref('ImmutableReference'))
d['GovernanceAction'] = obj({'action': {'enum': ['1', '2', '3']}, 'root': ref('Address'),
    'admins': arr(ref('Address'), 0, 8), 'nonce': ref('Uint64'),
    'witnessSetVersion': {'const': '2'}, 'expiresAt': ref('Uint64')})
d['GovernanceAction']['x-eip712Type'] = 'GovernanceAction(uint8 action,address root,address[] admins,uint64 nonce,uint64 witnessSetVersion,uint64 expiresAt)'
d['GovernanceAction']['properties']['root'] = {'allOf': [ref('Address'), {'not': {'const':'0x'+'00'*20}}]}
d['GovernanceAction']['properties']['admins']['uniqueItems'] = True
d['GovernanceAction']['allOf'] = [
    {'if': {'properties': {'action': {'const': '1'}}}, 'then': {'properties': {'admins': {'minItems': 1}}}},
    {'if': {'properties': {'action': {'const': '2'}}}, 'then': {'properties': {'admins': {'maxItems': 0}}}}]
d['RecordedCheckpoint'] = obj({'message': ref('StateCheckpoint'), 'signature': ref('Signature')})
d['RecordedReport'] = obj({'witnessIndex': ref('WitnessIndex'), **copy.deepcopy(d['RecordedCheckpoint']['properties'])})
d['InconsistentReport'] = obj({'witnessIndex': ref('WitnessIndex'), 'reports': arr(ref('RecordedCheckpoint'), 2)})
d['AdoptedCheckpoint'] = obj({'message': ref('StateCheckpoint'), 'reporters': arr(ref('WitnessIndex'), 2, 4),
    'reproposal': {'enum': ['sent', 'skipped_validity', 'skipped_deadline']}})
d['CollectionTiming'] = obj({k: ref('Uint256') for k in
    ['ledgerNowAtStart', 'proposalExpiresAt', 'collectionDeadlineMs', 'snapshotClosedAtMs']}
    | {'snapshotClosedBy': {'enum': ['all-replied', 'reply-timeout', 'deadline']}})
reason_groups = {
    'STALE_STATE': ['CONFLICT_PINNED', 'PROPOSAL_MISMATCH', 'WITNESS_SET_MISMATCH'],
    'ADAPTER_UNAVAILABLE': ['QUORUM_UNAVAILABLE', 'WITNESS_FAULTED', 'LEDGER_UNREACHABLE', 'STORE_MISSING', 'STORE_CORRUPT'],
    'WRONG_PROFILE': ['PROFILE_MISMATCH'],
    'WRONG_DESTINATION': ['UNSEALED', 'WIRING_MISMATCH', 'GENESIS_MISMATCH', 'CODE_MISMATCH', 'MUTATIONS_MISMATCH', 'BUILD_MISMATCH', 'LEGACY_STATE', 'BINDING_MISMATCH', 'OWNER_MISMATCH'],
    'MALFORMED': ['BUILD_PIN_INVALID']}
reasons = {r: code for code, rs in reason_groups.items() for r in rs}
assert len(reasons) == 19
codes = copy.deepcopy(d['Error']['properties']['code'])
outcome = obj({'witnessIndex': ref('WitnessIndex'), 'witness': ref('Address'),
    'status': {'enum': ['signed', 'refused', 'invalid', 'silent', 'dissent', 'duplicate-only']},
    'replies': ref('Uint256'), 'code': codes, 'reason': {'enum': list(reasons)},
    'detail': {'type':'string','minLength':1}}, ['code', 'reason', 'detail'])
outcome['allOf'] = [{'if': {'properties': {'status': {'const': 'refused'}}}, 'then': {'required': ['code']},
                     'else': {'not': {'anyOf': [{'required': ['code']}, {'required': ['reason']}]}}}]
for reason, code in reasons.items():
    outcome['allOf'].append({'if': {'required': ['reason'], 'properties': {'reason': {'const': reason}}},
                            'then': {'properties': {'code': {'const': code}}}})
outcome['allOf'].append({'if': {'properties': {'status': {'const': 'silent'}}}, 'then': {'properties': {'replies': {'const': '0'}}},
                         'else': {'properties': {'replies': {'not': {'const': '0'}}}}})
d['WitnessOutcome'] = outcome
d['Collection'] = obj({'quorum': {'const': '3'}, 'witnessSetVersion': {'const': '2'},
    'outcomes': arr(ref('WitnessOutcome'), 4, 4), 'submittedSigners': arr(ref('Address'), 0, 3),
    'recordedReports': arr(ref('RecordedReport'), 0, 4),
    'inconsistentReports': arr(ref('InconsistentReport'), 0, 4),
    'lateReports': arr(ref('RecordedReport')), 'adopted': ref('AdoptedCheckpoint'), 'timing': ref('CollectionTiming')},
    ['recordedReports', 'inconsistentReports', 'lateReports', 'adopted', 'timing'])
retry = ['recordedReports', 'inconsistentReports', 'lateReports', 'adopted']
d['Collection']['allOf'] = [
    {'if': {'anyOf': [{'required': [k]} for k in retry]}, 'then': {'required': ['timing']}},
    {'if': {'required': ['timing']}, 'then': {'anyOf': [{'required': [k]} for k in retry]}},
    {'if': {'required': ['timing'], 'properties': {'timing': {'properties': {'snapshotClosedBy': {'const': 'deadline'}}}}},
     'then': {'not': {'required': ['lateReports']}}}]
d['Collection']['properties']['outcomes']['prefixItems'] = [
    {'allOf': [ref('WitnessOutcome'), {'properties': {'witnessIndex': {'const': str(i)}}}]} for i in range(4)]
d['Error']['properties'].update(reason={'enum': list(reasons)}, collection=ref('Collection'), recorded=ref('RecordedCheckpoint'))
d['Error']['allOf'] = [
    {'if': {'required': ['reason'], 'properties': {'reason': {'const': r}}}, 'then': {'properties': {'code': {'const': c}}}}
    for r, c in reasons.items()]
d['Error']['allOf'] += [
    {'if': {'required': ['collection']}, 'then': {'required': ['reason'], 'properties': {'reason': {'const': 'QUORUM_UNAVAILABLE'}, 'collection': {'properties': {'submittedSigners': {'maxItems': 0}}}}}},
    {'if': {'required': ['reason'], 'properties': {'reason': {'const': 'QUORUM_UNAVAILABLE'}}}, 'then': {'required': ['collection']}},
    {'if': {'required': ['recorded']}, 'then': {'required': ['reason'], 'properties': {'reason': {'const': 'CONFLICT_PINNED'}}, 'not': {'required': ['collection']}}}]
for name in ['CollectCheckpointInput', 'CollectDecisionInput', 'AttestGrantInput']:
    d[name]['properties']['witnessIndex'] = ref('WitnessIndex')
    if 'witnessSetVersion' in d[name]['properties']:
        d[name]['properties']['witnessSetVersion'] = {'enum': ['1', '2']}
d['CollectGovernanceInput'] = copy.deepcopy(d['GovernanceAction'])
d['CollectGovernanceInput']['properties']['witnessIndex'] = ref('WitnessIndex')
for name in ['CollectCheckpointResult', 'CollectDecisionResult', 'AttestGrantResult']:
    d[name]['properties']['signatures']['maxItems'] = 3
    d[name]['properties']['collection'] = ref('Collection')
    d[name]['allOf'] = [{'if': {'required': ['collection']}, 'then': {'properties': {
        'signatures': {'minItems': 3, 'maxItems': 3}, 'collection': {'properties': {'submittedSigners': {'minItems': 3, 'maxItems': 3}}}}},
        'else': {'properties': {'signatures': {'minItems': 1, 'maxItems': 1}}}}]
d['DecisionCertificate']['properties']['signatures']['maxItems'] = 3
d['CollectGovernanceResult'] = obj({'schemaVersion': {'const': 'v2'}, 'adapterMode': {'const': 'symbolic'},
    'governanceAction': ref('GovernanceAction'), 'signatures': arr(ref('Signature'), 1, 3), 'collection': ref('Collection')}, ['collection'])
d['CollectGovernanceResult']['allOf'] = copy.deepcopy(d['CollectCheckpointResult']['allOf'])
d['CollectGovernanceRequest'] = copy.deepcopy(d['CollectCheckpointRequest'])
d['CollectGovernanceRequest']['properties']['operation'] = {'const': 'collect_governance'}
d['CollectGovernanceRequest']['properties']['input'] = ref('CollectGovernanceInput')
d['CollectGovernanceResponse'] = copy.deepcopy(d['CollectCheckpointResponse'])
d['CollectGovernanceResponse']['oneOf'][0]['properties']['result'] = ref('CollectGovernanceResult')
for name, field in [('CollectCheckpointResult','checkpoint'),('CollectDecisionResult','decision'),('AttestGrantResult','receipt')]:
    d[name]['allOf'].append({'if': {'required':['collection']}, 'then': {'properties': {field: {'properties': {'witnessSetVersion': {'const':'2'}}}}}})
for name in ['CollectDecisionResult','AttestGrantResult','CollectGovernanceResult']:
    d[name]['allOf'].append({'properties':{'collection':{'not':{'anyOf':[{'required':[k]} for k in retry+['timing']]}}}})
for name in list(d):
    if name.endswith('Response') and name not in ['AdapterResponse','CollectCheckpointResponse']:
        for branch in d[name].get('oneOf',[]):
            if branch['properties']['ok']['const'] is False:
                branch['properties']['error'] = {'allOf':[ref('Error'),{'not':{'required':['recorded']}}]}
                if name not in ['CollectDecisionResponse','AttestGrantResponse','CollectGovernanceResponse']:
                    branch['properties']['error']['allOf'].append({'not':{'required':['collection']}})
d['AdapterRequest']['oneOf'].append(ref('CollectGovernanceRequest'))
d['AdapterResponse']['oneOf'][0]['properties']['result']['oneOf'].append(ref('CollectGovernanceResult'))
# E export remains an explicit alternative; F export pins seven contracts.
e = copy.deepcopy(d['LedgerDeployment'])
e['properties']['interfaceVersion'] = {'const': 'v2'}
e['x-status'] = 'Candidate successor E carrier; historical E continues to use frozen v1'
f = copy.deepcopy(e)
f['properties']['schemaVersion'] = {'const': 'hmbc-ledger-deployment/v2'}
f['properties']['profile'] = {'const': 'repaired-f'}
f['properties']['profileEnum'] = {'const': '3'}
f['properties']['mutations'] = ref('FMutationMask')
f.pop('allOf', None)
d['LedgerAbiEntry']['properties']['runtimeBytes'] = ref('Uint32')
d['LedgerAbiEntry']['properties'].update(immutableReferences=ref('ImmutableReferences'), immutableRefsSha256=ref('FileHash'))
d['LedgerAbiEntry']['required'] += ['immutableReferences', 'immutableRefsSha256']
for key in ['LedgerAbiContracts', 'LedgerPbcChain', 'LedgerFixture', 'LedgerSourceHashes']:
    d[key + 'F'] = copy.deepcopy(d[key])
d['LedgerAbiContractsF']['properties']['Governance'] = ref('LedgerAbiEntry')
d['LedgerAbiContractsF']['required'].append('Governance')
d['LedgerPbcChainF']['properties']['contracts']['properties']['Governance'] = ref('Address')
d['LedgerPbcChainF']['properties']['contracts']['required'].append('Governance')
d['LedgerSourceHashesF']['properties'].update({'src/Governance.sol': ref('FileHash'), 'src/interfaces/IPolicyVersion.sol': ref('FileHash')})
d['LedgerSourceHashesF']['required'] += ['src/Governance.sol', 'src/interfaces/IPolicyVersion.sol']
d['LedgerWitnessSetF'] = copy.deepcopy(d['LedgerWitnessSet'])
d['LedgerWitnessSetF']['properties'].update(version={'const':'2'}, threshold={'enum':['2','3']}, usedBy={'const':'repaired-f only'})
for key in ['witnesses','keyLabels']:
    d['LedgerWitnessSetF']['properties'][key].update(minItems=4,maxItems=4,uniqueItems=True)
d['LedgerWitnessSetF']['properties']['keyLabels']['prefixItems'] = [{'const': 'witness-'+str(i)} for i in range(1,5)]
d['LedgerFixtureF']['properties']['witnessSet'] = ref('LedgerWitnessSetF')
f['properties']['fixture'] = ref('LedgerFixtureF')
f['properties']['abi'] = ref('LedgerAbiContractsF')
f['properties']['sources'] = ref('LedgerSourceHashesF')
f['properties']['chains']['properties']['pbc'] = ref('LedgerPbcChainF')
d['LedgerDeploymentE'] = e
d['LedgerDeploymentF'] = f
d['LedgerDeployment'] = {'oneOf':[ref('LedgerDeploymentE'),ref('LedgerDeploymentF')]}
# D50 document shape follows the owner vector, without copying its validator.
owner_vector = json.loads(git('show', refs['origin/agent-2'] + ':protocol/f0/vectors/d50_binding_vector.json'))


def binding_shape(value, key=''):
    if isinstance(value, dict):
        return obj({k: binding_shape(v, k) for k, v in value.items()})
    if isinstance(value, list):
        return arr(ref('Address'), 1)
    if key == 'name':
        return {'enum': ['paper-strict', 'paper-minimal', 'repaired-e', 'repaired-f']}
    if key == 'interfaceVersion':
        return {'type': 'string', 'pattern': '^v[0-9]+$'}
    if key.endswith('Sha256'):
        return ref('FileHash')
    if key in ['hash', 'genesisHash']:
        return ref('Hash')
    if value.startswith('0x'):
        return ref('Address')
    return ref('Uint32' if key == 'runtimeBytes' else 'Uint8' if key in ['enum','profile'] else
               'Uint64' if key in ['number','version'] else 'Uint256')


bindings = []
for profile in ['repaired-e', 'repaired-f']:
    shape = binding_shape(owner_vector['documents'][profile]['document'])
    shape['properties']['profile']['properties']['name'] = ({'const': 'repaired-f'} if profile == 'repaired-f'
        else {'enum': ['paper-strict', 'paper-minimal', 'repaired-e']})
    # E accepts all-or-none immutable digests; F requires every digest.
    if profile == 'repaired-e':
        rows = [r for c in shape['properties']['chains']['properties'].values()
                for r in c['properties']['contracts']['properties'].values()]
        no_pins = copy.deepcopy(shape)
        for c in no_pins['properties']['chains']['properties'].values():
            for row in c['properties']['contracts']['properties'].values():
                row['properties'].pop('immutableRefsSha256')
                row['required'].remove('immutableRefsSha256')
        bindings.append(no_pins)
    bindings.append(shape)
d['DeploymentBindingDocument'] = {'oneOf': bindings}
write(PROPOSAL / 'd50-owner-vectors.json', owner_vector)
write(PROPOSAL / 'hmbc.schema.json', s)
write(PROPOSAL / 'reason-codes.json', reasons)
print(json.dumps(dict(refs=refs, communicationPaths=len(communications), ownerF0Entries=owner_entries,
    exactCandidate8Acks=[a['messageId'] for a in acks], schemaDefinitions=len(d), schemaSha256=sha((PROPOSAL/'hmbc.schema.json').read_bytes()))))
