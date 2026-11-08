"""Verify an immutable ACK receipt; no module execution or gate advancement."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REFS = {
    'agent-1': '5c95418394b2de9c1f3940567ae1066c6b64287e',
    'agent-2': 'dcad9745a594770654810ca366ed78c6e559539f',
    'agent-3': '5b6bb9d3d795c90aaf0041089ce345342d752d6f',
}
ACK = 'communication/agent-1/outbox/0109-ack-v2-candidate2-ledger-mapping.md'
MANIFEST = 'interfaces/proposals/v2-candidate2/MANIFEST.json'
DIGEST = '0d1a2be44666164deccf19c8c7e942b91938d7577fd6caba569837888b4143e9'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def blob(owner, path):
    return git('show', REFS[owner] + ':' + path)


def ancestor(a, b):
    result = subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], cwd=ROOT)
    assert result.returncode in (0, 1)
    return result.returncode == 0


def main():
    assert git('branch', '--show-current').decode().strip() == 'agent-3'
    manifest_blob = blob('agent-3', MANIFEST)
    assert sha(manifest_blob) == DIGEST
    assert (ROOT / MANIFEST).read_bytes() == manifest_blob
    manifest = json.loads(manifest_blob)
    assert manifest['mappingAcks'] == [] and manifest['freezeAck'] is None
    assert manifest['executionAuthorized'] is False
    for path, digest in (manifest['files'] | manifest['historicalBase']).items():
        expected = blob('agent-3', path)
        assert sha(expected) == digest and (ROOT / path).read_bytes() == expected, path
    pins = json.loads(blob('agent-3', 'interfaces/proposals/v2-candidate2/OWNER-PINS.json'))
    for path, digest in pins['files'].items():
        assert sha(git('show', pins['ownerCommit'] + ':' + path)) == digest, path
    assert sha(git('show', pins['ledgerCommit'] + ':ledger/f0/A-F1-DESIGN.md')) == pins['ledgerDesignSha256']
    ack_blob = blob('agent-1', ACK)
    ack = ack_blob.decode()
    for text in ['Message-ID: A1-0109', 'From: agent-1', 'Type: ACK',
                 'Responds-to: A3-0071', DIGEST, 'ledger producer/consumer scope',
                 'not** an F0 freeze ACK, a source READY or an execution ACK']:
        assert text in ack, text
    ack_change = git('log', '-1', '--format=%H', REFS['agent-1'], '--', ACK).decode().strip()
    assert ack_change == REFS['agent-1']
    prior_a1 = '8a943a7c64e881ac0686587f01a9ebfaf2368706'
    assert ancestor(prior_a1, REFS['agent-1'])
    changes = git('diff', '--name-only', prior_a1, REFS['agent-1']).decode().splitlines()
    assert set(changes) == {ACK, 'communication/agent-1/STATUS.md', 'communication/agent-1/HANDOFF.md'}
    assert not git('diff', prior_a1, REFS['agent-1'], '--', 'ledger')
    manifests = {}
    for owner, path in [
        ('agent-1', 'ledger/evidence/source-manifest.sha256'),
        ('agent-2', 'protocol/evidence/source-manifest.sha256'),
        ('agent-2', 'protocol/f0/MANIFEST.sha256'),
    ]:
        source = blob(owner, path)
        lines = source.decode().splitlines()
        for line in lines:
            digest, name = line.split(maxsplit=1)
            name = name.lstrip('*').removeprefix('./')
            assert sha(blob(owner, name)) == digest, name
        manifests[path] = {'commit': REFS[owner], 'sha256': sha(source), 'verifiedEntries': len(lines)}
    latest = {}
    for owner, commit in REFS.items():
        for path in git('ls-tree', '-r', '--name-only', commit, '--', 'communication').decode().splitlines():
            change = git('log', '-1', '--format=%H', commit, '--', path).decode().strip()
            row = {'observedCommit': commit, 'fileChangingCommit': change, 'sha256': sha(blob(owner, path))}
            old = latest.get(path)
            if old and old['sha256'] != row['sha256']:
                if ancestor(change, old['fileChangingCommit']):
                    continue
                assert ancestor(old['fileChangingCommit'], change), ('incomparable communication', path)
            latest[path] = row
    a2_outbox = git('ls-tree', '-r', '--name-only', REFS['agent-2'], '--', 'communication/agent-2/outbox').decode().splitlines()
    assert not any(Path(p).name[:4].isdigit() and int(Path(p).name[:4]) > 56 for p in a2_outbox)
    # Immutable proposal and historical/peer source stay untouched, including dirty bytes.
    protected = ['interfaces', 'ledger', 'protocol', 'archive',
                 'communication/agent-1', 'communication/agent-2']
    assert not git('diff', REFS['agent-3'], '--', *protected)
    provenance = {
        'observedAtUtc': datetime.now(timezone.utc).isoformat(),
        'classification': 'VERIFIED_MAPPING_ACK_RECEIPT_NOT_RUNTIME',
        'refs': REFS, 'candidateManifest': {'path': MANIFEST, 'sha256': DIGEST},
        'candidatePayloadFilesVerified': len(manifest['files']),
        'historicalBaseFilesVerified': len(manifest['historicalBase']),
        'mappingAcks': [{'messageId': 'A1-0109', 'path': ACK, 'sha256': sha(ack_blob),
                         'observedCommit': REFS['agent-1'], 'fileChangingCommit': ack_change,
                         'scope': 'ledger producer/consumer mapping/layout only',
                         'manifestSha256': DIGEST}],
        'protocolMappingAck': None, 'freezeAck': None, 'executionAuthorized': False,
        'agent1ChangedPaths': changes, 'ownerManifests': manifests,
        'latestCommunication': latest, 'incomparableConflicts': [],
        'tools': {'python': git_tool_version(['python3', '--version']),
                  'git': git_tool_version(['git', '--version'])},
        'limits': ['Owner-reported Forge 26 PASS was read, not rerun.',
                   'No runtime, Forge, TLC, RPC, signing or full suite executed.',
                   'Correlated same-model receipt review; no extra agents.',
                   'Proposal publication-time empty ACK fields remain immutable.'],
    }
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps({'status': 'ACK_RECEIPT_VERIFIED', 'candidatePayloadFiles': len(manifest['files']),
                      'historicalBaseFiles': len(manifest['historicalBase']),
                      'ownerManifestEntries': {p: v['verifiedEntries'] for p, v in manifests.items()},
                      'communicationPaths': len(latest), 'ackSha256': sha(ack_blob),
                      'protocolMappingAck': None, 'f0Frozen': False, 'executionAuthorized': False}, indent=2))


def git_tool_version(command):
    return subprocess.check_output(command, cwd=ROOT).decode().strip()


if __name__ == '__main__':
    main()
