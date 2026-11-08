"""Verify exact peer notes, owner ABI copies and differential evidence pins.

Peer differential execution is intentionally not rerun: its scope and counts
remain owner claims. This review verifies its immutable source/output hashes.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


rows = []
for owner, commit, path in [
    ('agent-1', '8c0285ffa6986858caeb0140b930bf5db759fdc0', 'communication/agent-1/outbox/0116-note-governance-getters-and-d50-open.md'),
    ('agent-2', 'beab2d1e9545ae5df3b0867503c47750f42446c8', 'communication/agent-2/outbox/0062-note-d50-differential-against-a3-0081.md')]:
    raw = git('show', commit + ':' + path)
    assert git('log', '-1', '--format=%H', commit, '--', path).decode().strip() == commit
    assert subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'origin/' + owner], cwd=ROOT).returncode == 0
    rows.append({'owner': owner, 'commit': commit, 'path': path, 'sha256': sha(raw), 'classification': 'owner NOTE, not an ACK or source READY'})

commit = rows[1]['commit']
directory = 'protocol/v2-review/d50-differential/'
raw = git('show', commit + ':' + directory + 'MANIFEST.sha256')
entries = {}
for line in raw.decode().splitlines():
    h, name = line.split(maxsplit=1)
    payload = git('show', commit + ':' + directory + name)
    assert sha(payload) == h
    entries[name] = h
provenance = json.loads((ROOT / 'evaluation/fixtures/f/abi/PROVENANCE.json').read_text())
for name, pin in provenance['files'].items():
    raw = git('show', provenance['sourceCommit'] + ':' + pin['sourcePath'])
    assert sha(raw) == pin['sha256']
    assert (ROOT / 'evaluation/fixtures/f/abi' / (name + '.json')).read_bytes() == raw
data = {'notes': rows, 'differentialManifestSha256': sha(git('show', commit + ':' + directory + 'MANIFEST.sha256')),
    'differentialFiles': entries, 'differentialRerun': False,
    'differentialScope': 'owner-reported equal B/hash on 3 synthetic carriers and 178 fault verdicts; normalized facts depend on Agent3 expected-view builder; not an independent oracle',
    'exactOwnerAbiFiles': len(provenance['files']),
    'ruling': 'Keep frozen D50 S0 unchanged; evaluator separately acquires and checks both required Governance getters. No new ACK inferred.'}
(OUT / 'peer-review.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(data, indent=2))
