import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/karma/Documents/RIS')
RUN = Path(__file__).resolve().parent
COMMANDS = []
READS = []
BASELINE = '02e09c32b088ad8c946932ab5b2c2d901b3eb91f'
A1 = '012f24c7427f2106fc3166db3d540c8254d56a27'
A2 = '5e203d0c0b26235c4618548a797d93201275a14d'
LEDGER_PIN = 'e6cf4ff3a25bfe9f12da6e7f5c6b1563a194c07e'
SUPPLEMENT = 'b3fb3e7732310f231aafcda20bbaf4f7b8a772ce039a158dba3892c50682d88c'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def command(name, argv):
    started = now()
    p = subprocess.run(argv, cwd=ROOT, capture_output=True)
    for stream, data in [('stdout', p.stdout), ('stderr', p.stderr)]:
        (RUN / (name + '.' + stream)).write_bytes(data)
    COMMANDS.append(dict(name=name, argv=argv, cwd=str(ROOT), startedAt=started,
                         endedAt=now(), exitCode=p.returncode,
                         stdoutSha256=sha(p.stdout), stderrSha256=sha(p.stderr)))
    (RUN / 'commands.json').write_text(json.dumps(COMMANDS, indent=2) + '\n')
    if p.returncode:
        raise RuntimeError(f'{name}: {p.returncode}')
    return p.stdout

def git(*args):
    argv = ['git', *args]
    p = subprocess.run(argv, cwd=ROOT, capture_output=True)
    READS.append(dict(argv=argv, cwd=str(ROOT), exitCode=p.returncode,
                      stdoutSha256=sha(p.stdout), stderrSha256=sha(p.stderr)))
    if p.returncode:
        raise RuntimeError(str(argv))
    return p.stdout

started = now()
assert command('branch', ['git', 'branch', '--show-current']).decode().strip() == 'agent-3'
assert command('initial-status', ['git', 'status', '--porcelain=v1']) == b''
command('fetch', ['git', 'fetch', 'origin'])
command('peer-scan', [str(ROOT / '.venv/bin/python'), '-m', 'evaluation.peers',
                      '--output', str(RUN / 'peer-communication.json')])
state = json.loads((RUN / 'peer-communication.json').read_text())
assert not state['missingBranches']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in state['files'].values())
assert state['branches']['origin/agent-1'] == A1
assert state['branches']['origin/agent-2'] == A2
assert state['branches']['origin/agent-3'] == BASELINE
assert git('rev-parse', 'HEAD').decode().strip() == BASELINE

docs = ['AGENTS.md', 'README.md', 'communication/COMMON_AGENT_CONTEXT.md',
        'communication/agent-3/ROLE.md', 'communication/BOARD.md', 'communication/GATES.md',
        'communication/DECISIONS.md', 'communication/INTEGRATION.md', 'SPEC.md', 'PLAN.md',
        'interfaces/README.md', 'communication/PROTOCOL.md', 'communication/agent-3/STATUS.md',
        'communication/agent-3/HANDOFF.md', 'communication/E0_ACCEPTANCE.md',
        'communication/E0_REVIEW_A2_0009.md', 'evaluation/README.md', 'references/README.md']
documents = {p: sha((ROOT / p).read_bytes()) for p in docs}
for path, record in state['files'].items():
    if not path.startswith(('communication/agent-1/', 'communication/agent-2/')):
        assert sha((ROOT / path).read_bytes()) == record['sha256'], path

messages = []
for path, record in state['files'].items():
    if '/outbox/' not in path or not path.endswith('.md'):
        continue
    owner = path.split('/')[1]
    ref = 'origin/' + owner
    data = git('show', state['branches'][ref] + ':' + path)
    fields = {}
    for line in data.decode().splitlines():
        if ': ' in line:
            key, value = line.split(': ', 1)
            if key in ('Message-ID', 'From', 'To', 'Cc', 'Task', 'Type', 'Responds-to'):
                fields[key] = value
    if 'agent-3' in fields.get('To', '') or 'all' in fields.get('To', ''):
        messages.append(dict(path=path, commit=state['branches'][ref],
                             changeCommit=record['changeCommit'], sha256=sha(data), fields=fields))
new_messages = [m for m in messages if m['fields'].get('Message-ID') == 'A1-0020']
assert len(new_messages) == 1
assert not [m for m in messages if m['fields'].get('From') == 'agent-2'
            and int(m['fields']['Message-ID'].split('-')[1]) > 9]
ack = git('show', A1 + ':communication/agent-1/outbox/0020-ack-supplement-revision2.md')
supplement_path = 'communication/E0_REVIEW_A2_0009.md'
assert sha((ROOT / supplement_path).read_bytes()) == SUPPLEMENT
assert sha(git('show', '09c589dd033719536ca624af305a35e4f5183856:' + supplement_path)) == SUPPLEMENT
assert SUPPLEMENT.encode() in ack
assert b'agent 1\'s response to the supplement is complete' in ack

manifest_path = 'interfaces/proposals/v1/review-manifest.json'
manifest_bytes = (ROOT / manifest_path).read_bytes()
assert sha(manifest_bytes) == '124b95eb2830e422e79d0cee4b4b7ae28bf235239740980b984d7f9de2f9d8d0'
package = json.loads(manifest_bytes)['files']
assert len(package) == 32
for path, digest in package.items():
    assert sha((ROOT / path).read_bytes()) == digest
    assert sha(git('show', '3e0300a341aa577db8659d5e2e2d4792259dda4a:' + path)) == digest

