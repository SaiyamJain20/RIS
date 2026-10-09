import hashlib, importlib.metadata, json, subprocess, tarfile, tempfile, io
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/karma/Documents/RIS')
RUN = Path(__file__).resolve().parent
COMMANDS = []
A1 = '8aedd0cfcad2cdd659500778e23ce357740cf487'
A2 = 'a4dcade3dc3bf01e172a4a5ba30a40fc7ad97292'
A2_PREV = '27c51d2334f275041230b16c505522615621f553'
A3 = 'bf108237fc522c9177df832185d9c6c7d68137b0'
LEDGER = 'e6cf4ff3a25bfe9f12da6e7f5c6b1563a194c07e'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def cmd(name, argv, cwd=ROOT, expected=0):
    start = now()
    p = subprocess.run(argv, cwd=cwd, capture_output=True)
    for stream,b in [('stdout',p.stdout),('stderr',p.stderr)]: (RUN/f'{name}.{stream}').write_bytes(b)
    COMMANDS.append(dict(name=name, argv=list(map(str,argv)), cwd=str(cwd), startedAt=start,
        endedAt=now(), exitCode=p.returncode, stdoutSha256=sha(p.stdout), stderrSha256=sha(p.stderr)))
    (RUN/'audit-commands.json').write_text(json.dumps(COMMANDS,indent=2)+'\n')
    assert p.returncode == expected, (name,p.returncode)
    return p.stdout
def git(name,*args): return cmd(name,['git',*args])
def manifest(pin,path,label):
    data=git(label+'-manifest','show',pin+':'+path)
    entries={}
    for i,line in enumerate(data.decode().splitlines()):
        h,p=line.split(None,1);p=p.strip()
        b=git(label+'-file-'+str(i),'show',pin+':'+p)
        assert sha(b)==h,p
        entries[p]=h
    return dict(pin=pin,path=path,sha256=sha(data),entries=entries)
assert git('branch','branch','--show-current').decode().strip()=='agent-3'
assert git('status','status','--porcelain=v1')==b''
assert git('head','rev-parse','HEAD').decode().strip()==A3
state=json.loads((RUN/'peer-communication-before.json').read_text())
assert state['branches']['origin/agent-1']==A1 and state['branches']['origin/agent-2']==A2
assert not state['missingBranches'] and not any(f['ambiguous'] or f['divergentRevisions'] for f in state['files'].values())
docs=['AGENTS.md','README.md','communication/COMMON_AGENT_CONTEXT.md','communication/agent-3/ROLE.md',
 'communication/BOARD.md','communication/GATES.md','communication/DECISIONS.md','communication/INTEGRATION.md',
 'SPEC.md','PLAN.md','interfaces/README.md','communication/PROTOCOL.md','communication/agent-3/STATUS.md',
 'communication/agent-3/HANDOFF.md','communication/E0_ACCEPTANCE.md','communication/E0_REVIEW_A2_0009.md']
documents={p:sha((ROOT/p).read_bytes()) for p in docs}
for p,f in state['files'].items():
    if not p.startswith(('communication/agent-1/','communication/agent-2/')):
        assert sha((ROOT/p).read_bytes())==f['sha256'],p
messages=[]
for pin,path in [(A1,'communication/agent-1/outbox/0021-review-a2-0010-paper-grant-recipient.md'),
 (A2_PREV,'communication/agent-2/outbox/0010-ack-supplement-revision2-paper-review-and-tool.md'),
 (A2,'communication/agent-2/outbox/0011-review-x1-option-c-spike.md')]:
    b=git('message-'+path.split('/')[-1],'show',pin+':'+path)
    change=git('message-change-'+path.split('/')[-1],'log','-1','--format=%H %cI',pin,'--',path).decode().strip()
    messages.append(dict(path=path,pin=pin,sha256=sha(b),change=change))
package=json.loads((ROOT/'interfaces/proposals/v1/review-manifest.json').read_text())
for p,h in package['files'].items(): assert sha((ROOT/p).read_bytes())==h,p
assert sha((ROOT/'communication/E0_REVIEW_A2_0009.md').read_bytes())=='b3fb3e7732310f231aafcda20bbaf4f7b8a772ce039a158dba3892c50682d88c'
owners=[manifest(LEDGER,'ledger/evidence/source-manifest.sha256','ledger'),
 manifest(A2_PREV,'protocol/evidence/source-manifest.sha256','protocol-0010'),
 manifest(A2,'protocol/evidence/source-manifest.sha256','protocol-0011')]
assert git('ledger-stability','diff','--name-only',LEDGER,A1,'--','ledger')==b''
git('protocol-new-diff','diff','5e203d0c0b26235c4618548a797d93201275a14d',A2,'--','protocol')
adapter=json.loads(git('adapter','show',A2+':protocol/exports/adapter.json'))
assert adapter['interfaceVersion']=='candidate v1 revision 5 (NOT frozen)'
tools=json.loads((ROOT/'evaluation/toolchain.json').read_text())
toolchecks={}
for label,item in list(tools['foundry']['binaryPaths'].items())+[(k,tools[k]) for k in ['solc','proverif']]:
    assert sha(Path(item['path']).read_bytes())==item.get('sha256',item.get('binarySha256')),label
    toolchecks[label]=item
assert sha((ROOT/'uv.lock').read_bytes())==tools['pythonLock']['sha256']
cmd('python-version',[str(ROOT/'.venv/bin/python'),'--version'])
cmd('git-version',['git','--version'])
snapshot=Path(tempfile.mkdtemp(prefix='hmbc-a3-a2-e0-a4dcade-'))
raw=git('protocol-archive','archive',A2,'protocol')
with tarfile.open(fileobj=io.BytesIO(raw)) as archive: archive.extractall(snapshot,filter='data')
for p,h in owners[-1]['entries'].items(): assert sha((snapshot/p).read_bytes())==h,p
result=dict(startedAt=COMMANDS[0]['startedAt'],endedAt=now(),branches=state['branches'],
 communicationFiles=len(state['files']),documentsRead=documents,newMessages=messages,
 packageRevision5=dict(manifestSha256=sha((ROOT/'interfaces/proposals/v1/review-manifest.json').read_bytes()),files=package['files']),
 owners=owners,adapter=adapter,toolChecks=toolchecks,rootLockSha256=sha((ROOT/'uv.lock').read_bytes()),
 packageVersions={p:importlib.metadata.version(p) for p in ['eth-account','jsonschema','pytest']},
 snapshot=str(snapshot),sourcePaper=dict(pdfSha256=sha((ROOT/'references/HMBC2020.pdf').read_bytes()),
 textSha256=sha((ROOT/'references/HMBC2020.txt').read_bytes()),section='III-D3, PDF page 10',
 conclusion='PSC encrypts response to user public key; registered-key realization is an explicit symbolic reconstruction choice.'),
 assumptions='Synthetic HMBC2020 paper-derived reconstruction; safe ledgers and trusted worker/witness; Option A custody.',
 limitations='Static owner review/E0 snapshot only. No owner live/mutation/spike test executed, no service READY, E1/F/G locked.')
(RUN/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(messages=messages,communicationFiles=len(state['files']),
 ownerEntries=[len(o['entries']) for o in owners],snapshot=str(snapshot),commands=len(COMMANDS)),indent=2))
