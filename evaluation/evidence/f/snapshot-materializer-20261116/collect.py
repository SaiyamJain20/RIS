"""Collect offline provenance and audit peer attachment bytes; execute no suites."""
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from evaluation.manifests import canonical_hash, now, sha256


def main():
    evidence = Path(__file__).resolve().parent
    root = evidence.parents[3]
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root)
    refs = {name: git('rev-parse', 'origin/' + name).decode().strip()
            for name in ('agent-1', 'agent-2', 'agent-3')}
    peer = refs['agent-1']
    prefix = 'communication/agent-1/outbox/0144-attachments/'
    checksum_path = prefix + 'SHA256SUMS'
    sums = git('show', peer + ':' + checksum_path).decode()
    verified = []
    for line in sums.splitlines():
        if not line.strip(): continue
        expected, path = line.split(maxsplit=1)
        path = path.lstrip('*')
        payload = git('show', peer + ':' + path)
        actual = hashlib.sha256(payload).hexdigest()
        assert expected == actual, path
        verified.append({'path': path, 'sha256': actual})
    note_path = 'communication/agent-1/outbox/0144-note-a3-0162-ledger-baseline-recipe-checked.md'
    note = git('show', peer + ':' + note_path)
    (evidence / 'a1-0144-audit.json').write_text(json.dumps({
        'publicationRef': 'origin/agent-1', 'publicationCommit': peer,
        'notePath': note_path, 'noteSha256': hashlib.sha256(note).hexdigest(),
        'noteLastChangingCommit': git('log', '-1', '--format=%H', peer, '--', note_path).decode().strip(),
        'attachments': verified, 'attachmentCount': len(verified),
        'localOwnerCommandsExecuted': False, 'freezeAck': False,
        'interpretation': 'Peer command/output and post-check evidence only. Existing executor already excludes ledger/out and ledger/cache.'}, indent=2) + '\n')
    original = json.loads((evidence.parent / 'baseline-executor-20261116/owner-recipe-draft.json').read_text())
    draft = {'schemaVersion': 'hmbc-f-snapshot-plan/v1', 'status': 'DRAFT',
        'authorizesExecution': False, 'git': original['tools']['git'],
        'sources': original['sourceProvenance'], 'sourceFiles': original['sourceFiles'],
        'requiredGitCommits': ['91add8cc6000d1413bad2ed0aa119a5f26e8c776', '9d6911d9a35c7d20b3e0226400f8f0fcc99ef256'],
        'blockers': ['Not materialized against real owner sources in this receipt',
                     'Runtime closure and recipe/coordinator wiring incomplete',
                     'Exact executable FREEZE and owner ACKs required before owner suites/services/cases']}
    protocol_pin = next(row['commit'] for row in draft['sources'] if row['paths'] == ['protocol'])
    historical_pins = {}
    for path, constant, commit in [('protocol/tests/conftest.py', 'LEDGER_COMMIT', draft['requiredGitCommits'][0]),
        ('protocol/tests/test_peer_bootstrap_crosscheck.py', 'PEER_COMMIT', draft['requiredGitCommits'][1])]:
        payload = git('show', protocol_pin + ':' + path)
        assert (constant + ' = "' + commit + '"').encode() in payload
        historical_pins[path] = {'sourceCommit': protocol_pin, 'sha256': hashlib.sha256(payload).hexdigest(), 'requiredCommit': commit}
    (evidence / 'snapshot-plan-draft.json').write_text(json.dumps(draft, indent=2) + '\n')
    pinned_paths = ['evaluation/reports/RQ2-F-DRAFT.md',
        'evaluation/evidence/f/partial-report-packet-20261115/README.md',
        'evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json']
    identities = {}
    for path in pinned_paths:
        payload = (root / path).read_bytes()
        assert payload == git('show', refs['agent-3'] + ':' + path)
        identities[path] = hashlib.sha256(payload).hexdigest()
    plan = json.loads((root / pinned_paths[-1]).read_text())
    assert plan['status'] == 'DRAFT' and plan['authorizesExecution'] is False
    ids = [case for family in plan['families'].values() for case in family['cases']]
    assert len(ids) == len(set(ids)) == 32
    versions = {}
    for name, argv in [('python', [sys.executable, '--version']), ('pytest', [sys.executable, '-m', 'pytest', '--version']), ('git', ['git', '--version'])]:
        row = subprocess.run(argv, capture_output=True, text=True, check=True)
        versions[name] = {'argv': argv, 'exitCode': row.returncode, 'stdout': row.stdout.strip(), 'stderr': row.stderr.strip()}
    inputs = sorted({*[(root / path) for path in (evidence.parent / 'baseline-executor-20261116/source-inputs.sha256').read_text().splitlines()
                      for path in [path.split(maxsplit=1)[1]] if (root / path).is_file()],
                     root / 'evaluation/f_snapshot.py', root / 'evaluation/tests/test_f_snapshot.py',
                     evidence / 'probe.py', evidence / 'collect.py', evidence / 'PLAN.md'})
    (evidence / 'source-inputs.sha256').write_text(''.join(sha256(path) + '  ' + path.relative_to(root).as_posix() + '\n' for path in inputs))
    compressed = []
    for name in ['red.txt', 'green-initial.txt', 'review-red.txt', 'root-review-red.txt', 'focused-final.txt']:
        path = evidence / name
        if not path.exists(): continue
        payload = path.read_bytes()
        (evidence / (name + '.gz')).write_bytes(gzip.compress(payload, mtime=0))
        compressed.append({'path': name + '.gz', 'rawSha256': hashlib.sha256(payload).hexdigest()})
        path.unlink()
    if compressed:
        (evidence / 'compressed-logs.json').write_text(json.dumps(compressed, indent=2) + '\n')
    audit = {'collectedAt': now(), 'parent': git('rev-parse', 'HEAD').decode().strip(),
        'refs': refs, 'versions': versions, 'platform': platform.platform(),
        'snapshotPlanSha256': canonical_hash(draft), 'snapshotPlanExecuted': False,
        'proposedSourceFiles': len(draft['sourceFiles']), 'historicalPinEvidence': historical_pins,
        'preservedArtifacts': identities, 'selectedSourceInputs': len(inputs),
        'review': 'same-author self-review; correlated, no independent reviewer',
        'gateF': 'NOT_RUN', 'caseCount': 32, 'gateG': 'LOCKED', 'executionAuthorized': False}
    (evidence / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
