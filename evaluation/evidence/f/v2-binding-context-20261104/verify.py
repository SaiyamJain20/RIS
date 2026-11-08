"""Verify retained command evidence and source bracket; no owner execution."""
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
assert [(logs[n][0]['exitCode']) for n in ('red.txt', 'namespace-red.txt', 'audit-before.txt')] == [1, 1, 1]
assert '83 failed' in logs['red.txt'][1] and 'No module named' in logs['red.txt'][1]
assert '1 failed, 97 passed' in logs['namespace-red.txt'][1]
assert "KeyError: 'files'" in logs['audit-before.txt'][1]
assert '324 passed' in logs['focused.txt'][1] and logs['focused.txt'][0]['exitCode'] == 0
assert '1982 passed' in logs['root-suite.txt'][1] and logs['root-suite.txt'][0]['exitCode'] == 0
assert logs['audit-after-suite.txt'][0]['startedAt'] > logs['root-suite.txt'][0]['endedAt']
assert len(json.loads(logs['sensitivity.txt'][1])['controls']) == 6
before = json.loads((OUT / 'inputs-before.json').read_text())
assert all(sha((ROOT / p).read_bytes()) == h for p, h in before['inputs'].items())
provenance = json.loads((OUT / 'communication-provenance.json').read_text())
assert not provenance['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
proof = {'classification': 'synthetic tested reconstruction and deliberate in-memory mutations',
    'rootTests': 1982, 'focusedTests': 324, 'newTests': 98, 'joinRemovalControls': 6,
    'inputsStable': len(before['inputs']), 'ledgerReadyEntriesVerified': 429,
    'protocolF0PinsVerified': 52, 'publicationPayloadsVerified': before['publicationFiles'],
    'communicationPaths': len(provenance['files']), 'branches': provenance['branches'],
    'retainedCommandsVerified': len(rows), 'auditFirstSourceSha256': sha(gzip.decompress((OUT / 'audit-first.py.gz').read_bytes())),
    'auditFinalSourceSha256': sha((OUT / 'audit.py').read_bytes()),
    'rpcAcquisition': 'NOT_IMPLEMENTED', 'sourceConstructorAttestation': 'NOT_PROVED',
    'exporterHistoryWalNativeJoins': 'NOT_IMPLEMENTED', 'protocolSourceReady': False,
    'integratedExecution': 'LOCKED', 'gateF': 'NOT_RUN', 'g': 'LOCKED', 'independentReview': False}
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2))
