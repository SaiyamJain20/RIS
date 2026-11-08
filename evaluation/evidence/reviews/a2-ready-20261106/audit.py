"""Exact owner handoff provenance and scratch source brackets; no peer writes."""
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SCRATCH = ROOT / 'evaluation/runs/a2-ready-20261106/snapshot'
SOURCE = 'dbae4e1e13fb26984a6d4b0aa042ae321c1c49f0'
PUBLICATION = '9467ba170a0dff514d0457c8dbddc82510d177ca'
MANIFEST = 'protocol/evidence/af2-source-ready/MANIFEST.sha256'
MANIFEST_HASH = '6ed9a53de1ec2ec32fedad01019ce18cd4196a304cc47202b4a0e3655218ca08'
sys.path.insert(0, str(ROOT))
from evaluation.manifests import now
from evaluation.peers import scan


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + '\n')


def inventory():
    raw = git('show', PUBLICATION + ':' + MANIFEST)
    assert sha(raw) == MANIFEST_HASH
    pins = {}
    for line in raw.decode().splitlines():
        digest, path = line.split(maxsplit=1)
        assert path.startswith('protocol/') and '..' not in Path(path).parts and path not in pins
        assert sha(git('show', SOURCE + ':' + path)) == digest, path
        assert sha(git('show', PUBLICATION + ':' + path)) == digest, path
        pins[path] = digest
    tracked = set(git('ls-tree', '-r', '--name-only', SOURCE, 'protocol').decode().splitlines())
    assert set(pins) == tracked and len(pins) == 384, 'incomplete source manifest'
    return pins


def immutable_checks():
    accepted = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    assert accepted['implementationAuthorized'] and not accepted['executionAuthorized']
    for p, digest in accepted['protocolF0Files'].items():
        assert sha(git('show', SOURCE + ':' + p)) == digest, p
        assert sha(git('show', 'origin/agent-2:' + p)) == digest, p
    assert not git('diff', '--name-only', 'f48cb34', SOURCE, '--', 'protocol/hmbc_protocol/binding.py')
    ledger_source = '85c59f588de58a8ff5e87b9fe6f630c9d8c43642'
    ledger_manifest = git('show', ledger_source + ':ledger/evidence/source-manifest.sha256')
    assert sha(ledger_manifest) == '70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd'
    ledger_rows = ledger_manifest.decode().splitlines()
    for line in ledger_rows:
        digest, p = line.split(maxsplit=1)
        assert sha(git('show', ledger_source + ':' + p.removeprefix('./').lstrip('*'))) == digest
    assert not git('diff', '--name-only', ledger_source, 'origin/agent-1', '--', 'ledger')
    count = 0
    for revision in ('v1', 'v2', 'v2.1'):
        freeze = json.loads((ROOT / f'interfaces/{revision}/FREEZE.json').read_text())
        for p, row in freeze.get('frozenCopies', freeze.get('files', {})).items():
            assert sha((ROOT / p).read_bytes()) == row['sha256'], p
            count += 1
    return dict(protocolF0Pins=len(accepted['protocolF0Files']), publishedFiles=count,
                ledgerReadyEntries=len(ledger_rows), d50BindingSourceUnchangedSince='f48cb34')


def local_inputs():
    files = git('ls-files', 'evaluation', 'interfaces', 'pyproject.toml', 'uv.lock', 'SPEC.md', 'PLAN.md', 'AGENTS.md').decode().splitlines()
    return {p: sha((ROOT / p).read_bytes()) for p in files if '/evidence/' not in p}


mode = sys.argv[1]
pins = inventory()
immutables = immutable_checks()
if mode == 'before':
    assert not SCRATCH.exists()
    SCRATCH.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(git('archive', SOURCE, 'protocol'))) as archive:
        archive.extractall(SCRATCH, filter='data')
    for p, digest in pins.items():
        assert sha((SCRATCH / p).read_bytes()) == digest, p
    provenance = scan(ROOT)
    assert not provenance['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
    write('communication-provenance.json', provenance)
    owner_paths = ['communication/agent-2/outbox/0063-ready-isolated-successor-source-and-mapping.md',
                   'communication/agent-2/STATUS.md', 'communication/agent-2/HANDOFF.md', MANIFEST,
                   'protocol/evidence/af2-source-ready/MAPPING.md', 'protocol/evidence/af2-source-ready/README.md']
    owner = {p: dict(sha256=sha(git('show', PUBLICATION + ':' + p)),
        fileChangingCommit=git('log', '-1', '--format=%H', PUBLICATION, '--', p).decode().strip()) for p in owner_paths}
    historical = git('show', SOURCE + ':protocol/evidence/source-manifest.sha256')
    assert sha(historical) == '005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612'
    changed = []
    for line in historical.decode().splitlines():
        digest, path = line.split(maxsplit=1)
        path = path.removeprefix('./').lstrip('*')
        if sha(git('show', SOURCE + ':' + path)) != digest:
            changed.append(path)
    assert set(changed) == {'protocol/hmbc_protocol/worker_log.py', 'protocol/testtools/deviating_witness.py'}
    copies = json.loads((SCRATCH / 'protocol/tests/fixtures/agent3-interfaces-provenance.json').read_text())
    for name, row in copies['files'].items():
        data = (SCRATCH / 'protocol/tests/fixtures' / name).read_bytes()
        assert sha(data) == row['sha256']
        assert data == git('show', row.get('commit', copies['commit']) + ':' + row['path'])
    run_diff = git('diff', '--name-only', '076bde2c8f965b032d3b9a4d9ee99e124dc586d3', SOURCE, '--', 'protocol').decode().splitlines()
    assert set(run_diff) == {'protocol/evidence/af2-state/README.md', 'protocol/evidence/af2-state/full-suite-0f7-after-7b.txt'}
    data = dict(recordedAt=now(), sourceCommit=SOURCE, publicationCommit=PUBLICATION, manifestSha256=MANIFEST_HASH,
        scratch=str(SCRATCH), sourcePins=pins, localInputs=local_inputs(), immutableChecks=immutables,
        ownerProvenance=owner, communicationPaths=len(provenance['files']), branches=provenance['branches'],
        historicalEChanged=changed, historicalEEntries=len(historical.decode().splitlines()), copiedFixtures=len(copies['files']),
        ownerFullSuiteSourceDiff=run_diff, tools=dict(python=sys.version, executable=sys.executable,
            git=git('--version').decode().strip(), **{n: importlib.metadata.version(n) for n in ('pytest', 'jsonschema', 'eth-account')}))
    write('inputs-before.json', data)
    print(json.dumps({k: v for k, v in data.items() if k not in ('sourcePins', 'localInputs')}, indent=2))
elif mode == 'after':
    before = json.loads((OUT / 'inputs-before.json').read_text())
    assert before['sourcePins'] == pins and before['localInputs'] == local_inputs()
    for p, digest in pins.items():
        assert sha((SCRATCH / p).read_bytes()) == digest, p
    data = dict(recordedAt=now(), sourceEntriesUnchanged=len(pins), localInputsUnchanged=len(before['localInputs']), **immutables)
    write('source-after.json', data)
    print(json.dumps(data, indent=2))
elif mode == 'peers':
    provenance = scan(ROOT)
    assert not provenance['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
    write('communication-provenance-final.json', provenance)
    print(json.dumps(dict(recordedAt=now(), branches=provenance['branches'],
        communicationPaths=len(provenance['files']), immutableChecks=immutables,
        sourceDeltaSinceReady=git('diff', '--name-status', SOURCE, 'origin/agent-2', '--', 'protocol').decode()), indent=2))
else:
    raise SystemExit('before, after or peers required')
