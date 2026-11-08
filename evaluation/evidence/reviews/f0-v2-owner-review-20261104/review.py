"""Candidate1 defect reproductions and in-memory correction checks; no runtime code."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
P = ROOT / 'interfaces/proposals/v2'
REFS = {'agent-1': 'adb668dfa643a77732c6b3093c5b4053b798aa12',
        'agent-2': '9ced19af68bec8348d696f4db510fd9cfca497f4',
        'agent-3': '4de6274e8479659f2808552061585895bb897b2d'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def corrected_schema(schema):
    """Prospective changes only. Final owner revision8 pins/layouts are absent."""
    s = copy.deepcopy(schema)
    s['title'] = 'Prospective candidate2 corrections — incomplete draft, NOT FROZEN'
    s['x-status'] = 'REVIEW_PREPARATION_ONLY; owner revision8 and export layouts absent; no mapping ACK or execution authorization'
    d = s['$defs']
    # M1; both bounds are explicit proposed constants, not measured live views.
    d['LedgerFixtureF']['properties']['governance'] = {
        'type': 'object', 'additionalProperties': False,
        'properties': {'maxGovernanceTtl': {'const': '120'}, 'maxAdmins': {'const': '8'}},
        'required': ['maxGovernanceTtl', 'maxAdmins']}
    d['LedgerFixtureF']['required'].append('governance')
    # M2: preserve the historical definition's actual v1 meaning, rename all
    # successor references before restoring it. E and F successor carriers use v2.
    d['LedgerAbiEntryV2'] = d.pop('LedgerAbiEntry')
    def rename(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k == '$ref' and v == '#/$defs/LedgerAbiEntry':
                    value[k] = '#/$defs/LedgerAbiEntryV2'
                else:
                    rename(v)
        elif isinstance(value, list):
            for v in value:
                rename(v)
    rename(s)
    d['LedgerAbiEntry'] = json.loads((ROOT/'interfaces/v1/hmbc.schema.json').read_text())['$defs']['LedgerAbiEntry']
    d['LedgerDeploymentE']['properties']['schemaVersion'] = {'const': 'hmbc-ledger-deployment/v2'}
    # M3: q2 and nonzero code masks cannot be combined in this evidence profile.
    d['LedgerDeploymentF']['allOf'] = [{
        'if': {'properties': {'fixture': {'properties': {'witnessSet': {
            'properties': {'threshold': {'const': '2'}}}}}}},
        'then': {'properties': {'mutations': {'const': '0'}}}}]
    # P1 schema portion only: normalization/runtime precedence still owner work.
    for shape in d['DeploymentBindingDocument']['oneOf']:
        names = shape['properties']['profile']['properties']['name']
        allowed = [names['const']] if 'const' in names else names['enum']
        shape['properties']['profile'] = {
            'oneOf': [{'type': 'object', 'additionalProperties': False,
                'properties': {'name': {'const': name}, 'enum': {'const': str(i)}},
                'required': ['name', 'enum']}
                for i, name in enumerate(['paper-strict', 'paper-minimal', 'repaired-e', 'repaired-f'])
                if name in allowed]}
        def unique(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    if k == 'witnesses' and isinstance(v, dict) and v.get('type') == 'array':
                        v['uniqueItems'] = True
                    unique(v)
            elif isinstance(value, list):
                for v in value:
                    unique(v)
        unique(shape)
    # P4/P5, N1; ordering is structural where the finite set permits it.
    for name in ['recordedReports', 'inconsistentReports', 'lateReports']:
        d['Collection']['properties'][name]['minItems'] = 1
    d['AdoptedCheckpoint']['properties']['reporters'] = {
        'enum': [list(x) for n in [2, 3, 4] for x in itertools.combinations(['0', '1', '2', '3'], n)]}
    d['GovernanceAction']['properties']['admins']['items'] = {
        'allOf': [{'$ref': '#/$defs/Address'}, {'not': {'const': '0x'+'00'*20}}]}
    # Input is a separately copied definition, so apply N1 there too.
    d['CollectGovernanceInput']['properties']['admins']['items'] = copy.deepcopy(
        d['GovernanceAction']['properties']['admins']['items'])
    return s


def run():
    provenance = {'refs': REFS, 'reviews': [], 'ownerManifests': {},
                  'classification': 'TESTED_PROPOSAL_SHAPE_RESULT_NOT_RUNTIME',
                  'mappingAck': False, 'freezeAck': False}
    for owner, path in [('agent-1', 'communication/agent-1/outbox/0105-review-v2-candidate1-ledger-mappings.md'),
                        ('agent-2', 'communication/agent-2/outbox/0054-review-v2-candidate1-protocol-mappings.md')]:
        blob = git('show', REFS[owner]+':'+path)
        assert b'Type: REVIEW' in blob
        provenance['reviews'].append({'path': path, 'commit': REFS[owner], 'sha256': sha(blob),
            'fileChangingCommit': git('log', '-1', '--format=%H', REFS[owner], '--', path).decode().strip()})
    # Verify blobs, never import peer implementations or modify peer mailboxes.
    for owner, manifest, base in [
        ('agent-1', 'ledger/evidence/source-manifest.sha256', ''),
        ('agent-2', 'protocol/evidence/source-manifest.sha256', ''),
        ('agent-2', 'protocol/f0/MANIFEST.sha256', ''),
        ('agent-2', 'protocol/v2-review/candidate1/MANIFEST.sha256', 'protocol/v2-review/candidate1/')]:
        blob = git('show', REFS[owner]+':'+manifest)
        count = 0
        for line in blob.decode().splitlines():
            h, path = line.split(maxsplit=1)
            path = base + path.lstrip('*').removeprefix('./')
            assert sha(git('show', REFS[owner]+':'+path)) == h, path
            count += 1
        provenance['ownerManifests'][manifest] = {'sha256': sha(blob), 'verifiedEntries': count}
    for path in ['interfaces/proposals/v2/MANIFEST.json',
                 'evaluation/evidence/reviews/f0-v2-candidate1-20261104/review-manifest.json']:
        m = json.loads((ROOT/path).read_text())
        for p, h in m['files'].items():
            assert sha((ROOT/p).read_bytes()) == h, p
    # All fetched communication: newest changing-commit ancestry; no mtimes.
    communications = {}
    for commit in REFS.values():
        for path in git('ls-tree', '-r', '--name-only', commit, '--', 'communication').decode().splitlines():
            change = git('log', '-1', '--format=%H', commit, '--', path).decode().strip()
            row = {'commit': commit, 'fileChangingCommit': change, 'sha256': sha(git('show', commit+':'+path))}
            old = communications.get(path)
            if old and old['sha256'] != row['sha256']:
                def ancestor(a, b):
                    result = subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], cwd=ROOT)
                    assert result.returncode in [0, 1]
                    return result.returncode == 0
                if ancestor(change, old['fileChangingCommit']):
                    continue
                assert ancestor(old['fileChangingCommit'], change), path
            communications[path] = row
    provenance['latestCommunication'] = communications
    for owner, base, paths in [('agent-1', '933d2a7', ['ledger/src', 'ledger/script', 'ledger/foundry.toml']),
                               ('agent-2', 'fe03df72a6dadb585451575c20866c57ad7c9d7f', ['protocol/hmbc_protocol', 'protocol/exports', 'protocol/testtools'])]:
        assert not git('diff', '--name-only', base, REFS[owner], '--', *paths)
    s = json.loads((P/'hmbc.schema.json').read_text())
    c = corrected_schema(s)
    Draft202012Validator.check_schema(c)
    checks = []
    def verdict(schema, name, value):
        return Draft202012Validator(schema | {'$ref': '#/$defs/'+name}).is_valid(value)
    def probe(label, name, value, before, after):
        actual = [verdict(s, name, value), verdict(c, name, value)]
        assert actual == [before, after], (label, actual)
        checks.append({'label': label, 'definition': name, 'candidate1': before, 'prospectiveCorrection': after})
    owner = json.loads((P/'d50-owner-vectors.json').read_text())
    for profile, vector in owner['documents'].items():
        value = vector['document']
        probe(profile+' positive binding', 'DeploymentBindingDocument', value, True, True)
        bad = copy.deepcopy(value); bad['profile']['enum'] = '4'
        probe(profile+' enum4', 'DeploymentBindingDocument', bad, True, False)
        bad = copy.deepcopy(value); bad['profile']['enum'] = '0' if profile == 'repaired-f' else '1'
        probe(profile+' name/enum mismatch', 'DeploymentBindingDocument', bad, True, False)
        bad = copy.deepcopy(value)
        witness_lists = bad['witnessSets']
        for field in witness_lists:
            bad2 = copy.deepcopy(bad)
            row = bad2['witnessSets'][field]
            row['witnesses'] = [row['witnesses'][0]]*2
            probe(profile+' duplicate '+field, 'DeploymentBindingDocument', bad2, True, False)
    examples = json.loads((P/'vectors/wire.json').read_text())['responses']
    for i, response in enumerate(examples):
        probe('wire positive '+str(i), 'AdapterResponse', response, True, True)
    for i, row in enumerate(json.loads((P/'vectors/success.json').read_text())):
        probe('success positive '+str(i), 'AdapterResponse', row['response'], True, True)
    collection = next((r.get('result') or r.get('error'))['collection'] for r in examples
        if 'timing' in (r.get('result') or r.get('error')).get('collection', {}))
    for field in ['recordedReports', 'inconsistentReports', 'lateReports']:
        bad = copy.deepcopy(collection);bad[field] = []
        probe('empty '+field, 'Collection', bad, True, False)
    adopted = {'message': json.loads((P/'vectors/signing.json').read_text())['vectors'][0]['typedData']['message'],
               'reporters': ['0', '1'], 'reproposal': 'sent'}
    for reporters in [['0', '0'], ['1', '0'], ['3', '2', '1']]:
        probe('invalid reporters '+str(reporters), 'AdoptedCheckpoint', adopted | {'reporters': reporters}, True, False)
    for n in [2, 3, 4]:
        for reporters in itertools.combinations(['0', '1', '2', '3'], n):
            probe('valid reporters '+str(reporters), 'AdoptedCheckpoint', adopted | {'reporters': list(reporters)}, True, True)
    fixture = c['$defs']['LedgerFixtureF']['properties']['governance']
    assert Draft202012Validator(fixture).is_valid({'maxGovernanceTtl': '120', 'maxAdmins': '8'})
    assert not Draft202012Validator(fixture).is_valid({'maxGovernanceTtl': '121', 'maxAdmins': '8'})
    assert c['$defs']['LedgerAbiEntry'] == json.loads((ROOT/'interfaces/v1/hmbc.schema.json').read_text())['$defs']['LedgerAbiEntry']
    assert s['$defs']['LedgerDeploymentE']['properties']['schemaVersion']['const'] == 'hmbc-ledger-deployment/v0'
    assert c['$defs']['LedgerDeploymentE']['properties']['schemaVersion']['const'] == 'hmbc-ledger-deployment/v2'
    # Isolate M3's cross-field constraint; these are fragments, not full manifests.
    constraint = c['$defs']['LedgerDeploymentF']['allOf'][0]
    for threshold, mask, valid in [('2', '0', True), ('2', '64', False), ('3', '0', True), ('3', '64', True)]:
        assert Draft202012Validator(constraint).is_valid({'mutations': mask, 'fixture': {'witnessSet': {'threshold': threshold}}}) == valid
    for name in ['GovernanceAction', 'CollectGovernanceInput']:
        gov = next(v['typedData']['message'] for v in json.loads((P/'vectors/signing.json').read_text())['vectors'] if v['name']=='GovernanceAction')
        probe(name+' zero admin', name, gov | {'admins': ['0x'+'00'*20]}, True, False)
    dump('input-provenance.json', provenance)
    dump('shape-checks.json', checks)
    dump('prospective-schema.json', c)
    print(json.dumps({'status': 'REVIEW_PROBES_PASS_NOT_MAPPING_ACK', 'pairedShapeChecks': len(checks),
        'additionalAssertions': 'governance bounds, preserved v1 entry, v2 carrier tag, four M3 constraints',
        'communicationPaths': len(communications), 'ownerManifests': provenance['ownerManifests'],
        'pending': 'Agent2 revision8 D50/wire/export layouts; renewed design ACKs; complete candidate2 mapping ACKs; separate F0 freeze',
        'limits': 'No peer helpers, Forge, runtime, services, F implementation, timing, or RQ gate run.'}, indent=2))


if __name__ == '__main__':
    run()
