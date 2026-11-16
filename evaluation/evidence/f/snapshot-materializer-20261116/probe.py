"""Reproduce synthetic preparation and refusal; never execute owner code."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from evaluation.f_snapshot import (inventory_runtime, materialize_snapshot,
                                 verify_runtime_inventory, verify_snapshot)
from evaluation.manifests import canonical_hash, sha256


def main():
    evidence = Path(__file__).resolve().parent
    commands = []
    with tempfile.TemporaryDirectory(prefix='hmbc-snapshot-fixture-') as scratch:
        root = Path(scratch)
        repo = root / 'synthetic-repository'
        repo.mkdir()
        def git(*args):
            row = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True)
            commands.append({'argv': ['git', '-C', str(repo), *args], 'exitCode': row.returncode,
                             'stdoutSha256': hashlib.sha256(row.stdout).hexdigest(),
                             'stderrSha256': hashlib.sha256(row.stderr).hexdigest()})
            return row.stdout
        git('init', '-q', '--template=')
        git('config', 'user.name', 'Synthetic fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        (repo / 'protocol').mkdir()
        (repo / 'protocol/input.txt').write_text('synthetic current input\n')
        (repo / 'old.txt').write_text('synthetic historical input\n')
        git('add', 'protocol/input.txt', 'old.txt')
        git('commit', '-qm', 'synthetic historical fixture')
        old = git('rev-parse', 'HEAD').decode().strip()
        old_archive = hashlib.sha256(git('archive', old)).hexdigest()
        (repo / 'old.txt').unlink()
        git('add', 'old.txt')
        git('commit', '-qm', 'synthetic current fixture')
        current = git('rev-parse', 'HEAD').decode().strip()
        archive = git('archive', current, 'protocol')
        plan = {'schemaVersion': 'hmbc-f-snapshot-plan/v1',
            'git': {'path': shutil.which('git'), 'sha256': sha256(shutil.which('git'))},
            'sources': [{'commit': current, 'paths': ['protocol'],
                         'archiveSha256': hashlib.sha256(archive).hexdigest()}],
            'sourceFiles': {'protocol/input.txt': sha256(repo / 'protocol/input.txt')},
            'requiredGitCommits': [old]}
        prepared = materialize_snapshot(repo, root / 'prepared', plan,
                                        expected_plan_sha256=canonical_hash(plan))
        assert prepared['status'] == 'PREPARED', prepared
        repo.rename(root / 'origin-moved')
        assert verify_snapshot(prepared, expected_manifest_sha256=canonical_hash(prepared))
        historical = next(row for row in prepared['gitCommits'] if row['commit'] == old)
        assert historical['archiveSha256'] == old_archive
        bad = copy.deepcopy(plan)
        bad['sourceFiles']['protocol/input.txt'] = '0' * 64
        blocked = materialize_snapshot(root / 'origin-moved', root / 'blocked', bad,
                                        expected_plan_sha256=canonical_hash(bad))
        assert blocked['status'] == 'BLOCKED'
        runtime = root / 'runtime'
        runtime.mkdir()
        library = runtime / 'library'
        library.write_bytes(b'synthetic runtime library')
        tool = root / 'tool'
        tool.symlink_to(library)
        observed = inventory_runtime(tools={'synthetic': str(tool)}, roots=[runtime])
        assert verify_runtime_inventory(observed, expected_inventory_sha256=canonical_hash(observed))
        library.write_bytes(b'drift')
        try:
            verify_runtime_inventory(observed, expected_inventory_sha256=canonical_hash(observed))
        except ValueError:
            drift_refused = True
        else:
            raise AssertionError('Runtime drift was not detected')
        summary = {'classification': 'tested reconstruction result; synthetic inputs only',
            'snapshot': prepared['status'], 'originalRepositoryMoved': True,
            'historicalArchiveMatches': True, 'wrongSource': blocked['status'],
            'runtimeDriftRefused': drift_refused, 'closureEstablished': False,
            'executionAuthorized': False, 'gateF': 'NOT_RUN',
            'note': 'Temporary source/object/runtime trees removed after verified probe; manifests retained, rerun this script to reproduce.'}
        for name, data in [('sample-plan.json', plan), ('sample-prepared.json', prepared),
                           ('sample-blocked.json', blocked), ('sample-runtime.json', observed),
                           ('sample-summary.json', summary), ('sample-commands.json', commands)]:
            (evidence / name).write_text(json.dumps(data, indent=2) + '\n')
        print(json.dumps(summary))


if __name__ == '__main__':
    main()
