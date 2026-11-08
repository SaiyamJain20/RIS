"""Read-only provenance; never import or execute a NOT_READY peer runtime."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


tip = git('rev-parse', 'origin/agent-2').decode().strip()
base = '254faacdb2344aabed6bb9f66957fc5101487dd6'
paths = git('diff', '--name-only', base, tip, '--', 'protocol').decode().splitlines()
copied = json.loads(git('show', tip + ':protocol/tests/fixtures/agent3-interfaces-provenance.json'))
for local, row in copied['files'].items():
    raw = git('show', tip + ':protocol/tests/fixtures/' + local)
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    assert raw == git('show', row.get('commit', copied['commit']) + ':' + row['path'])
report = dict(agent1=git('rev-parse', 'origin/agent-1').decode().strip(), agent2=tip,
    previousAgent2=base, verifiedFixtureCopies=len(copied['files']),
    protocolPaths={p: dict(sha256=hashlib.sha256(git('show', tip + ':' + p)).hexdigest(),
        fileChangingCommit=git('log', '-1', '--format=%H', tip, '--', p).decode().strip()) for p in paths},
    newestOutboxes={owner: sorted(p for p in git('ls-tree', '-r', '--name-only', 'origin/' + owner,
        f'communication/{owner}/outbox').decode().splitlines()
        if re.fullmatch(r'communication/agent-[12]/outbox/[0-9]{4}-.+\.md', p))[-1]
        for owner in ('agent-1', 'agent-2')},
    review='Read newest STATUS/HANDOFF, whole adapter_v2_start.py and tests and mutation definitions. Startup composes explicit carrier selection, D50 reconstruction, worker binding and lazy factories. Chain/view/worker/witness transport injected; full manifest not exercised. Explicit NOT_READY.',
    ownerReportedOnly='27 startup tests;15/15 mutants after15/16 with equivalent T16 removed;360 related tests. Full suite NOT rerun. Counts not rerun or adopted as evaluator evidence.',
    remaining='CLI and actual wiring, real chain view/worker factory/transport/processes, A3-0079 full consumer mapping, D6/hooks/byzantine, full E regressions and ONE complete exact source READY',
    noExecutionAuthority=True)
(OUT / 'peer-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
