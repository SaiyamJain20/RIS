"""Re-run owned E0 checks against an explicitly reviewed, pinned peer snapshot.

This runs ledger module tests/toolchain smoke, never E1 service integration.
Extract the acknowledged agent-1 commit using git archive into a scratch directory
before invoking --peer-root; do not point this at a mutable peer working checkout.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from evaluation.manifests import canonical_hash,hash_files,record_command,sha256,source_manifest

ROOT=Path(__file__).resolve().parents[1]
EXPECTED='19273f507edb22fbbb9205ca2a587f764b5d79465fdfd327d751a31c3910f1a0' # A1-0011 READY, ledger 54262c2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--peer-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();peer=args.peer_root.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    toolchain=json.loads((ROOT/'evaluation/toolchain.json').read_text())
    manifest=peer/'ledger/evidence/source-manifest.sha256'
    if sha256(manifest)!=EXPECTED:parser.exit(2,'Peer manifest differs from reviewed A1-0011; review new READY before running\n')
    files={}
    for line in manifest.read_text().splitlines():
        expected,path=line.split('  ',1);files[Path(path)]=expected
    pre_peer=hash_files(peer,files)
    if pre_peer!={str(p):h for p,h in files.items()}:parser.exit(2,'Peer files differ from READY manifest\n')
    before=source_manifest(ROOT)
    for tool in toolchain['foundry']['binaryPaths'].values():
        if sha256(tool['path'])!=tool['sha256']:parser.exit(2,'Pinned Foundry binary hash changed\n')
    if sha256(toolchain['proverif']['path'])!=toolchain['proverif']['binarySha256']:parser.exit(2,'Pinned ProVerif binary hash changed\n')
    env=dict(os.environ)
    for key in list(env):
        if key.startswith('FOUNDRY_'):del env[key]
    env['FOUNDRY_PROFILE']='default'
    env['PATH']=str(Path(toolchain['foundry']['binaryPaths']['forge']['path']).parent)+os.pathsep+env.get('PATH','')
    commands=[]
    def execute(name,argv,expected_exit,cwd=ROOT,override_env=None,timeout=60):
        log=out/(name+'.txt');result=record_command(argv,cwd,log,timeout,override_env or env)
        result.update({'name':name,'expectedExit':expected_exit,'output':log.name,'matchesExpectedExit':result['exitCode']==expected_exit})
        commands.append(result)
        return result
    execute('evaluation-tests',[sys.executable,'-m','pytest','evaluation/tests','-q'],0)
    execute('python-vectors',[sys.executable,'-m','evaluation.vectors','interfaces/vectors/eip712-agent1-candidate.json','--output',str(out/'python-vectors.json')],0)
    schema_check = """import json
from pathlib import Path
from jsonschema import ValidationError
from evaluation.schema import validate
cases=json.loads(Path('interfaces/vectors/schema-candidate.json').read_text())['cases']
mismatches=[]
for i,c in enumerate(cases):
    try: validate(c['schema'],c['input']);actual=True
    except (ValidationError,ValueError): actual=False
    if actual!=c['valid']:mismatches.append(i)
result={'cases':len(cases),'valid':sum(c['valid'] for c in cases),'invalid':sum(not c['valid'] for c in cases),'mismatches':mismatches}
print(json.dumps(result));raise SystemExit(bool(mismatches) or not cases)
"""
    execute('schema-fixtures',[sys.executable,'-c',schema_check],0)
    execute('ledger-tests',[toolchain['foundry']['binaryPaths']['forge']['path'],'test','--root',str(peer/'ledger')],0)
    execute('cast-vectors',[sys.executable,'-I',str(peer/'ledger/tools/crosscheck_cast.py')],0)
    execute('ledger-mutants',[sys.executable,'-I',str(peer/'ledger/tools/check_mutants.py'),str(out/'ledger-mutants.json')],0)
    execute('receipt-outcome-controls',[toolchain['foundry']['binaryPaths']['forge']['path'],'test','--root',str(peer/'ledger'),'--match-contract','OutcomeEvidence'],0)
    execute('proverif-smoke',[toolchain['proverif']['path'],str(ROOT/'evaluation/models/e0/smoke.pv')],0)
    execute('launch-prompts',[sys.executable,'communication/build_prompts.py','--check'],0)
    preflight=out/'preflight'
    execute('runner-preflight',[sys.executable,'-m','evaluation.run','--rq','E','--profile','repaired-e','--output',str(preflight)],2)
    execute('gate-preflight',[sys.executable,'-m','evaluation.gate','--rq','E','--run',str(preflight)],2)
    pv=(out/'proverif-smoke.txt').read_text()
    after=source_manifest(ROOT);post_peer=hash_files(peer,files)
    result={'scope':'E0 compatibility + independent unit preparation; no E1 integration','sourceManifest':before,'sourceManifestSha256':canonical_hash(before),'sourceStable':before==after,'peerReadyManifestSha256':EXPECTED,'peerSourceStable':pre_peer==post_peer,'peerEntries':len(files),'commands':commands,'toolchainSha256':sha256(ROOT/'evaluation/toolchain.json'),'smokeQueriesExpected':'not attacker(publicToken) false; not attacker(secretToken) true','smokeQueryOutputsMatch':'RESULT not attacker(publicToken[]) is false.' in pv and 'RESULT not attacker(secretToken[]) is true.' in pv,'allExpectedOutcomes':all(c['matchesExpectedExit'] for c in commands),'limitations':['Receipt controls are ledger module tests; historical pending failures remain recorded. BLOCKED preflights are not gate successes.','Agent-2 REVIEW is available but its services/schema ACK and exact executable READY remain absent. No frozen interface/real E integration or E model correspondence was run.']}
    result['ok']=result['sourceStable'] and result['peerSourceStable'] and result['allExpectedOutcomes'] and result['smokeQueryOutputsMatch']
    result['resultHashes']={str(p.relative_to(out)):sha256(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('ok','sourceStable','peerSourceStable','allExpectedOutcomes','smokeQueryOutputsMatch')},indent=2))
    return 0 if result['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
