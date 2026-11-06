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
base = '9184e3bbd961f5cf461320a9ef3edaceeea76af7'
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
    review='Read complete Byzantine endpoint module, checkpoint variant tests and mutation definitions, D6 strict-loader delta/tests and latest owner state. Real services/stores/pool with one fake ledger and virtual transport; checkpoint only. Repeater/equivocator valid first reply can count once; other invalid replies excluded. View override explicitly breaks safe-ledger assumption. Explicit NOT_READY.',
    ownerReportedOnly='D6 seven tests (six RED), four handcrafted mutants. Byzantine22 tests,15/16 then16/16 mutants; survivor test gap fixed. Counts NOT rerun or adopted as evaluator results. Full E regressions not run.',
    remaining='CLI/real wiring, actual transport/processes/chain view, H5 worker variant, other three signed message types, full E regressions, A3-0079 complete mapping and ONE complete source READY listing worker_log.py and deviating_witness.py',
    noExecutionAuthority=True)
(OUT / 'peer-review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
