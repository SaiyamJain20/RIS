"""Verify retained command bytes, complete source brackets and probe claims."""
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
rows = json.loads((OUT / 'commands.json').read_text())
for row in rows:
    assert row['exitCode'] == 0 and not row['timedOut'], row
    packed = (ROOT / row['log']).read_bytes()
    assert sha(packed) == row['compressedSha256']
    assert sha(gzip.decompress(packed)) == row['outputSha256']
before = json.loads((OUT / 'inputs-before.json').read_text())
after = json.loads((OUT / 'source-after.json').read_text())
assert after['sourceEntriesUnchanged'] == len(before['sourcePins'])
assert after['localInputsUnchanged'] == len(before['localInputs'])
for name, digest in before['helperPins'].items():
    assert sha((OUT / name).read_bytes()) == digest
peer = json.loads((OUT / 'communication-provenance-final.json').read_text())
assert not peer['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in peer['files'].values())
baseline = json.loads((OUT / 'baseline-probes.json').read_text())
assert len(baseline['gaps']) == 9
assert sum(r['actual'] == 'AttributeError' for r in baseline['rows']) == 4
probes = json.loads((OUT / 'fixed-probes.json').read_text())
assert [(r['label'], r['replies'], r['expected'], r['diagnostic']) for r in baseline['rows']] == [(r['label'], r['replies'], r['expected'], r['diagnostic']) for r in probes['rows']]
assert [r['label'] for r in baseline['rows'] if r['actual'] != next(x['actual'] for x in probes['rows'] if x['label'] == r['label'])] == [r['label'] for r in baseline['rows'] if r['actual'] == 'AttributeError']
assert all(r['actual'] == 'LEDGER_UNREACHABLE' for r in probes['rows'] if r['label'].startswith('transaction shape '))
assert probes['controls'] == 14 and probes['diagnostics'] == 13
assert len(probes['gaps']) == 5
assert sum(r['actual'] == 'AttributeError' for r in probes['rows']) == 0
assert all(r['actual'] == r['expected'] for r in probes['rows'] if not r['diagnostic'])
read = lambda label: gzip.decompress((OUT / (label + '.txt.gz')).read_bytes()).decode()
selection = json.loads((OUT / 'focused-selection.json').read_text())
assert not selection['excludedLiveFixture']
count = len(selection['selected'])
assert re.search(r'\b' + str(count) + r' passed', read('focused-tests'))
assert 'control: unmutated module passes all tests' in read('witness-mutants')
assert 'detected 45 of 45' in read('witness-mutants')
assert len(re.findall(r'^DETECTED ', read('witness-mutants'), re.M)) == 45
assert 'NOT-DETECTED' not in read('witness-mutants')
assert read('exports').strip() == 'exports match 9 files'
result = dict(commandsVerified=len(rows), sourceCommit=before['sourceCommit'],
              sourceEntries=len(before['sourcePins']), localInputs=len(before['localInputs']),
              focusedPass=count, ownerMutantsDetected=45, defaultExports=9,
              controls=14, diagnostics=13, baselineDiagnosticGaps=9, diagnosticGaps=5, uncaughtAttributeErrors=0,
              immutableChecks=after, peerBranches=peer['branches'], communicationPaths=len(peer['files']),
              ownerRuntimeReady=False, ownerLiveResultsRerun=False, executionAuthorized=False,
              fGate='NOT_RUN', gGate='LOCKED')
(OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
