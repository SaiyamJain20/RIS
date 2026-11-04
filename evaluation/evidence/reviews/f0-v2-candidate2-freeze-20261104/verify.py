"""Check exact mapping receipts and a pending F0 freeze; run no F experiment."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REFS = {'agent-1': '5c95418394b2de9c1f3940567ae1066c6b64287e',
        'agent-2': 'ac624b46f59b63151434e72bcbc4bb6109bb9db1',
        'agent-3': '5b6bb9d3d795c90aaf0041089ce345342d752d6f'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ancestor(a, b):
    result = subprocess.run(['git', 'merge-base', '--is-ancestor', a, b], cwd=ROOT)
    assert result.returncode in (0, 1)
    return result.returncode == 0


def main():
    path = 'communication/F0_FREEZE_CANDIDATE2.json'
    freeze_bytes = (ROOT / path).read_bytes()
    freeze = json.loads(freeze_bytes)
    assert sha(freeze_bytes) == (OUT / 'freeze-request.sha256').read_text().split()[0]
    assert freeze['status'] == 'REQUESTED_PENDING_BOTH_EXACT_OWNER_FREEZE_ACKS'
    assert freeze['freezeAcks'] == []
    assert not freeze['implementationAuthorized'] and not freeze['executionAuthorized']
    manifest_pin = freeze['candidateManifest']
    manifest_bytes = git('show', manifest_pin['commit'] + ':' + manifest_pin['path'])
    assert sha(manifest_bytes) == manifest_pin['sha256']
    manifest = json.loads(manifest_bytes)
    assert freeze['candidateFiles'] == manifest['files']
    assert freeze['historicalBase'] == manifest['historicalBase']
    for name, digest in (freeze['candidateFiles'] | freeze['historicalBase']).items():
        assert sha((ROOT / name).read_bytes()) == digest, name
        assert sha(git('show', REFS['agent-3'] + ':' + name)) == digest, name
    for ack in freeze['mappingAcks']:
        data = git('show', ack['commit'] + ':' + ack['path'])
        assert sha(data) == ack['sha256'] and manifest_pin['sha256'] in data.decode()
        assert 'Type: ACK' in data.decode() and ack['messageId'] in data.decode()
        assert ack['fileChangingCommit'] == git('log', '-1', '--format=%H', ack['commit'], '--', ack['path']).decode().strip()
        assert ancestor(ack['commit'], REFS['agent-1' if ack['messageId'].startswith('A1') else 'agent-2'])
    assert {a['messageId'] for a in freeze['mappingAcks']} == {'A1-0109', 'A2-0057'}
    for ack in freeze['candidate8DesignAcks']:
        assert sha(git('show', ack['commit'] + ':' + ack['path'])) == ack['sha256']
    owner = freeze['ownerInputs']
    for name, digest in owner['files'].items():
        assert sha(git('show', owner['ownerCommit'] + ':' + name)) == digest
    assert sha(git('show', owner['ledgerCommit'] + ':ledger/f0/A-F1-DESIGN.md')) == owner['ledgerDesignSha256']
    assert len(freeze['explicitLayoutPins']) == 5
    assert all(freeze['protocolF0Files'][p] == d for p, d in freeze['explicitLayoutPins'].items())
    counts = {}
    for agent, name, relative in [
        ('agent-1', 'ledger/evidence/source-manifest.sha256', ''),
        ('agent-2', 'protocol/evidence/source-manifest.sha256', ''),
        ('agent-2', 'protocol/f0/MANIFEST.sha256', ''),
        ('agent-2', 'protocol/v2-review/candidate2/MANIFEST.sha256', 'protocol/v2-review/candidate2/'),
    ]:
        raw = git('show', REFS[agent] + ':' + name)
        rows = {}
        for line in raw.decode().splitlines():
            digest, filename = line.split(maxsplit=1)
            filename = relative + filename.lstrip('*').removeprefix('./')
            assert sha(git('show', REFS[agent] + ':' + filename)) == digest, filename
            rows[filename] = digest
        counts[name] = {'sha256': sha(raw), 'verifiedEntries': len(rows)}
        if name == 'protocol/f0/MANIFEST.sha256':
            assert rows == freeze['protocolF0Files']
    assert counts['protocol/v2-review/candidate2/MANIFEST.sha256']['sha256'] == '4f13146391bbac0a8deb877844e1ea68ec5ca70602726ba69c9593f41e3b525b'
    previous = 'dcad9745a594770654810ca366ed78c6e559539f'
    changed = git('diff', '--name-only', previous, REFS['agent-2']).decode().splitlines()
    assert all(p.startswith('protocol/v2-review/candidate2/') or p in [
        'communication/agent-2/STATUS.md', 'communication/agent-2/HANDOFF.md',
        'communication/agent-2/outbox/0057-ack-v2-candidate2-protocol-mapping-layout.md'] for p in changed)
    matrix = json.loads((ROOT / 'evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json').read_text())
    assert len(matrix['cases']) == 32 and all(c['executionStatus'] == 'NOT_RUN' for c in matrix['cases'])
    assert freeze['caseIds'] == [c['id'] for c in matrix['cases']]
    assert freeze['numericPlan'] == {k: v for k, v in matrix['numericPlan'].items() if k not in ['status', 'actualTimings']}
    latest = {}
    for commit in REFS.values():
        for name in git('ls-tree', '-r', '--name-only', commit, '--', 'communication').decode().splitlines():
            change = git('log', '-1', '--format=%H', commit, '--', name).decode().strip()
            row = {'observedCommit': commit, 'fileChangingCommit': change,
                   'sha256': sha(git('show', commit + ':' + name))}
            old = latest.get(name)
            if old and old['sha256'] != row['sha256']:
                if ancestor(change, old['fileChangingCommit']):
                    continue
                assert ancestor(old['fileChangingCommit'], change), name
            latest[name] = row
    assert not git('diff', REFS['agent-3'], '--', 'interfaces', 'ledger', 'protocol', 'archive',
                   'communication/agent-1', 'communication/agent-2')
    result = {'status': 'BOTH_MAPPING_ACKS_AND_PENDING_FREEZE_VERIFIED',
              'capturedUtc': datetime.now(timezone.utc).isoformat(), 'refs': REFS,
              'freezeRequestSha256': sha(freeze_bytes), 'mappingAcks': freeze['mappingAcks'],
              'ownerManifests': counts, 'latestCommunication': latest,
              'incomparableConflicts': [], 'caseCount': 32, 'caseResults': 'ALL_NOT_RUN',
              'implementationAuthorized': False, 'executionAuthorized': False, 'freezeAcks': []}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'latestCommunication'}, indent=2))
    print('Latest communication paths:', len(latest))


if __name__ == '__main__':
    main()
