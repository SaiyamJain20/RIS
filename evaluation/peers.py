"""Read newest communication file revisions across fetched parallel branches.

No checkout, merge, commit or push occurs. Git commit timestamps are recorded
provenance, not a proof of synchronized clocks. Incomparable revisions with
changed content must be reviewed; this tool never fabricates an ACK.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from evaluation.manifests import now


def select_revision(candidates):
    newest=max(c['changeTime'] for c in candidates)
    latest=[c for c in candidates if c['changeTime']==newest]
    chosen=sorted(latest,key=lambda c:c['ref'])[0]
    return {**chosen,'ambiguous':len({c['sha256'] for c in latest})>1,'candidates':candidates}


def scan(root):
    def git(*argv):return subprocess.check_output(['git',*argv],cwd=root)
    refs=git('for-each-ref','--format=%(refname)','refs/remotes/origin/').decode().splitlines()
    refs=[r.removeprefix('refs/remotes/') for r in refs if r!='refs/remotes/origin/HEAD']
    branches={r:git('rev-parse',r).decode().strip() for r in refs}
    candidates={}
    for ref in refs:
        for path in git('ls-tree','-r','--name-only',ref,'communication/').decode().splitlines():
            change=git('log','-1','--format=%H %ct',ref,'--',path).decode().strip().split()
            content=git('show',f'{ref}:{path}')
            candidates.setdefault(path,[]).append({'ref':ref,'commit':branches[ref],'changeCommit':change[0],'changeTime':int(change[1]),'sha256':hashlib.sha256(content).hexdigest()})
    files={}
    for path,items in sorted(candidates.items()):
        heads=[]
        for candidate in items:
            obsolete=any(candidate['changeCommit']!=other['changeCommit'] and subprocess.run(['git','merge-base','--is-ancestor',candidate['changeCommit'],other['changeCommit']],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0 for other in items)
            if not obsolete:heads.append(candidate)
        record=select_revision(heads)
        record['candidates']=items
        files[path]=record
    # Expose divergent non-ancestral edits (even with differing timestamps).
    for path,record in files.items():
        chosen=record['changeCommit'];divergent=[]
        for other in record['candidates']:
            if other['sha256']==record['sha256']:continue
            ancestor=subprocess.run(['git','merge-base','--is-ancestor',other['changeCommit'],chosen],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode
            if ancestor!=0:divergent.append(other['changeCommit'])
        record['divergentRevisions']=sorted(set(divergent))
    return {'capturedAt':now(),'branches':branches,'missingBranches':[f'origin/agent-{n}' for n in (1,2,3) if f'origin/agent-{n}' not in branches],'files':files,'note':'Chosen by newest file-changing commit after ancestry review. Inspect divergentRevisions before relying on conflicting shared instructions. Remote file contents are read with git show; immutable messages never overwritten.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=scan(args.root);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'branches':result['branches'],'missingBranches':result['missingBranches'],'files':len(result['files'])},indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
