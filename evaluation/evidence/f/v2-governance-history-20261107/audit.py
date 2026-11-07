"""Immutable complete input brackets and exact unchanged peer provenance."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'evaluation/evidence/f/v2-governance-state-20261107/inputs-before.json'
sys.path.insert(0,str(ROOT))
from evaluation.manifests import now
from evaluation.peers import scan

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def write(name,data):
    p=OUT/name;assert not p.exists(), 'immutable evidence'
    p.write_text(json.dumps(data,indent=2)+'\n')
def local_inputs():
    paths=git('ls-files','--cached','--others','--exclude-standard','evaluation','interfaces',
              'pyproject.toml','uv.lock','SPEC.md','PLAN.md','AGENTS.md').decode().splitlines()
    return {p:sha((ROOT/p).read_bytes()) for p in paths if '/evidence/' not in p}
def helpers():
    return {p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.suffix=='.py' or p.name=='PLAN.md'}
def owners():
    prior=json.loads(PRIOR.read_text())
    tips={n:git('rev-parse','origin/agent-'+n).decode().strip() for n in ('1','2','3')}
    assert all(tips[n]==prior['tips'][n] for n in ('1','2')), 'review peer changes first'
    for p,digest in prior['sourcePins'].items():
        commit=tips['1'] if p.startswith('ledger/') else tips['2']
        assert sha(git('show',commit+':'+p))==digest,p
    frozen=0
    for version in ('v1','v2','v2.1'):
        freeze=json.loads((ROOT/f'interfaces/{version}/FREEZE.json').read_text())
        for p,row in freeze.get('frozenCopies',freeze.get('files',{})).items():
            assert sha((ROOT/p).read_bytes())==row['sha256'],p
            frozen+=1
    acceptance=json.loads((ROOT/'communication/F0_ACCEPTANCE_CANDIDATE2.json').read_text())
    assert acceptance['implementationAuthorized'] and not acceptance['executionAuthorized']
    for p,digest in acceptance['protocolF0Files'].items():
        assert sha(git('show',tips['2']+':'+p))==digest,p
    return dict(tips=tips,sourcePins=prior['sourcePins'],priorInputsSha256=sha(PRIOR.read_bytes()),
                frozenFilesChecked=frozen,protocolF0FilesChecked=len(acceptance['protocolF0Files']),
                completeRuntimeReady=False,executionAuthorized=False)
def carried(base):
    assert git('rev-parse','HEAD').decode().strip()==base
    rows={}
    for entry in git('ls-tree','-rz',base).split(b'\0'):
        if not entry:continue
        meta,path=entry.split(b'\t',1);mode,kind,oid=meta.decode().split();path=path.decode()
        assert kind=='blob',path
        p=ROOT/path;data=os.readlink(p).encode() if mode=='120000' else p.read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid,path
        rows[path]=sha(data)
    return dict(baselineCommit=base,trackedPathsChecked=len(rows),
        canonicalPathSha256MapSha256=sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()))

mode=sys.argv[1]
if mode=='before':
    assert git('branch','--show-current').decode().strip()=='agent-3'
    state=owners()
    state.update(recordedAt=now(),localInputs=local_inputs(),helpers=helpers(),
        carried=carried(state['tips']['3']),environmentSha256=sha(json.dumps(dict(os.environ),sort_keys=True).encode()),
        tools=dict(python=sys.version,executable=sys.executable,git=git('--version').decode().strip(),
                   **{p:importlib.metadata.version(p) for p in ('pytest','eth-account','eth-abi','jsonschema')}))
    locks={}
    for name in ('ris-agent3-scheduled.lock','hmbc-coordinator.lock'):
        path=ROOT/'.git'/name
        check=subprocess.run(['flock','-n','-E','75',str(path),'true'])
        assert check.returncode==75,name
        locks[name]=dict(inode=path.stat().st_ino,concurrentExit=check.returncode)
    state['locks']=locks
    write('inputs-before.json',state)
    print(json.dumps(dict(ownerPaths=len(state['sourcePins']),localInputs=len(state['localInputs']),
                         helpers=len(state['helpers']),carried=state['carried'],locks=locks,tools=state['tools']),indent=2))
elif mode=='after':
    before=json.loads((OUT/'inputs-before.json').read_text())
    assert before['localInputs']==local_inputs()
    assert before['sourcePins']==owners()['sourcePins']
    assert before['helpers']==helpers()
    assert before['carried']==carried(before['tips']['3'])
    write('inputs-after.json',dict(recordedAt=now(),ownerPaths=len(before['sourcePins']),
        localInputs=len(before['localInputs']),helpers=len(before['helpers']),carried=before['carried']))
    print((OUT/'inputs-after.json').read_text())
elif mode=='peers':
    result=scan(ROOT)
    assert not result['missingBranches']
    assert not any(v['ambiguous'] or v['divergentRevisions'] for v in result['files'].values())
    write(sys.argv[2],result)
    print(json.dumps(dict(branches=result['branches'],communicationPaths=len(result['files'])),indent=2))
else:raise SystemExit('before/after/peers output-name')
