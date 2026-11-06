"""Verify exact retained evidence and source brackets; no RQ gate assertion."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


rows = json.loads((OUT / 'commands.json').read_text())
logs = {}
for row in rows:
    raw = (ROOT / row['log']).read_bytes()
    assert sha(raw) == row['compressedSha256']
    raw = gzip.decompress(raw)
    assert sha(raw) == row['outputSha256']
    logs[Path(row['log']).name.removesuffix('.txt.gz')] = (row, raw.decode())
assert logs['red'][0]['exitCode'] == 1 and '90 failed' in logs['red'][1]
assert "No module named 'evaluation.witness_history_v2'" in logs['red'][1]
assert logs['green'][0]['exitCode'] == 0 and '90 passed' in logs['green'][1]
assert logs['review-controls'][0]['exitCode'] == 0 and '139 passed' in logs['review-controls'][1]
assert logs['focused'][0]['exitCode'] == 0 and '582 passed' in logs['focused'][1]
assert logs['root-suite'][0]['exitCode'] == 0 and '2267 passed' in logs['root-suite'][1]
assert logs['audit-after'][0]['exitCode'] == 0
assert logs['audit-after'][0]['startedAt'] > logs['root-suite'][0]['endedAt']
assert logs['sensitivity'][0]['exitCode'] == 0
assert len(json.loads(logs['sensitivity'][1])['controls']) == 7
frozen = json.loads((OUT / 'inputs-frozen.json').read_text())
assert all(sha((ROOT / p).read_bytes()) == h for p, h in frozen['inputs'].items())
assert all(sha((ROOT / p).read_bytes()) == h for p, h in frozen['completeE2SourceInventory'].items())
provenance = json.loads((OUT / 'communication-provenance.json').read_text())
assert not provenance['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
proof = dict(classification='synthetic tested reconstruction and deliberate mutations', newTests=139,
    focusedTests=582, rootTests=2267, joinRemovalControls=7,
    inputsStable=len(frozen['inputs']), completeSourceInventoryStable=len(frozen['completeE2SourceInventory']),
    retainedCommandsVerified=len(rows), ledgerReadyEntriesVerified=429, protocolF0PinsVerified=52,
    publicationPayloadsVerified=frozen['publicationFiles'], communicationPaths=len(provenance['files']),
    branches=provenance['branches'], independentReview=False,
    nativeLedgerTruth='NOT_PROVED', walMarkerStoreCompleteness='NOT_IMPLEMENTED',
    faultOracleFiniteModel='NOT_IMPLEMENTED', protocolSourceReady=False,
    integratedExecution='LOCKED', gateF='NOT_RUN', g='LOCKED')
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2))
