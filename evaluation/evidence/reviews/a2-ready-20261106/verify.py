"""Verify retained outputs and emit the scoped review receipt; no test is inferred."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.manifests import now

rows = json.loads((OUT / 'commands.json').read_text())
for row in rows:
    raw = (ROOT / row['log']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['compressedSha256']
    assert hashlib.sha256(gzip.decompress(raw)).hexdigest() == row['outputSha256']
    expected = 1 if row['log'].endswith('/isolated-regression.txt.gz') else 0
    assert row['exitCode'] == expected
for name, required in (
    ('focused', '843 passed'),
    ('isolated-regression-v2', '2027 passed, 201 skipped, 199 deselected'),
    ('adapter-mutants', 'detected 43 of 43'),
    ('startup-mutants', 'detected 15 of 15'),
    ('worker-binding-mutants', 'detected 32 of 32'),
    ('export-check', 'exports match 9 files'),
):
    assert required in gzip.decompress((OUT / (name + '.txt.gz')).read_bytes()).decode()
probe = json.loads(gzip.decompress((OUT / 'mapping-probe-v2.txt.gz').read_bytes()))
assert len(probe['controls']) == 16
bracket = json.loads((OUT / 'source-after.json').read_text())
assert bracket['sourceEntriesUnchanged'] == 384 and bracket['localInputsUnchanged'] == 248
selected = json.loads((OUT / 'regression-selection-v2.json').read_text())
assert len(selected['selected']) == 2228 and len(selected['excludedLiveFixture']) == 199
proof = dict(recordedAt=now(), classification='synthetic tested reconstruction/extension source review',
    sourceCommit='dbae4e1e13fb26984a6d4b0aa042ae321c1c49f0',
    publicationCommit='9467ba170a0dff514d0457c8dbddc82510d177ca',
    ownerManifestSha256='6ed9a53de1ec2ec32fedad01019ce18cd4196a304cc47202b4a0e3655218ca08',
    focusedPassed=843, isolatedRegression=dict(passed=2027, skipped=201, deselected=199, exitCode=0, fullSuite=False),
    coordinatorControls=16, selectedMutantsDetected=dict(adapter=43, startup=15, workerBinding=32),
    sourceBracket=bracket,
    failedReviewAttempt=dict(failed=23, passed=2027, skipped=201, deselected=170, errors=6, exitCode=1,
        classification='coordinator selection failure before chain startup; retained'),
    reviewedScope='isolated injected APIs with supplied published schema',
    sourceOrganization='new modules instead of editing carried witness.py; accepted internal organization, runtime process obligations remain',
    omissionControls=['schema=None permits incomplete carrier', 'frontend accepts arbitrary dict handler result'],
    runtimeReady=False, executionAuthorized=False, gateF='NOT_RUN', gateG='LOCKED',
    servicesStarted=False, peerEdits=False, ownerTestsCorrelated=True, rootEvaluatorSuiteRerun=False,
    helperSourceHashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.py')})
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2))
