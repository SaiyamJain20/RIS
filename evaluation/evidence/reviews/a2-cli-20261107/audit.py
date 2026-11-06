"""Exact peer snapshots and pre/post input brackets; no runtime READY inference."""
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'evaluation/runs/a2-cli-20261107'
SNAP = RUN / 'snapshot'
A1 = '8c0285ffa6986858caeb0140b930bf5db759fdc0'
A2 = '7915d532ff17c9e782bd23d4887374c01601154f'
LEDGER = '85c59f588de58a8ff5e87b9fe6f630c9d8c43642'
BASE = 'b0184e7cca2be4328ccd1ce10e99b3c87eacff28'
FORGE = '/home/karma/.local/share/hmbc-tools/foundry-1.8.5/forge'
sys.path.insert(0, str(ROOT))
from evaluation.peers import scan
from evaluation.manifests import now

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n')

def local_inputs():
    paths = git('ls-files', 'evaluation', 'interfaces', 'pyproject.toml', 'uv.lock', 'SPEC.md', 'PLAN.md', 'AGENTS.md').decode().splitlines()
    return {p: sha((ROOT / p).read_bytes()) for p in paths if '/evidence/' not in p}

def helpers():
    return {p.name: sha(p.read_bytes()) for p in OUT.iterdir() if p.suffix in ('.py', '.sol') or p.name == 'PLAN.md'}

def immutable():
    a = json.loads((ROOT / 'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    assert a['implementationAuthorized'] and not a['executionAuthorized']
    for p, digest in a['protocolF0Files'].items():
        assert sha(git('show', A2 + ':' + p)) == digest, p
    lm = git('show', LEDGER + ':ledger/evidence/source-manifest.sha256')
    assert sha(lm) == '70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd'
    for line in lm.decode().splitlines():
        digest, p = line.split(maxsplit=1)
        assert sha(git('show', LEDGER + ':' + p.removeprefix('./').lstrip('*'))) == digest, p
    assert not git('diff', '--name-only', LEDGER, A1, '--', 'ledger')
    count = 0
    for revision in ('v1', 'v2', 'v2.1'):
        f = json.loads((ROOT / f'interfaces/{revision}/FREEZE.json').read_text())
        for p, row in f.get('frozenCopies', f.get('files', {})).items():
            assert sha((ROOT / p).read_bytes()) == row['sha256'], p
            count += 1
    return dict(ledgerReadyEntries=len(lm.decode().splitlines()), protocolF0Pins=len(a['protocolF0Files']), frozenPayloads=count)

def peers(filename):
    result = scan(ROOT)
    assert not result['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in result['files'].values())
    write(filename, result)
    return dict(branches=result['branches'], communicationPaths=len(result['files']))

mode = sys.argv[1]
if mode == 'before':
    assert git('branch', '--show-current').decode().strip() == 'agent-3'
    assert not SNAP.exists()
    SNAP.mkdir(parents=True)
    pins = {}
    for commit, module in ((LEDGER, 'ledger'), (A2, 'protocol')):
        with tarfile.open(fileobj=io.BytesIO(git('archive', commit, module))) as archive:
            archive.extractall(SNAP, filter='data')
        for p in git('ls-tree', '-r', '--name-only', commit, module).decode().splitlines():
            pins[p] = sha(git('show', commit + ':' + p))
            assert sha((SNAP / p).read_bytes()) == pins[p]
    delta = git('diff', BASE, A2, '--', 'protocol', 'communication/agent-2')
    (OUT / 'owner-delta.patch.gz').write_bytes(gzip.compress(delta, mtime=0))
    changed = git('diff', '--name-only', BASE, A2).decode().splitlines()
    provenance = {p: dict(sha256=sha(git('show', A2 + ':' + p)), fileChangingCommit=git('log', '-1', '--format=%H', A2, '--', p).decode().strip()) for p in changed}
    old = git('show', BASE + ':protocol/hmbc_protocol/worker.py')
    (RUN / 'baseline_worker.py').write_bytes(old)
    historical = git('show', A2 + ':protocol/evidence/source-manifest.sha256')
    changed_e = []
    for line in historical.decode().splitlines():
        digest, p = line.split(maxsplit=1)
        p = p.removeprefix('./').lstrip('*')
        if sha(git('show', A2 + ':' + p)) != digest:
            changed_e.append(p)
    assert set(changed_e) == {'protocol/hmbc_protocol/worker.py', 'protocol/hmbc_protocol/worker_log.py', 'protocol/testtools/deviating_witness.py'}
    data = dict(recordedAt=now(), a1Tip=A1, a2Tip=A2, ledgerSource=LEDGER,
                deltaBase=BASE, completeRuntimeReady=False, executionAuthorized=False,
                sourcePins=pins, localInputs=local_inputs(), helperPins=helpers(),
                historicalEChanged=changed_e, historicalEEntries=len(historical.decode().splitlines()), baselineWorkerSha256=sha(old),
                deltaProvenance=provenance, immutable=immutable(), **peers('communication-before.json'),
                tools=dict(python=sys.version, executable=sys.executable, git=git('--version').decode().strip(), forge=subprocess.check_output([FORGE, '--version']).decode(), forgeSha256=sha(Path(FORGE).read_bytes()), **{n: importlib.metadata.version(n) for n in ('pytest','eth-account','eth-abi','jsonschema')}),
                environmentSha256=sha(json.dumps(dict(os.environ), sort_keys=True).encode()))
    write('inputs-before.json', data)
    print(json.dumps(dict(sourceEntries=len(pins), deltaPaths=len(changed), immutable=data['immutable'], tools=data['tools'], communicationPaths=data['communicationPaths']), indent=2))
elif mode == 'after':
    data = json.loads((OUT / 'inputs-before.json').read_text())
    assert data['localInputs'] == local_inputs()
    assert data['helperPins'] == helpers()
    for p, digest in data['sourcePins'].items():
        assert sha((SNAP / p).read_bytes()) == digest, p
    assert sha((RUN / 'baseline_worker.py').read_bytes()) == data['baselineWorkerSha256']
    write('inputs-after.json', dict(recordedAt=now(), unchangedSourceEntries=len(data['sourcePins']), unchangedLocalInputs=len(data['localInputs']), unchangedHelpers=len(data['helperPins']), immutable=immutable()))
    print((OUT / 'inputs-after.json').read_text())
elif mode == 'peers':
    print(json.dumps(peers('communication-final.json'), indent=2))
else:
    raise SystemExit('before, after, peers')
