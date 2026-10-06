"""E integration preflight: record explicit blockers rather than synthesize success.

C-E1 provider execution will be implemented against the frozen public adapter
and manifests after E0. This entry point does not start unfrozen service code.
"""
import argparse
import json
import platform
import subprocess
from pathlib import Path
from evaluation.manifests import now,source_manifest

ROOT=Path(__file__).resolve().parents[1]
PROFILES=('paper-strict','paper-minimal','repaired-e')


def run(rq,profile,output):
    if rq!='E':raise ValueError('NOT_IMPLEMENTED_IN_PHASE: F/G remain locked')
    if profile not in PROFILES:raise ValueError('Unsupported preflight profile')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    started=now();source=source_manifest(ROOT)
    missing=[]
    freeze=ROOT/'interfaces/v1/FREEZE.json'
    if not freeze.is_file():missing.append('E0 exact three-agent ACK/source/schema/vector freeze is absent')
    for path in ('ledger/exports/abi/manifest.json','protocol/exports/adapter.json'):
        if not (ROOT/path).is_file():missing.append(path+' is absent from this integration checkout; review and pin owner handoff before execution')
    missing.append('Real provider execution awaits frozen agent-2 input/result/deployment contract; no E1 integration is claimed')
    manifest={'runId':output.name,'rq':rq,'profile':profile,'interfaceVersion':'v0 proposed','adapterMode':'symbolic','executionMode':'preflight','status':'BLOCKED','sourceManifest':source,'sourceStable':source==source_manifest(ROOT),'toolVersions':{'python':platform.python_version()},'commands':[],'inputHashes':{},'seed':None,'startedAt':started,'endedAt':now(),'exitCodes':[2],'resultFiles':{},'blockers':missing,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirtyTree':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines()}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rq',choices=['E','F','G'],required=True)
    parser.add_argument('--profile',choices=PROFILES,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:result=run(args.rq,args.profile,args.output)
    except (ValueError,FileExistsError) as error:parser.exit(2,str(error)+'\n')
    print(json.dumps({'status':result['status'],'manifest':str(args.output/'manifest.json'),'blockers':result['blockers']},indent=2))
    return 2


if __name__=='__main__':raise SystemExit(main())
