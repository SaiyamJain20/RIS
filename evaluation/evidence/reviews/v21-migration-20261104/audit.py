"""Verify review receipts, retained command bytes and immutable publication pins."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    data = json.loads((ROOT / 'communication/E_SOURCE_CLOSURE_MAPPING.json').read_text())
    for receipt in data['publicationReceipts']:
        raw = subprocess.check_output(['git', 'show', receipt['commit'] + ':' + receipt['path']], cwd=ROOT)
        assert sha(raw) == receipt['sha256']
        assert receipt['fileChangingCommit'] == subprocess.check_output(
            ['git', 'log', '-1', '--format=%H', receipt['commit'], '--', receipt['path']], cwd=ROOT).decode().strip()
        assert data['publication']['freeze']['sha256'] in raw.decode()
        assert data['publication']['schema']['sha256'] in raw.decode()
    for pin in data['publication'].values():
        if isinstance(pin, dict):
            assert sha((ROOT / pin['path']).read_bytes()) == pin['sha256']
    old = data['historicalAcceptanceUnchanged']
    assert sha((ROOT / old['path']).read_bytes()) == old['sha256']
    assert json.loads((ROOT / old['path']).read_text())['publicationMappingAcks'] == []
    assert data['executionAuthorized'] is False and data['protocolMigration']['sourceReady'] is None
    assert data['protocolMigration']['consumerMappingAck'] is None
    proof = OUT / 'verification.json'
    assert sha(proof.read_bytes()) == data['ledgerMigration']['verificationSha256']
    v = json.loads(proof.read_text())
    assert v['inventoryEntriesBeforeAfter'] == 429 and len(v['syntheticProducerTrials']) == 28
    assert v['ownerCarriersCompiledChecked'] == 4 and v['sourceMapEntries'] == 12
    inputs = json.loads((OUT / 'inputs.json').read_text())
    scratch = Path(inputs['scratch'])
    assert all(sha((scratch / p).read_bytes()) == h for p, h in inputs['entries'].items())
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in inputs['publicationPins'].items())
    command_count = 0
    for name in ('commands.json', 'helper-commands.json'):
        for row in json.loads((OUT / name).read_text()):
            raw = (ROOT / row['log']).read_bytes()
            if row.get('contentEncoding') == 'gzip':
                assert sha(raw) == row['compressedSha256']
                raw = gzip.decompress(raw)
            assert sha(raw) == row['outputSha256'], row['log']
            assert not row['timedOut']
            command_count += 1
    failures = json.loads((OUT / 'helper-commands.json').read_text())
    assert [r['exitCode'] for r in failures] == [1, 0]
    assert sha(gzip.decompress((OUT / 'helper-first.py.gz').read_bytes())) == failures[0]['helperSourceSha256']
    assert sha((OUT / 'review.py').read_bytes()) == failures[1]['helperSourceSha256']
    provenance = json.loads((OUT / 'final-communication-provenance.json').read_text())
    assert not provenance['missingBranches']
    assert not any(r['ambiguous'] or r['divergentRevisions'] for r in provenance['files'].values())
    print(json.dumps({'receipts': 2, 'sourceEntriesStable': 429, 'producerTrials': 28,
        'retainedCommands': command_count, 'communicationPaths': len(provenance['files']),
        'executionAuthorized': False, 'gateF': 'NOT_RUN'}, indent=2))


if __name__ == '__main__':
    main()
