import hashlib, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
root = Path('/home/karma/Documents/RIS')
run = Path(__file__).resolve().parent
commands = []
def now(): return datetime.now(timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def command(name, argv):
    start = now()
    proc = subprocess.run(argv, cwd=root, capture_output=True)
    output = run / (name + '.stdout')
    errors = run / (name + '.stderr')
    output.write_bytes(proc.stdout); errors.write_bytes(proc.stderr)
    commands.append(dict(name=name, argv=argv, cwd=str(root), startedAt=start, endedAt=now(), exitCode=proc.returncode, stdout=str(output), stdoutSha256=sha(proc.stdout), stderr=str(errors), stderrSha256=sha(proc.stderr)))
    (run / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    if proc.returncode: raise RuntimeError(f'{name} exited {proc.returncode}')
    return proc.stdout

def git(*args): return subprocess.check_output(['git', *args], cwd=root)
started = now()
branch = command('branch', ['git','branch','--show-current']).decode().strip()
assert branch == 'agent-3'
assert command('initial-status', ['git','status','--porcelain=v1']) == b''
command('fetch', ['git','fetch','origin'])
command('peers', [str(root / '.venv/bin/python'), '-m', 'evaluation.peers', '--output', str(run/'peer-communication.json')])
state = json.loads((run/'peer-communication.json').read_text())
assert not state['missingBranches']
assert not any(v['ambiguous'] or v['divergentRevisions'] for v in state['files'].values())
expected = {'origin/agent-1': '73ae718b917a787bbdee0c3802fe32e265b0d70d', 'origin/agent-2': 'e4e2c9ead8571a2bf1fc932a917f2a6d7f0d461b', 'origin/agent-3': 'b9db5cdace1940fffae40b5babe9267b81b6380d'}
changes = {r: {'previous': old, 'current': state['branches'][r]} for r, old in expected.items() if state['branches'][r] != old}
messages=[]; new_messages=[]; latest_files=[]
for path, item in state['files'].items():
    owner = path.split('/')[1] if path.startswith('communication/agent-') else None
    if owner and '/outbox/' in path:
        ref='origin/'+owner
        data=git('show', ref+':'+path)
        fields={}
        for line in data.decode().splitlines():
            if ': ' in line:
                k,v=line.split(': ',1)
                if k in ('Message-ID','From','To','RQ','Task','Type','Responds-to'): fields[k]=v
        if 'agent-3' in fields.get('To','') or 'all' in fields.get('To',''):
            record={'path':path,'ref':ref,'commit':state['branches'][ref], 'changeCommit':git('log','-1','--format=%H',ref,'--',path).decode().strip(),'sha256':sha(data),'fields':fields}
            messages.append(record)
            sequence=int(fields['Message-ID'].split('-')[1])
            if sequence > {'agent-1':18,'agent-2':8,'agent-3':13}[owner]: new_messages.append(record)
    if owner is None or (owner=='agent-3' and '/outbox/' not in path):
        local=root/path
        assert local.exists() and sha(local.read_bytes()) == item['sha256'], path
manifest_path='interfaces/proposals/v1/review-manifest.json'
manifest_data=(root/manifest_path).read_bytes()
assert sha(manifest_data)=='124b95eb2830e422e79d0cee4b4b7ae28bf235239740980b984d7f9de2f9d8d0'
manifest=json.loads(manifest_data)
package=[]
for path,digest in manifest['files'].items():
    local=(root/path).read_bytes()
    reviewed=git('show','3e0300a341aa577db8659d5e2e2d4792259dda4a:'+path)
    assert sha(local)==digest==sha(reviewed), path
    package.append({'path':path,'sha256':digest,'reviewedCommit':'3e0300a341aa577db8659d5e2e2d4792259dda4a'})
assert len(package)==32
owner_checks=[]
for ref,pin,module,digest in [('origin/agent-1','e6cf4ff3a25bfe9f12da6e7f5c6b1563a194c07e','ledger','5866921aa8ba4716a24afb4144123295f0e5f809296ed488a06bc84f07c277a9'),('origin/agent-2',state['branches']['origin/agent-2'],'protocol',None)]:
    path=module+'/evidence/source-manifest.sha256'
    content=git('show',pin+':'+path)
    if digest: assert sha(content)==digest
    checked=[]
    for line in content.decode().splitlines():
        expected_hash, file=line.split(maxsplit=1); file=file.removeprefix('*')
        assert sha(git('show',pin+':'+file))==expected_hash, file
        assert sha(git('show',state['branches'][ref]+':'+file))==expected_hash, file
        checked.append({'path':file,'sha256':expected_hash})
    if module=='ledger': assert git('diff','--name-only',pin,state['branches'][ref],'--','ledger/')==b''
    owner_checks.append({'ref':ref,'commit':state['branches'][ref],'pin':pin,'manifestPath':path,'manifestSha256':sha(content),'entries':checked})
    change=git('log','-1','--format=%H',ref,'--',module+'/').decode().strip()
    files=git('diff-tree','--root','--no-commit-id','--name-only','-r',change,'--',module+'/').decode().splitlines()
    latest_files.append({'ref':ref,'latestModuleChangeCommit':change,'files':[{'path':p,'changeCommit':git('log','-1','--format=%H',ref,'--',p).decode().strip(),'sha256':sha(git('show',ref+':'+p))} for p in files]})
ref='origin/agent-3'; change=git('log','-1','--format=%H',ref).decode().strip()
files=git('diff-tree','--root','--no-commit-id','--name-only','-r',change).decode().splitlines()
latest_files.append({'ref':ref,'latestChangeCommit':change,'files':[{'path':p,'changeCommit':git('log','-1','--format=%H',ref,'--',p).decode().strip(),'sha256':sha(git('show',ref+':'+p))} for p in files]})
adapter=json.loads(git('show',state['branches']['origin/agent-2']+':protocol/exports/adapter.json'))
operations=[v['name'] for v in adapter['operations']]
missing=sorted({'collect_checkpoint','attest_grant'}-set(operations))
tools=json.loads((root/'evaluation/toolchain.json').read_text())
tool_checks=[]
for name,item in [('uv.lock',tools['pythonLock']),*tools['foundry']['binaryPaths'].items(),('solc',tools['solc'])]:
    path=Path(item['path']); path=path if path.is_absolute() else root/path
    assert sha(path.read_bytes())==item['sha256'], name
    tool_checks.append({'name':name,'path':str(path),'sha256':item['sha256']})
command('python-version',[str(root/'.venv/bin/python'),'--version'])
command('git-version',['git','--version'])
command('final-status',['git','status','--porcelain=v1'])
assert git('rev-parse','HEAD').decode().strip()==state['branches']['origin/agent-3']
assert commands[-1]['stdoutSha256']==sha(b'')
result={'startedAt':started,'endedAt':now(),'classification':'static source/provenance check; no new experiment', 'branches':state['branches'],'branchChangesSincePriorRun':changes,'communicationFiles':len(state['files']),'addressedMessages':messages,'newAddressedMessages':new_messages,'package':package,'ownerChecks':owner_checks,'latestFileChangingRevisions':latest_files,'tools':tool_checks,'adapterInterface':adapter['interfaceVersion'],'adapterOperations':operations,'missingRevision5Operations':missing,'phase':'E/E0; v1 revision5 NOT frozen; E1/F/G locked','assumptions':'Exact source hashes establish byte stability only; no peer owner claim substitutes for gate evidence. Synthetic fixture bytes unchanged.','limitations':'Static scan only. A2-0009 has new scoped ACK; no service READY or integrated result inferred. 48 schedules remain NOT_RUN.'}
(run/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'evidenceDirectory':str(run),'branches':state['branches'],'branchChanges':changes,'newAddressedMessages':new_messages,'communicationFiles':len(state['files']),'packageFilesVerified':len(package),'ownerEntriesVerified':[len(v['entries']) for v in owner_checks],'missingRevision5Operations':missing,'commands':len(commands),'reviewSha256':sha((run/'review.json').read_bytes())},indent=2))
