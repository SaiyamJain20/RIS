"""Verify retained evidence and exact source brackets, never assert an RQ gate."""
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
    raw = (ROOT / row['log']).read_bytes()
    assert sha(raw) == row['compressedSha256']
    raw = gzip.decompress(raw)
    assert sha(raw) == row['outputSha256']
    logs[Path(row['log']).name.removesuffix('.txt.gz')] = (row, raw.decode())
assert logs['red'][0]['exitCode'] == 1
assert "No module named 'evaluation.store_snapshot_v2'" in logs['red'][1]
assert '30 errors' in logs['red'][1]
assert logs['green'][0]['exitCode'] == 1 and '2 failed, 28 passed' in logs['green'][1]
assert logs['review-red'][0]['exitCode'] == 1 and '1 failed, 39 passed' in logs['review-red'][1]
assert logs['review-green'][0]['exitCode'] == 0 and '40 passed' in logs['review-green'][1]
assert logs['sensitivity'][0]['exitCode'] == 0 and '"sourceUnchanged": true' in logs['sensitivity'][1]
assert logs['sensitivity'][1].count('"mutatedSourceSha256"') == 6
assert logs['focused'][0]['exitCode'] == 0 and '622 passed' in logs['focused'][1]
assert logs['root-suite'][0]['exitCode'] == 0 and '2307 passed' in logs['root-suite'][1]
assert logs['audit-after'][0]['exitCode'] == 0
assert logs['audit-after'][0]['startedAt'] > logs['root-suite'][0]['endedAt']
frozen = json.loads((OUT / 'inputs-frozen.json').read_text())
for category in ('inputs', 'completeE2SourceInventory'):
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in frozen[category].items())
provenance = json.loads((OUT / 'communication-provenance.json').read_text())
assert not provenance['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
report = {'verified': True, 'classification': 'synthetic tested reconstruction/extension result',
          'rootTests': 2307, 'newTests': 40, 'focusedTests': 622, 'sensitivityControls': 6,
          'selectedInputsStable': len(frozen['inputs']),
          'completeExecutionSourcesStable': len(frozen['completeE2SourceInventory']),
          'communicationPaths': len(provenance['files']),
          'frozenManifestSha256': sha((OUT / 'inputs-frozen.json').read_bytes()),
          'notEstablished': ['export completeness', 'owner store compatibility', 'native ledger facts',
                             'authenticated history', 'power-loss persistence', 'new E parity',
                             'integrated F cases', 'F gate', 'G']}
(OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
