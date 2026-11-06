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
base = 'b8d57cd3bc4a4a1de1ae267923509d840446aabf'
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
    review='Read exact owner STATUS/HANDOFF, new pool driver and virtual transport, tests/mutation evidence. Driver feeds an existing collection through injected transport. Four owner services share one fake ledger view and virtual time. Explicitly NOT_READY; no new ACK or READY.',
    ownerReportedOnly='12 driver tests,15/15 mutants after initial13/18 and three equivalent removals; NOT rerun or adopted as independent evidence. Owner states implementation preceded tests; moving module aside produced ceremonial RED, not tests-first proof.',
    remaining='witness handlers/startup/CLI wiring, full successor consumer mapping, real chain view/transport/process clock, D6/hooks/byzantine, full E parity and ONE source READY')
(OUT / 'peer-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
