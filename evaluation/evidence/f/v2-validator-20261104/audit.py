"""Pin local test inputs and verify fetched owner evidence without executing it."""
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def inputs():
    paths = []
    for folder in ['evaluation', 'interfaces']:
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and
                     'runs' not in p.relative_to(ROOT).parts and
                     '__pycache__' not in p.parts and
                     (p.suffix in ('.py', '.json', '.csv', '.pv', '.tla', '.cfg') and
                      'evidence' not in p.relative_to(ROOT).parts))
    paths.extend(ROOT / p for p in ['pyproject.toml', 'uv.lock', 'AGENTS.md', 'SPEC.md',
        'PLAN.md', 'communication/F0_ACCEPTANCE_CANDIDATE2.json', 'interfaces/v2/FREEZE.json'])
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(set(paths))}


def peers():
    provenance = json.loads((OUT / 'communication-provenance.json').read_text())
    assert not provenance['missingBranches']
    assert not {p: r for p, r in provenance['files'].items() if r['divergentRevisions'] or r['ambiguous']}
    refs = {n: provenance['branches']['origin/' + n] for n in ['agent-1', 'agent-2', 'agent-3']}
    counts = []
    for owner, path in [('agent-1', 'ledger/evidence/source-manifest.sha256'),
                        ('agent-2', 'protocol/evidence/source-manifest.sha256'),
                        ('agent-2', 'protocol/f0/MANIFEST.sha256')]:
        commit = refs[owner]
        raw = git('show', commit + ':' + path)
        entries = {}
        for line in raw.decode().splitlines():
            digest, source = line.split(maxsplit=1)
            source = source.lstrip('*').removeprefix('./')
            assert sha(git('show', commit + ':' + source)) == digest, source
            entries[source] = digest
        counts.append({'owner': owner, 'commit': commit, 'manifest': path,
                       'manifestSha256': sha(raw), 'entries': len(entries)})
    accepted = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    assert accepted['implementationAuthorized'] and not accepted['executionAuthorized']
    for path, digest in accepted['protocolF0Files'].items():
        assert sha(git('show', refs['agent-2'] + ':' + path)) == digest
    publication = json.loads((ROOT / 'interfaces/v2/FREEZE.json').read_text())
    assert publication['acceptance']['sha256'] == sha((ROOT / publication['acceptance']['path']).read_bytes())
    assert not publication['executionAuthorized']
    for path, pin in publication['files'].items():
        assert sha((ROOT / path).read_bytes()) == pin['sha256']
        assert (ROOT / path).read_bytes() == (ROOT / pin['sourcePath']).read_bytes()
    for path, digest in accepted['historicalBase'].items():
        assert sha((ROOT / path).read_bytes()) == digest
    # Readiness requires an actual immutable owner message, never a commit title.
    messages = {}
    for owner in ['agent-1', 'agent-2']:
        prefix = 'communication/' + owner + '/outbox/'
        candidates = [p for p in provenance['files'] if p.startswith(prefix) and p.endswith('.md') and
                      Path(p).name[:4].isdigit()]
        last = max(candidates)
        row = provenance['files'][last]
        messages[owner] = {'path': last, 'commit': refs[owner],
                          'fileChangingCommit': row['changeCommit'], 'sha256': row['sha256']}
    return {'refs': refs, 'communicationPaths': len(provenance['files']),
            'conflicts': [], 'manifests': counts, 'lastOwnerMessages': messages,
            'publishedPayloadsVerified': len(publication['files']),
            'protocolF0PinsVerified': len(accepted['protocolF0Files']),
            'note': 'Owner logs read/hash-verified, not rerun. No new source READY or execution ACK inferred.'}


mode = sys.argv[1]
if mode == 'before':
    result = {'capturedUtc': datetime.now(timezone.utc).isoformat(),
              'localCommit': git('rev-parse', 'HEAD').decode().strip(),
              'inputs': inputs(), 'peers': peers(),
              'tools': {'python': sys.version, 'pythonExecutable': sys.executable,
                        'git': git('--version').decode().strip(),
                        **{n: importlib.metadata.version(n) for n in ['pytest', 'jsonschema', 'eth-account']}}}
    (OUT / 'inputs-before.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'inputs'}, indent=2))
elif mode == 'after':
    before = json.loads((OUT / 'inputs-before.json').read_text())
    current = inputs()
    assert before['inputs'] == current, 'Local test inputs changed'
    result = {'capturedUtc': datetime.now(timezone.utc).isoformat(), 'stableInputs': len(current),
              'inputMapSha256': sha(json.dumps(current, sort_keys=True).encode()),
              'peers': peers(), 'runtimeOrGateResults': False, 'Fcases': 'ALL_32_NOT_RUN'}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
elif mode == 'compress-red':
    path = OUT / 'red.txt'
    raw = path.read_bytes()
    target = OUT / 'red.txt.gz'
    with target.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0))
    index = OUT / 'commands.json'
    rows = json.loads(index.read_text())
    row = next(r for r in rows if r['log'].endswith('/red.txt'))
    assert row['outputSha256'] == sha(raw)
    row.update(log=str(target.relative_to(ROOT)), contentEncoding='gzip',
               compressedSha256=sha(target.read_bytes()))
    index.write_text(json.dumps(rows, indent=2) + '\n')
    path.unlink()
    print('Preserved original RED output losslessly as gzip; raw SHA-256 unchanged.')
else:
    raise SystemExit('Unknown audit mode')
