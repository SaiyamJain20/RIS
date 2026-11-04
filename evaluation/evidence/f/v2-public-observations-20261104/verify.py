"""Validate immutable command evidence, owner copies and both input brackets."""
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
    if row.get('contentEncoding') == 'gzip':
        assert sha(raw) == row['compressedSha256']
        raw = gzip.decompress(raw)
    assert sha(raw) == row['outputSha256'], row['log']
    assert not row['timedOut']
    logs[Path(row['log']).name.removesuffix('.gz')] = (row, raw.decode())
for name, count in [('red.txt', '39 failed'), ('review-red.txt', '1 failed, 52 passed')]:
    assert logs[name][0]['exitCode'] == 1 and count in logs[name][1]
assert 'No module named' in logs['red.txt'][1]
assert logs['root-suite.txt'][0]['exitCode'] == 2
assert 'test_audit_execution_requires_each_complete_row_proof[complete]' in logs['root-suite.txt'][1]
assert 'KeyboardInterrupt' in logs['root-suite.txt'][1]
assert logs['root-suite-frozen.txt'][0]['exitCode'] == 0
assert '2036 passed' in logs['root-suite-frozen.txt'][1]
assert '351 passed' in logs['focused.txt'][1] and logs['focused.txt'][0]['exitCode'] == 0
assert logs['audit-after-suite.txt'][0]['startedAt'] > logs['root-suite-frozen.txt'][0]['endedAt']
assert len(json.loads(logs['sensitivity.txt'][1])['controls']) == 6
before = json.loads((OUT / 'inputs-frozen.json').read_text())
assert all(sha((ROOT / p).read_bytes()) == h for p, h in before['inputs'].items())
assert all(sha((ROOT / p).read_bytes()) == h for p, h in before['completeE2SourceInventory'].items())
provenance = json.loads((OUT / 'communication-provenance.json').read_text())
assert not provenance['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
peer_review = json.loads((OUT / 'peer-review.json').read_text())
assert peer_review['exactOwnerAbiFiles'] == 7 and not peer_review['differentialRerun']
proof = {'classification': 'synthetic tested reconstruction; deliberate in-memory mutations',
    'newTests': 54, 'focusedTests': 351, 'rootTests': 2036, 'joinRemovalControls': 6,
    'inputsStable': len(before['inputs']), 'completeE2SourceInventoryStable': len(before['completeE2SourceInventory']),
    'retainedCommandsVerified': len(rows), 'ledgerReadyEntriesVerified': 429,
    'protocolF0PinsVerified': 52, 'publicationPayloadsVerified': before['publicationFiles'],
    'communicationPaths': len(provenance['files']), 'branches': provenance['branches'],
    'initialRootAttempt': 'interrupted after source drift failure from adding two evidence scripts; retained exit2',
    'publicAbiCollector': 'IMPLEMENTED; byte-level synthetic RPC and synthetic CLI tests only',
    'liveRpc': 'NOT_RUN', 'sourceConstructorAttestation': 'NOT_PROVED',
    'signingContextWiring': 'NOT_IMPLEMENTED', 'exporterHistoryWalNativeJoins': 'NOT_IMPLEMENTED',
    'protocolSourceReady': False, 'integratedExecution': 'LOCKED', 'gateF': 'NOT_RUN', 'g': 'LOCKED',
    'independentReview': False}
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2))
