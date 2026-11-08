"""Pin a partial owner source delta for review; never declare owner READY."""
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
SCRATCH = ROOT / 'evaluation/runs/a2-parser-fixes-20261106/snapshot'
SOURCE = '0297adb6e784b9667befbc6330e1dfcb3ec81e3e'
DELTA_BASE = '3b86183b8f537e32fc2f2c3be8b650735ab8173a'
PREVIOUS = 'c138185428ebe572c86cdc42985b340a262aa8aa'
PUBLICATION = 'f2c86ad868c3c6c0799f2b610ad55f5cb1a7306f'
LEDGER = '85c59f588de58a8ff5e87b9fe6f630c9d8c43642'
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
    paths = git('ls-tree', '-r', '--name-only', SOURCE, 'protocol').decode().splitlines()
    return {p: sha(git('show', SOURCE + ':' + p)) for p in paths}


def immutable_checks():
    acceptance = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    assert acceptance['implementationAuthorized'] and not acceptance['executionAuthorized']
    for p, digest in acceptance['protocolF0Files'].items():
        assert sha(git('show', SOURCE + ':' + p)) == digest, p
        assert sha(git('show', 'origin/agent-2:' + p)) == digest, p
    lm = git('show', LEDGER + ':ledger/evidence/source-manifest.sha256')
    assert sha(lm) == '70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd'
    for line in lm.decode().splitlines():
        digest, p = line.split(maxsplit=1)
        assert sha(git('show', LEDGER + ':' + p.removeprefix('./').lstrip('*'))) == digest, p
    assert not git('diff', '--name-only', LEDGER, 'origin/agent-1', '--', 'ledger')
    count = 0
    for revision in ('v1', 'v2', 'v2.1'):
        freeze = json.loads((ROOT / f'interfaces/{revision}/FREEZE.json').read_text())
        for p, row in freeze.get('frozenCopies', freeze.get('files', {})).items():
            assert sha((ROOT / p).read_bytes()) == row['sha256'], p
            count += 1
    ready = git('show', PUBLICATION + ':protocol/evidence/af2-source-ready-2/MANIFEST.sha256')
    assert sha(ready) == '016ffd0870e3b9bfd2b8b297c8c977bcfe29ce687d0a54b548b901c52e8b9cbf'
    changed = []
    for line in ready.decode().splitlines():
        digest, p = line.split(maxsplit=1)
        assert sha(git('show', PREVIOUS + ':' + p)) == digest, p
        assert sha(git('show', PUBLICATION + ':' + p)) == digest, p
        if sha(git('show', SOURCE + ':' + p)) != digest:
            changed.append(p)
    assert changed == ['protocol/evidence/af2-state/README.md'], changed
    assert not git('diff', '--name-only', 'f48cb34', SOURCE, '--', 'protocol/hmbc_protocol/binding.py')
    return dict(ledgerReadyEntries=len(lm.decode().splitlines()),
                protocolF0Pins=len(acceptance['protocolF0Files']), publishedFiles=count,
                previousReadyEntries=len(ready.decode().splitlines()),
                previousReadyChangedAtReviewedSource=changed)


def local_inputs():
    paths = git('ls-files', 'evaluation', 'interfaces', 'pyproject.toml', 'uv.lock',
                'SPEC.md', 'PLAN.md', 'AGENTS.md').decode().splitlines()
    return {p: sha((ROOT / p).read_bytes()) for p in paths if '/evidence/' not in p}


def peer_scan(name):
    result = scan(ROOT)
    assert not result['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in result['files'].values())
    write(name, result)
    return dict(branches=result['branches'], communicationPaths=len(result['files']))


mode = sys.argv[1]
pins = inventory()
immutable = immutable_checks()
if mode == 'before':
    assert not SCRATCH.exists()
    SCRATCH.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(git('archive', SOURCE, 'protocol'))) as archive:
        archive.extractall(SCRATCH, filter='data')
    for p, digest in pins.items():
        assert sha((SCRATCH / p).read_bytes()) == digest, p
    owner_paths = git('diff', '--name-only', DELTA_BASE, SOURCE).decode().splitlines()
    provenance = {p: dict(sha256=sha(git('show', SOURCE + ':' + p)),
                         fileChangingCommit=git('log', '-1', '--format=%H', SOURCE, '--', p).decode().strip())
                  for p in owner_paths}
    abi_provenance = json.loads((SCRATCH / 'protocol/tests/fixtures/agent1-85c59f5-abi-provenance.json').read_text())
    for name, row in abi_provenance['files'].items():
        p = 'protocol/tests/fixtures/agent1-85c59f5-abi/' + name + '.json'
        raw = (SCRATCH / p).read_bytes()
        assert sha(raw) == row['sha256']
        assert raw == git('show', LEDGER + ':ledger/exports/abi/' + name + '.json')
    copied = json.loads((SCRATCH / 'protocol/tests/fixtures/agent3-interfaces-provenance.json').read_text())
    for name, row in copied['files'].items():
        raw = (SCRATCH / 'protocol/tests/fixtures' / name).read_bytes()
        assert sha(raw) == row['sha256']
        assert raw == git('show', row.get('commit', copied['commit']) + ':' + row['path'])
    data = dict(recordedAt=now(), sourceCommit=SOURCE, ownerRuntimeReady=False,
                previousReadySource=PREVIOUS, previousReadyPublication=PUBLICATION,
                scratch=str(SCRATCH), sourcePins=pins, localInputs=local_inputs(),
                helperPins={p.name: sha(p.read_bytes()) for p in OUT.glob('*.py')},
                deltaProvenance=provenance, immutableChecks=immutable,
                copiedAbiFiles=len(abi_provenance['files']), copiedInterfaceFixtures=len(copied['files']),
                **peer_scan('communication-provenance.json'),
                tools=dict(python=sys.version, executable=sys.executable,
                           git=git('--version').decode().strip(),
                           **{n: importlib.metadata.version(n) for n in ('pytest', 'jsonschema', 'eth-account', 'eth-abi')}))
    write('inputs-before.json', data)
    print(json.dumps({k: v for k, v in data.items() if k not in ('sourcePins', 'localInputs')}, indent=2))
elif mode == 'after':
    before = json.loads((OUT / 'inputs-before.json').read_text())
    assert before['sourcePins'] == pins and before['localInputs'] == local_inputs()
    assert before['helperPins'] == {p.name: sha(p.read_bytes()) for p in OUT.glob('*.py')}
    for p, digest in pins.items():
        assert sha((SCRATCH / p).read_bytes()) == digest, p
    data = dict(recordedAt=now(), sourceEntriesUnchanged=len(pins),
                localInputsUnchanged=len(before['localInputs']), **immutable)
    write('source-after.json', data)
    print(json.dumps(data, indent=2))
elif mode == 'peers':
    print(json.dumps(dict(recordedAt=now(), **peer_scan('communication-provenance-final.json'),
                         immutableChecks=immutable), indent=2))
else:
    raise SystemExit('before, after or peers required')
