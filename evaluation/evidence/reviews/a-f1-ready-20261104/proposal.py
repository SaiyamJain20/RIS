"""Materialize and verify an additive carrier proposal; never change published bytes."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from jsonschema import Draft202012Validator
from evaluation.schema_v2 import FORMATS

OUT = Path(__file__).resolve().parent
PROPOSAL = ROOT / 'interfaces/proposals/v2-e-source-closure'
SOURCE = 'aef3daa5ebbe434f97b016719f8762d4aaf09441'
BASE_HASH = '79e34dbb8f9b11b310decf416d27a57aa8c1f249e0c5a6d3985e52740376c093'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    if path.exists():
        assert path.read_bytes() == raw, f'Refuse to change existing proposal bytes: {path}'
    else:
        path.write_bytes(raw)


def owner_json(path):
    return json.loads(subprocess.check_output(['git', 'show', SOURCE + ':' + path], cwd=ROOT))


def main():
    raw = (ROOT / 'interfaces/v2/hmbc.schema.json').read_bytes()
    assert sha(raw) == BASE_HASH
    base = json.loads(raw)
    new_carrier = deepcopy(base['$defs']['LedgerDeploymentE'])
    new_carrier['properties']['schemaVersion'] = {'const': 'hmbc-ledger-deployment/v2.1'}
    new_carrier['properties']['sources'] = {'$ref': '#/$defs/LedgerSourceHashesF'}
    operations = [
        {'op': 'add', 'path': '/$defs/LedgerDeploymentEComplete', 'value': new_carrier},
        {'op': 'add', 'path': '/$defs/LedgerDeployment/oneOf/-',
         'value': {'$ref': '#/$defs/LedgerDeploymentEComplete'}}]
    amendment = {'format': 'RIS-interface-amendment-proposal-1', 'status': 'PROPOSED_NO_ACK',
        'basePath': 'interfaces/v2/hmbc.schema.json', 'baseSha256': BASE_HASH,
        'ownerSourceCommit': SOURCE, 'operations': operations,
        'publicationRequires': ['exact Agent1 ACK', 'exact Agent2 ACK', 'separate successor freeze'],
        'defaultV1ChangeAuthorized': False, 'executionAuthorized': False}
    proposed = deepcopy(base)
    proposed['$defs']['LedgerDeploymentEComplete'] = new_carrier
    proposed['$defs']['LedgerDeployment']['oneOf'].append(operations[1]['value'])
    Draft202012Validator.check_schema(proposed)
    for key, definition in base['$defs'].items():
        if key != 'LedgerDeployment':
            assert definition == proposed['$defs'][key], key
    assert proposed['$defs']['LedgerDeployment']['oneOf'][:-1] == base['$defs']['LedgerDeployment']['oneOf']
    original = owner_json('ledger/evidence/af1/slice6-smoke/e-successor/deployment-v2.json')
    complete = deepcopy(original)
    complete['schemaVersion'] = 'hmbc-ledger-deployment/v2.1'
    complete['sources'] = owner_json('ledger/exports/abi/manifest-v2.json')['sources']
    assert len(original['sources']) == 10 and len(complete['sources']) == 12

    def valid(schema, value):
        rule = {'$ref': '#/$defs/LedgerDeployment', '$defs': schema['$defs']}
        return Draft202012Validator(rule, format_checker=FORMATS).is_valid(value)

    cases = []
    def check(name, value, expected_base, expected_proposal):
        got = (valid(base, value), valid(proposed, value))
        assert got == (expected_base, expected_proposal), (name, got)
        cases.append({'name': name, 'acceptedBase': got[0], 'proposed': got[1]})

    check('historical successor E retained', original, True, True)
    check('new explicit marker with complete inventory', complete, False, True)
    old_marker_full_map = deepcopy(complete)
    old_marker_full_map['schemaVersion'] = original['schemaVersion']
    check('do not silently expand old marker', old_marker_full_map, False, False)
    new_marker_old_map = deepcopy(complete)
    new_marker_old_map['sources'] = original['sources']
    check('new marker cannot omit new inputs', new_marker_old_map, False, False)
    for path in complete['sources']:
        changed = deepcopy(complete)
        del changed['sources'][path]
        check('missing source ' + path, changed, False, False)
    for path in ('src/Governance.sol', 'src/interfaces/IPolicyVersion.sol'):
        changed = deepcopy(complete)
        changed['sources'][path] = 'not-a-hash'
        check('malformed source hash ' + path, changed, False, False)
    changed = deepcopy(complete)
    changed['sources']['src/unreviewed.sol'] = '0' * 64
    check('unreviewed extra source rejected', changed, False, False)
    for profile in ('f-base', 'f-q2', 'f-bit7'):
        f = owner_json(f'ledger/evidence/af1/slice6-smoke/{profile}/deployment.json')
        check('F carrier unchanged ' + profile, f, True, True)
    changed = deepcopy(complete)
    changed['interfaceVersion'] = 'v2.1'
    check('wire family remains v2', changed, False, False)
    dump(PROPOSAL / 'AMENDMENT.json', amendment)
    dump(PROPOSAL / 'e-complete-example.json', complete)
    files = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(PROPOSAL.iterdir())
             if p.name != 'MANIFEST.json' and p.is_file()}
    dump(PROPOSAL / 'MANIFEST.json', {'format': 'RIS-proposal-manifest-1',
        'status': 'PROPOSED_NO_ACK', 'baseSha256': BASE_HASH, 'files': files,
        'implementationAuthorized': False, 'executionAuthorized': False})
    result = {'capturedUtc': datetime.now(timezone.utc).isoformat(), 'cases': cases,
        'unchangedOriginalDefinitions': len(base['$defs']) - 1,
        'baseUnchanged': sha((ROOT / 'interfaces/v2/hmbc.schema.json').read_bytes()) == BASE_HASH,
        'manifestSha256': sha((PROPOSAL / 'MANIFEST.json').read_bytes()),
        'sourceCommit': SOURCE, 'newCarrierPublished': False, 'peerAcks': [],
        'scope': 'offline structural proposal checks; no new cryptographic or runtime result'}
    (OUT / 'proposal-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