owners = []
for ref, pin, module, manifest_hash, count in [
    ('origin/agent-1', LEDGER_PIN, 'ledger',
     '5866921aa8ba4716a24afb4144123295f0e5f809296ed488a06bc84f07c277a9', 100),
    ('origin/agent-2', A2, 'protocol',
     'a352f339f3c874cbb5634efffd1478abbc0b098292ec1d7ba97d348d76b4cdac', 89)]:
    tip = state['branches'][ref]
    path = module + '/evidence/source-manifest.sha256'
    data = git('show', pin + ':' + path)
    assert sha(data) == manifest_hash
    entries = []
    for line in data.decode().splitlines():
        digest, file = line.split(maxsplit=1)
        file = file.removeprefix('*')
        assert sha(git('show', pin + ':' + file)) == digest
        assert sha(git('show', tip + ':' + file)) == digest
        change = git('log', '-1', '--format=%H', tip, '--', file).decode().strip()
        entries.append(dict(path=file, sha256=digest, changeCommit=change))
    assert len(entries) == count
    assert git('diff', '--name-only', pin, tip, '--', module + '/') == b''
    owners.append(dict(ref=ref, tip=tip, pin=pin, manifestPath=path,
                       manifestSha256=manifest_hash, entries=entries))

psc = git('show', LEDGER_PIN + ':ledger/src/PSC.sol')
section = psc.decode().split('function _checkReceipt(', 1)[1].split('// ------------------------------------------------------------------', 1)[0]
assert section.index('return ErrorCode.WRONG_SUBJECT') < section.index('return QuorumLib.verify(')
assert 'g.requestDigest != requestDigest || g.gid != rec.gid || g.dataId != rec.dataId' in section
source_paths = git('ls-tree', '-r', '--name-only', LEDGER_PIN, 'ledger/src/').decode().splitlines()
quorum_paths = [p for p in source_paths if b'library QuorumLib {' in git('show', LEDGER_PIN + ':' + p)]
assert len(quorum_paths) == 1
quorum_path = quorum_paths[0]
quorum = git('show', LEDGER_PIN + ':' + quorum_path)
assert b'BAD_SIGNATURE' in quorum
adapter = json.loads(git('show', A2 + ':protocol/exports/adapter.json'))
assert len(adapter['operations']) == 8
assert 'revision 3' in adapter['interfaceVersion']

toolchain = json.loads((ROOT / 'evaluation/toolchain.json').read_text())
tools = []
for name, item in [('uv.lock', toolchain['pythonLock']), *toolchain['foundry']['binaryPaths'].items(),
                   ('solc', toolchain['solc']), ('proverif', dict(path=toolchain['proverif']['path'],
                    sha256=toolchain['proverif']['binarySha256']))]:
    path = Path(item['path'])
    path = path if path.is_absolute() else ROOT / path
    assert sha(path.read_bytes()) == item['sha256']
    tools.append(dict(name=name, path=str(path), sha256=item['sha256']))
command('python-version', [str(ROOT / '.venv/bin/python'), '--version'])
command('git-version', ['git', '--version'])
command('prompts-check', [str(ROOT / '.venv/bin/python'), 'communication/build_prompts.py', '--check'])
assert command('final-status', ['git', 'status', '--porcelain=v1']) == b''
result = dict(startedAt=started, endedAt=now(), classification='static reconstruction/source review',
              branches=state['branches'], communicationFiles=len(state['files']),
              documentsRead=documents, addressedMessages=messages, newAddressedMessages=new_messages,
              acceptedSupplement=dict(path=supplement_path, sha256=SUPPLEMENT,
                reviewedCommit='09c589dd033719536ca624af305a35e4f5183856',
                messageCommit=A1, messageSha256=sha(ack), scope='Agent1 ledger conditions only'),
              unchangedPackage=package, ownerChecks=owners, toolChecks=tools,
              receiptStaticReview=dict(pin=LEDGER_PIN, pscSha256=sha(psc), source=section,
                  quorumPath=quorum_path, quorumSha256=sha(quorum),
                  conclusion='binding precedes quorum: modified bound field/original signature rejects WRONG_SUBJECT in repaired-e; with binding removed BAD_SIGNATURE. Static review, not execution.'),
              adapterInterface=adapter['interfaceVersion'], adapterOperations=adapter['operations'],
              gitReadCommands=READS,
              assumptions='Synthetic fixtures, HMBC2020 paper-derived reconstruction; Option A custody preserved; exact bytes establish stability, not runtime correctness.',
              limitations='No module/schema/service/formal test repeated. Prior results historical;48 schedules NOT_RUN. E0 waiting Agent2 exact supplement/paper-profile expectation ACK and export label correction. E1/F/G locked. No services/freeze.',
              explorationFailures=[dict(exitCode=2, command='sed -n 1,270p runs/a2-ack-20261008/monitor.py',
                  reason='nonexistent helper path; actual helpers located with rg --files; no repository write'),
                dict(exitCode=128, command='git show 5e203d0:communication/agent-2/outbox/0009-ack-candidate-revision-5.md',
                  reason='incorrect guessed filename; ls-tree located actual 0009-ready-e0-revision5-scoped-ack-and-candidate-b-e1.md, read successfully')])
(RUN / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(evidence=str(RUN), communicationFiles=len(state['files']),
                     newMessages=[m['fields']['Message-ID'] for m in new_messages],
                     packageFiles=32, ownerEntries=[len(o['entries']) for o in owners],
                     commands=len(COMMANDS), reviewSha256=sha((RUN/'review.json').read_bytes()),
                     ackSha256=sha(ack)), indent=2))
