"""Input brackets, immutable publications and exact fetched peer provenance."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.manifests import now
from evaluation.peers import scan


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def inputs():
    paths = [p for folder in ('evaluation', 'interfaces') for p in (ROOT / folder).rglob('*')
        if p.is_file() and not {'runs', 'evidence', '__pycache__'}.intersection(p.relative_to(ROOT).parts)
        and p.suffix in ('.py', '.json', '.csv', '.pv', '.tla', '.cfg', '.md')]
    paths += [ROOT / p for p in ('pyproject.toml', 'uv.lock', 'AGENTS.md', 'SPEC.md', 'PLAN.md',
        'communication/F0_ACCEPTANCE_CANDIDATE2.json', 'communication/E_SOURCE_CLOSURE_ACCEPTANCE.json',
        'communication/E_SOURCE_CLOSURE_MAPPING.json')]
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(set(paths))}


def peers():
    provenance = scan(ROOT)
    (OUT / 'communication-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    assert not provenance['missingBranches']
    assert not any(v['ambiguous'] or v['divergentRevisions'] for v in provenance['files'].values())
    accepted = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    assert accepted['implementationAuthorized'] and not accepted['executionAuthorized']
    for p, h in accepted['protocolF0Files'].items():
        assert sha(git('show', provenance['branches']['origin/agent-2'] + ':' + p)) == h, p
    ledger_source = '85c59f588de58a8ff5e87b9fe6f630c9d8c43642'
    raw = git('show', ledger_source + ':ledger/evidence/source-manifest.sha256')
    assert sha(raw) == '70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd'
    entries = {}
    for line in raw.decode().splitlines():
        h, p = line.split(maxsplit=1)
        p = p.removeprefix('./').lstrip('*')
        assert sha(git('show', ledger_source + ':' + p)) == h
        entries[p] = h
    assert not git('diff', '--name-only', ledger_source, 'origin/agent-1', '--', 'ledger')
    statuses = {}
    for owner in ('agent-1', 'agent-2'):
        commit = provenance['branches']['origin/' + owner]
        for kind in ('STATUS', 'HANDOFF'):
            p = f'communication/{owner}/{kind}.md'
            row = provenance['files'][p]
            data = git('show', commit + ':' + p)
            assert sha(data) == row['sha256']
            statuses[p] = {'commit': commit, 'fileChangingCommit': row['changeCommit'], 'sha256': sha(data)}
    return {'branches': provenance['branches'], 'communicationPaths': len(provenance['files']),
        'ownerState': statuses, 'ledgerSource': ledger_source, 'ledgerEntriesVerified': len(entries),
        'protocolF0PinsVerified': len(accepted['protocolF0Files']),
        'protocolStatus': 'partial implementation; NOT_READY; owner tests not rerun or adopted',
        'protocolDelta': git('diff', '--name-status', '051cf67ccb16913d275337a98cf62a5575f0b9a4', 'origin/agent-2', '--', 'protocol').decode()}


def publications():
    count = 0
    for revision in ('v1', 'v2', 'v2.1'):
        freeze = json.loads((ROOT / f'interfaces/{revision}/FREEZE.json').read_text())
        pins = freeze['frozenCopies'] if revision == 'v1' else freeze['files']
        for p, pin in pins.items():
            assert sha((ROOT / p).read_bytes()) == pin['sha256'], p
            count += 1
    return count


mode = sys.argv[1]
if mode == 'before':
    data = {'capturedAt': now(), 'head': git('rev-parse', 'HEAD').decode().strip(),
        'inputs': inputs(), 'peers': peers(), 'publicationFiles': publications(),
        'tools': {'python': sys.version, 'executable': sys.executable, 'git': git('--version').decode().strip(),
                  **{n: importlib.metadata.version(n) for n in ('pytest', 'jsonschema', 'eth-account')}}}
    assert not (OUT / 'inputs-before.json').exists()
    (OUT / 'inputs-before.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'inputs': len(data['inputs']), 'peers': data['peers']['branches'], 'publicationFiles': data['publicationFiles']}))
elif mode == 'frozen':
    from evaluation.e2 import _sources
    data = {'capturedAt': now(), 'head': git('rev-parse', 'HEAD').decode().strip(),
        'inputs': inputs(), 'completeE2SourceInventory': _sources(),
        'peers': peers(), 'publicationFiles': publications(),
        'tools': {'python': sys.version, 'executable': sys.executable, 'git': git('--version').decode().strip(),
                  **{n: importlib.metadata.version(n) for n in ('pytest', 'jsonschema', 'eth-account')}}}
    assert not (OUT / 'inputs-frozen.json').exists()
    (OUT / 'inputs-frozen.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'inputs': len(data['inputs']), 'completeE2Sources': len(data['completeE2SourceInventory']),
        'publicationFiles': data['publicationFiles'], 'peers': data['peers']['branches']}))
elif mode == 'after':
    from evaluation.e2 import _sources
    frozen = json.loads((OUT / 'inputs-frozen.json').read_text())
    assert _sources() == frozen['completeE2SourceInventory'], 'complete E2 source inventory drift'
    before = json.loads((OUT / 'inputs-before.json').read_text())
    assert inputs() == before['inputs'], 'test input drift'
    assert inputs() == frozen['inputs'], 'frozen test input drift'
    print(json.dumps({'inputsUnchanged': len(before['inputs']), 'completeE2SourcesUnchanged': len(frozen['completeE2SourceInventory']),
        'publicationFilesVerified': publications()}))
elif mode == 'peers':
    print(json.dumps(peers(), indent=2))
else:
    raise SystemExit('before, frozen, after or peers required')
