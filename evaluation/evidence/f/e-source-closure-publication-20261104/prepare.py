"""Materialize the exact ACKed amendment; do not touch accepted publication bytes."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PROPOSAL = 'interfaces/proposals/v2-e-source-closure'
PROPOSAL_HASH = '7810ad105330de73920450d82f4850ebb6de0846396e5bb786818e700e49bb0a'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    provenance = json.loads((OUT / 'communication-provenance.json').read_text())
    assert not provenance['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
    manifest = ROOT / PROPOSAL / 'MANIFEST.json'
    assert sha(manifest.read_bytes()) == PROPOSAL_HASH
    for path, digest in json.loads(manifest.read_text())['files'].items():
        assert sha((ROOT / path).read_bytes()) == digest, path
    amendment = json.loads((ROOT / PROPOSAL / 'AMENDMENT.json').read_text())
    base = ROOT / amendment['basePath']
    assert sha(base.read_bytes()) == amendment['baseSha256']
    accepted = json.loads((ROOT / 'interfaces/v2/FREEZE.json').read_text())
    for path, pin in accepted['files'].items():
        assert sha((ROOT / path).read_bytes()) == pin['sha256'], path
    f0 = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    for path, digest in f0['protocolF0Files'].items():
        assert sha(git('show', provenance['branches']['origin/agent-2'] + ':' + path)) == digest, path
    acks = []
    for owner, number, scope in [('agent-1', '0114', 'ledger producer'),
                                  ('agent-2', '0060', 'protocol producer/consumer')]:
        path, = [p for p in provenance['files'] if p.startswith(f'communication/{owner}/outbox/{number}-')]
        row = provenance['files'][path]
        ref = provenance['branches']['origin/' + owner]
        raw = git('show', ref + ':' + path)
        assert sha(raw) == row['sha256']
        text = raw.decode()
        message_id = 'A' + owner[-1] + '-' + number
        assert f'Message-ID: {message_id}\n' in text and '\nType: ACK\n' in text
        assert 'A3-0078' in text and PROPOSAL_HASH in text
        assert 'hmbc-ledger-deployment/v2.1' in text
        assert subprocess.run(['git', 'merge-base', '--is-ancestor', row['changeCommit'], ref], cwd=ROOT).returncode == 0
        acks.append({'owner': owner, 'messageId': message_id, 'path': path,
                     'commit': ref, 'fileChangingCommit': row['changeCommit'],
                     'sha256': sha(raw), 'scope': scope + ' amendment proposal only'})
    # Fixed exact patch: no opportunistic annotation changes, marker renames or
    # other edits beyond what both owners reviewed.
    document = json.loads(base.read_text())
    target = copy.deepcopy(document)
    first, second = amendment['operations']
    assert first['op'] == second['op'] == 'add'
    assert first['path'] == '/$defs/LedgerDeploymentEComplete'
    assert second['path'] == '/$defs/LedgerDeployment/oneOf/-'
    assert 'LedgerDeploymentEComplete' not in target['$defs']
    target['$defs']['LedgerDeploymentEComplete'] = first['value']
    target['$defs']['LedgerDeployment']['oneOf'].append(second['value'])
    destination = ROOT / 'interfaces/v2.1'
    destination.mkdir(exist_ok=True)
    schema_path = destination / 'hmbc.schema.json'
    assert not schema_path.exists(), 'Do not overwrite a successor publication'
    dump(schema_path, target)
    receipt_path = ROOT / 'communication/E_SOURCE_CLOSURE_ACCEPTANCE.json'
    dump(receipt_path, {
        'format': 'RIS-interface-amendment-acceptance-1',
        'status': 'ACCEPTED_FOR_SEPARATE_SUCCESSOR_PUBLICATION',
        'acceptedUtc': datetime.now(timezone.utc).isoformat(),
        'proposal': {'commit': git('rev-parse', 'HEAD').decode().strip(),
                     'path': str(manifest.relative_to(ROOT)), 'sha256': PROPOSAL_HASH},
        'proposalAcks': acks,
        'publicationMappingAcks': [],
        'migrationPolicy': 'Opt-in E F-tree successor uses v2.1 marker and twelve sources; wire family v2. '
                           'Old ten-source E is historical compatibility only. Default v1 and F unchanged.',
        'sourceReadyRequired': True, 'executionAuthorized': False,
        'note': 'Proposal ACKs verified; no completed exporter/consumer migration, publication receipt ACK or run ACK inferred.'})
    # The README is written before this helper; freeze it with the exact schema.
    dump(destination / 'FREEZE.json', {
        'format': 'RIS-interface-successor-publication-1',
        'schemaRevision': 'v2.1', 'interfaceVersion': 'v2',
        'status': 'PUBLISHED_FOR_OWNED_OPT_IN_MIGRATION',
        'acceptance': {'path': str(receipt_path.relative_to(ROOT)), 'sha256': sha(receipt_path.read_bytes())},
        'baseFreeze': {'path': 'interfaces/v2/FREEZE.json', 'sha256': sha((ROOT / 'interfaces/v2/FREEZE.json').read_bytes())},
        'baseSchema': {'path': amendment['basePath'], 'sha256': amendment['baseSha256']},
        'amendment': {'path': str(manifest.relative_to(ROOT)), 'sha256': PROPOSAL_HASH},
        'files': {str(p.relative_to(ROOT)): {'sha256': sha(p.read_bytes())}
                  for p in [schema_path, destination / 'README.md']},
        'inheritedPayloads': {p: pin['sha256'] for p, pin in accepted['files'].items()
                              if p != amendment['basePath']},
        'implementationAuthorized': True, 'executionAuthorized': False,
        'note': 'Exact semantic application of the two ACKed add operations. Original v2/v1 and proposal bytes immutable. '
                'Both owners must receipt this publication and publish changed source READY/mapping artifacts before integrated execution.'})
    print(json.dumps({'proposalAcks': acks, 'schemaSha256': sha(schema_path.read_bytes()),
                      'freezeSha256': sha((destination / 'FREEZE.json').read_bytes()),
                      'unchangedDefinitions': len(document['$defs']) - 1}, indent=2))


if __name__ == '__main__':
    main()
