"""Reproduce the exact A1-0111 handoff in disposable scratch; no services."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import re
from collections import Counter
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.manifests import record_command
from evaluation.peers import scan
from evaluation.schema_v2 import validate

SOURCE = 'aef3daa5ebbe434f97b016719f8762d4aaf09441'
MANIFEST = '6358359e35771ac2f3a6041148ee28a5ae8c979fde657406db16515d09e1c0a0'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def command(label, argv, cwd, env=None, required=True):
    log = OUT / (label + '.txt')
    if log.exists():
        rows = json.loads((OUT / 'commands.json').read_text())
        row, = [r for r in rows if r['log'] == str(log.relative_to(ROOT))]
        assert row['argv'] == argv and row['cwd'] == str(cwd)
        assert sha(log.read_bytes()) == row['outputSha256'] and row['exitCode'] == 0
        print(label, 'reuse verified same-run log', flush=True)
        return log.read_text()
    row = record_command(argv, cwd, log, timeout=900, **({'env': env} if env else {}))
    rows = json.loads((OUT / 'commands.json').read_text()) if (OUT / 'commands.json').exists() else []
    rows.append(row | {'log': str(log.relative_to(ROOT))})
    write('commands.json', rows)
    print(label, row['exitCode'], row['elapsedSeconds'], flush=True)
    if required:
        assert row['exitCode'] == 0, label
    return log.read_text()


def main():
    scratch = Path(sys.argv[1]).resolve()
    resume = len(sys.argv) == 3 and sys.argv[2] == '--resume'
    assert resume == scratch.exists(), 'Use a new path, or explicit same-run --resume'
    scratch.mkdir(parents=True, exist_ok=resume)
    provenance = scan(ROOT)
    write('communication-provenance.json', provenance)
    assert not provenance['missingBranches']
    assert not {p: r for p, r in provenance['files'].items() if r['ambiguous'] or r['divergentRevisions']}
    messages = {}
    for owner, numbers in [('agent-1', ('0111', '0112', '0113')), ('agent-2', ('0059',))]:
        ref = provenance['branches']['origin/' + owner]
        for number in numbers:
            path, = [p for p in provenance['files'] if p.startswith(f'communication/{owner}/outbox/{number}-')]
            row = provenance['files'][path]
            messages[owner + '-' + number] = {'path': path, 'observedCommit': ref,
                'fileChangingCommit': row['changeCommit'], 'sha256': sha(git('show', ref + ':' + path))}
    raw = git('show', SOURCE + ':ledger/evidence/source-manifest.sha256')
    assert sha(raw) == MANIFEST
    entries = {}
    for line in raw.decode().splitlines():
        digest, path = line.split(maxsplit=1)
        path = path.lstrip('*').removeprefix('./')
        assert path.startswith('ledger/') and '..' not in Path(path).parts
        assert sha(git('show', SOURCE + ':' + path)) == digest, path
        entries[path] = digest
    paths = set(git('ls-tree', '-r', '--name-only', SOURCE, 'ledger/').decode().splitlines())
    assert set(entries) == paths - {'ledger/evidence/source-manifest.sha256'}
    publication = json.loads((ROOT / 'interfaces/v2/FREEZE.json').read_text())
    for path, pin in publication['files'].items():
        assert sha((ROOT / path).read_bytes()) == pin['sha256']
    accepted = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    for path, digest in accepted['protocolF0Files'].items():
        assert sha(git('show', provenance['branches']['origin/agent-2'] + ':' + path)) == digest
    # Archive extraction is limited to this pinned tree into a fresh task-owned directory.
    if not resume:
        with tarfile.open(fileobj=io.BytesIO(git('archive', SOURCE, 'ledger'))) as archive:
            archive.extractall(scratch, filter='data')
    assert all(sha((scratch / p).read_bytes()) == d for p, d in entries.items())
    tools = json.loads((ROOT / 'evaluation/toolchain.json').read_text())
    binaries = {name: spec for name, spec in tools['foundry']['binaryPaths'].items()}
    binaries['solc'] = {k: tools['solc'][k] for k in ('path', 'sha256')}
    for spec in binaries.values():
        assert sha(Path(spec['path']).read_bytes()) == spec['sha256']
    env = dict(os.environ, PATH=str(Path(binaries['forge']['path']).parent) + os.pathsep + os.environ['PATH'],
               FOUNDRY_SOLC=binaries['solc']['path'], FOUNDRY_OFFLINE='true')
    write('inputs.json', {'capturedUtc': datetime.now(timezone.utc).isoformat(), 'source': SOURCE,
        'manifestSha256': MANIFEST, 'entries': entries, 'messages': messages,
        'remoteRefs': provenance['branches'], 'tools': binaries, 'scratch': str(scratch),
        'execution': 'isolated Forge only; no chains or integrated scenarios'})
    command('forge-version', [binaries['forge']['path'], '--version'], scratch)
    full = command('forge-tests', [binaries['forge']['path'], 'test', '--root', 'ledger'], scratch, env)
    assert '316 tests passed, 0 failed, 0 skipped' in full
    baseline = (scratch / 'ledger/evidence/af1/baseline-198-pass-list.txt').read_text().splitlines()
    passed = re.findall(r'^\[PASS\] (\w+)\(', full, re.MULTILINE)
    baseline_names = [re.search(r'\[PASS\] (\w+)\(', line).group(1) for line in baseline]
    assert len(baseline_names) == 198 and not (Counter(baseline_names) - Counter(passed))
    command('mutants', [sys.executable, '-I', 'ledger/tools/check_mutants.py', str(OUT / 'mutants.json')], scratch, env)
    command('controls', ['bash', 'ledger/tools/af1_controls.sh', str(scratch / 'controls')], scratch, env)
    vectors = command('generate-vectors', [sys.executable, '-I', 'ledger/tools/gen_v2_vector_test.py',
                       '--implemented', str(ROOT / 'interfaces/v2')], scratch, env)
    (scratch / 'ledger/test/V2VectorsReview.t.sol').write_text(vectors)
    mapped = command('mapping-tests', [binaries['forge']['path'], 'test', '--root', 'ledger',
                     '--match-path', 'test/V2VectorsReview.t.sol'], scratch, env)
    assert '26 tests passed, 0 failed, 0 skipped' in mapped
    # Default/successor exporters may write scratch only. Compare every original tracked input afterwards.
    command('export-default', [sys.executable, '-I', 'ledger/tools/export_abi.py'], scratch, env)
    command('export-successor', [sys.executable, '-I', 'ledger/tools/export_abi.py', '--successor'], scratch, env)
    unchanged = {p: d for p, d in entries.items() if sha((scratch / p).read_bytes()) == d}
    changed = sorted(set(entries) - set(unchanged))
    assert not changed, changed
    smoke = scratch / 'ledger/evidence/af1/slice6-smoke'
    deployments = sorted(smoke / p / 'deployment.json' for p in ('f-base', 'f-q2', 'f-bit7'))
    deployments.append(smoke / 'e-successor/deployment-v2.json')
    assert len(deployments) == 4
    for path in deployments:
        validate('LedgerDeployment', json.loads(path.read_text()))
    command('compiled-manifests', [sys.executable, '-I', 'ledger/tools/check_successor_export.py',
        '--schema', str(ROOT / 'interfaces/v2/hmbc.schema.json'), *map(str, deployments)], scratch, env)
    # Native Solidity compilation metadata exposes the missing KSSC import independently of owner prose.
    kssc = json.loads((scratch / 'ledger/out/KSSC.sol/KSSC.json').read_text())
    metadata = kssc.get('metadata') or kssc['rawMetadata']
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    e_sources = set(json.loads((scratch / 'ledger/exports/abi/manifest.json').read_text())['sources'])
    f_sources = set(json.loads((scratch / 'ledger/exports/abi/manifest-v2.json').read_text())['sources'])
    missing = sorted(set(metadata['sources']) - e_sources)
    assert missing == ['src/interfaces/IPolicyVersion.sol'], missing
    assert set(metadata['sources']) <= f_sources
    result = {'capturedUtc': datetime.now(timezone.utc).isoformat(), 'source': SOURCE,
        'manifestEntriesVerified': len(entries), 'scratchOriginalEntriesUnchanged': len(unchanged),
        'communicationPaths': len(provenance['files']), 'communicationConflicts': [],
        'publishedPayloadsVerified': len(publication['files']), 'protocolF0PinsVerified': len(accepted['protocolF0Files']),
        'forgeTests': 316, 'baselinePassNameMultiplicityRetained': 198,
        'mappingTests': 26, 'mutationSuites': 12, 'sensitivityControls': 13,
        'successorManifests': len(deployments), 'eSourceMapMissingKsscCompileInputs': missing,
        'fSourceMapCoversKsscCompileInputs': True, 'sourceReadyReview': 'REVIEWED_WITH_E_PROVENANCE_LIMIT',
        'protocolSourceReady': False, 'integratedExecution': False, 'Fgate': 'NOT_RUN', 'G': 'LOCKED',
        'limits': ['correlated model review', 'no RPC/live M4 replay', 'no integrated E regression',
                   'no timing or independent-host claim', 'owner NOTE messages are not ACKs']}
    write('verification.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
