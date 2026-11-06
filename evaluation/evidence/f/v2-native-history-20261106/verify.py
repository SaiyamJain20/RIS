"""Verify retained logs and complete source brackets; never an RQ gate."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


logs = {}
for row in json.loads((OUT / 'commands.json').read_text()):
    compressed = (ROOT / row['log']).read_bytes()
    assert sha(compressed) == row['compressedSha256']
    raw = gzip.decompress(compressed)
    assert sha(raw) == row['outputSha256']
    logs[Path(row['log']).name.removesuffix('.txt.gz')] = (row, raw.decode())
assert logs['red'][0]['exitCode'] == 1 and '63 failed' in logs['red'][1]
assert logs['red'][1].count("No module named 'evaluation.witness_native_v2'") == 63
assert logs['green-attempt'][0]['exitCode'] == 1 and '1 failed, 62 passed' in logs['green-attempt'][1]
assert logs['final-green'][0]['exitCode'] == 0 and '68 passed' in logs['final-green'][1]
assert logs['sensitivity'][0]['exitCode'] == 0 and '"sourceUnchanged": true' in logs['sensitivity'][1]
assert logs['sensitivity'][1].count('"mutatedSourceSha256"') == 7
assert logs['focused'][0]['exitCode'] == 0 and '754 passed' in logs['focused'][1]
assert logs['root-suite'][0]['exitCode'] == 0 and '2439 passed' in logs['root-suite'][1]
assert logs['audit-after'][0]['exitCode'] == 0
assert logs['audit-after'][0]['startedAt'] > logs['root-suite'][0]['endedAt']
frozen = json.loads((OUT / 'inputs-frozen.json').read_text())
for category in ('inputs', 'completeE2SourceInventory'):
    assert all(sha((ROOT / p).read_bytes()) == h for p,h in frozen[category].items())
provenance = json.loads((OUT / 'communication-provenance.json').read_text())
assert not provenance['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
report = dict(verified=True, classification='synthetic tested reconstruction/extension result',
    rootTests=2439, newTests=68, focusedTests=754, sensitivityControls=7,
    selectedInputsStable=len(frozen['inputs']), completeExecutionSourcesStable=len(frozen['completeE2SourceInventory']),
    communicationPaths=len(provenance['files']), frozenManifestSha256=sha((OUT / 'inputs-frozen.json').read_bytes()),
    notEstablished=['authenticated RPC captures', 'actual native ledger truth', 'source-state truth',
        'sign-time validity', 'exporter/store completeness', 'arrival/timing', 'persistence',
        'new E parity', 'integrated F cases', 'F gate', 'G'])
(OUT / 'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
