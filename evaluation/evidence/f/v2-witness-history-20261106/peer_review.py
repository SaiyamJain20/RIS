"""Exact read-only provenance of peer deltas; no NOT_READY runtime consumption."""
import hashlib
import json
from pathlib import Path
import subprocess
import re

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


tip = git('rev-parse', 'origin/agent-2').decode().strip()
base = 'eb6e29954786750a1216aa8ea3b3f81929063d66'
paths = git('diff', '--name-only', base, tip, '--', 'protocol').decode().splitlines()
copied = json.loads(git('show', tip + ':protocol/tests/fixtures/agent3-interfaces-provenance.json'))
for local, row in copied['files'].items():
    raw = git('show', tip + ':protocol/tests/fixtures/' + local)
    assert sha(raw) == row['sha256']
    assert raw == git('show', row.get('commit', copied['commit']) + ':' + row['path'])
report = dict(agent1=git('rev-parse', 'origin/agent-1').decode().strip(), agent2=tip, previousAgent2=base,
    protocolPaths={p: dict(sha256=sha(git('show', tip + ':' + p)),
                          fileChangingCommit=git('log', '-1', '--format=%H', tip, '--', p).decode().strip()) for p in paths},
    verifiedFixtureCopies=len(copied['files']),
    newestOutboxes={owner: sorted(p for p in git('ls-tree', '-r', '--name-only', 'origin/' + owner, f'communication/{owner}/outbox').decode().splitlines()
                                 if re.fullmatch(r'communication/agent-[12]/outbox/[0-9]{4}-.+\.md', p))[-1]
                   for owner in ('agent-1', 'agent-2')},
    review='Read exact latest owner state and entire new adapter source. Strict envelope, explicit schema selection, whole manifest equality and injected handlers. Owner explicitly NOT_READY; no new ACK or READY.',
    ownerReportedOnly='96 adapter tests,43/43 mutants; NOT rerun or adopted as independent evidence.',
    remaining='handler/startup/result/CLI wiring, full successor consumer mapping, real chain view/driver, D4/D6/hooks/byzantine, full E parity and ONE source READY')
(OUT / 'peer-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
