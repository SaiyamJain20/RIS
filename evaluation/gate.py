"""Phase gate preflight. Never promote claims or unit/stub success to an RQ PASS.

Final E gate adjudication is deliberately unavailable until E0/E1 provide the
frozen artifact/ACK format. This CLI reports remaining evidence and fails closed;
GATES.md remains the mandatory human/peer review checklist.
"""
import argparse
import json
from pathlib import Path
from evaluation.manifests import safe_artifact,sha256

E_CRITERIA=('interface-and-source-review','legitimate-and-denied-controls','E01-E02-E03-classification','repairs-and-mutants','real-two-chain-and-recovery','proverif-and-negative-control','RQ1-report','stable-hashed-input-output-tools','three-matching-acks')


def check_gate(run,rq='E'):
    run=Path(run);missing=[]
    if rq!='E':return {'rq':rq,'decision':'BLOCKED','missing':['Prior RQ gates have not passed; F/G adjudication not implemented in E.']}
    try:manifest=json.loads((run/'manifest.json').read_text())
    except (OSError,ValueError):return {'rq':rq,'decision':'BLOCKED','missing':['Readable manifest.json required',*E_CRITERIA]}
    if not isinstance(manifest,dict):return {'rq':rq,'decision':'BLOCKED','missing':['Manifest must be an object']}
    if manifest.get('rq')!='E':missing.append('RQ mismatch')
    if manifest.get('executionMode')!='real-integrated':missing.append('Real contracts plus agent-2 services required; provided/stub traces are insufficient')
    if manifest.get('interfaceVersion')!='v1':missing.append('Frozen v1 interface required')
    if manifest.get('sourceStable') is not True:missing.append('Stable input source hashes required')
    if manifest.get('status')!='PASS':missing.append('Run did not pass')
    results=manifest.get('resultFiles',{})
    if not isinstance(results,dict) or not results:missing.append('Hashed result artifacts required')
    else:
        for name,expected in results.items():
            try:
                path=safe_artifact(run,name)
                if sha256(path)!=expected:missing.append(f'Hash mismatch: {name}')
            except (OSError,ValueError):missing.append(f'Missing/invalid artifact: {name}')
    try:bundle=json.loads((run/'gate-evidence.json').read_text())
    except (OSError,ValueError):bundle={}
    criteria=bundle.get('criteria',{}) if isinstance(bundle,dict) else {}
    if not isinstance(criteria,dict):criteria={}
    for criterion in E_CRITERIA:
        record=criteria.get(criterion)
        if not isinstance(record,dict) or record.get('status')!='VERIFIED' or not record.get('evidencePaths'):missing.append(criterion)
    # E0 has not defined/frozen the evidence/ACK format. Do not accept fabricated
    # booleans or self-reported strings as the three-agent gate decision.
    missing.append('Final evidence and exact three-peer ACK adjudication pending E0/E1 freeze; automated PASS unavailable')
    return {'rq':rq,'decision':'BLOCKED','missing':missing}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rq',choices=['E','F','G'],required=True)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();result=check_gate(args.run,args.rq)
    print(json.dumps(result,indent=2));return 0 if result['decision']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
