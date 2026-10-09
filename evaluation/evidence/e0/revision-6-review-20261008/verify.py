import concurrent.futures,csv,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/home/karma/Documents/RIS');RUN=Path(__file__).resolve().parent
def now():return datetime.now(timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
audit=json.loads((RUN/'audit.json').read_text());snap=Path(audit['snapshot'])
manifest=json.loads((ROOT/'interfaces/proposals/v1/revision6/review-manifest.json').read_text())
pre={p:sha((ROOT/p).read_bytes()) for p in manifest['files']}
assert pre==manifest['files']
old=json.loads(subprocess.check_output(['git','show','3e0300a:interfaces/proposals/v1/hmbc.schema.json'],cwd=ROOT))['$defs']
new=json.loads((ROOT/'interfaces/proposals/v1/hmbc.schema.json').read_text())['$defs']
assert set(old)==set(new)
changed=[k for k in old if old[k]!=new[k]]
assert set(changed)=={'E0CaseStep','E0CaseFixture'}
before=json.loads(subprocess.check_output(['git','show','3e0300a:evaluation/scenarios/e0_cases.json'],cwd=ROOT))['cases']
after=json.loads((ROOT/'evaluation/scenarios/e0_cases.json').read_text())['cases']
assert [c['id'] for c in before]==[c['id'] for c in after]
for a,b in zip(before,after):
    assert a['steps']==b['steps']
    assert {k:v for k,v in a['expected'].items() if k!='qualification'}=={k:v for k,v in b['expected'].items() if k!='qualification'}
    assert a['executionStatus']==b['executionStatus']=='NOT_RUN'
for p,h in audit['owners'][-1]['entries'].items():assert sha((snap/p).read_bytes())==h,p
python=str(ROOT/'.venv/bin/python')
jobs=[('owned-final',[python,'-m','pytest','evaluation/tests','-q'],ROOT),
 ('peer-final',[python,'-m','pytest','-c','pytest.ini','--rootdir','.',
    'tests/test_boundary_review_r5.py','tests/test_candidate_schema_review.py','tests/test_exports.py','tests/test_eip712_vs_agent1.py','-q'],snap/'protocol'),
 ('peer-exports',[python,'-m','hmbc_protocol.export','--check'],snap/'protocol'),
 ('schema-final',[python,'-m','evaluation.check_schema_vectors','interfaces/vectors/schema-candidate.json','interfaces/vectors/boundary-candidate.json','--output',str(RUN/'schema-final-results.json')],ROOT),
 ('vectors-final',[python,'-m','evaluation.vectors','interfaces/vectors/eip712-agent1-candidate.json'],ROOT),
 ('boundary-generator',[python,'interfaces/proposals/build_boundary_vectors.py','--check'],ROOT),
 ('prompts-final',[python,'communication/build_prompts.py','--check'],ROOT)]
def execute(job):
    name,argv,cwd=job;started=now();p=subprocess.run(argv,cwd=cwd,capture_output=True)
    for stream,b in [('stdout',p.stdout),('stderr',p.stderr)]: (RUN/f'{name}.{stream}').write_bytes(b)
    rec=dict(name=name,argv=argv,cwd=str(cwd),startedAt=started,endedAt=now(),exitCode=p.returncode,
        stdoutSha256=sha(p.stdout),stderrSha256=sha(p.stderr))
    (RUN/f'{name}-command.json').write_text(json.dumps(rec,indent=2)+'\n')
    return rec
started=now()
(RUN/'verification-source-before.json').write_text(json.dumps(pre,indent=2)+'\n')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: commands=list(pool.map(execute,jobs))
post={p:sha((ROOT/p).read_bytes()) for p in manifest['files']}
assert pre==post
for p,h in audit['owners'][-1]['entries'].items():assert sha((snap/p).read_bytes())==h,p
result=dict(startedAt=started,endedAt=now(),commands=commands,sourceManifest=pre,sourceStable=pre==post,
 peerSnapshotStable=True,peerPin=audit['owners'][-1]['pin'],changedDefinitions=changed,
 old48ExpectedOutcomesStepsCountsPreserved=True,reviewManifestSha256=sha((ROOT/'interfaces/proposals/v1/revision6/review-manifest.json').read_bytes()),
 evidenceClass='E0 schema/vector/module compatibility only',limits='No live fixture/services/owner mutation/spike/formal query;56 schedules NOT_RUN; E0/E1/F/G gates unchanged.')
(RUN/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(exitCodes=[c['exitCode'] for c in commands],sourceStable=pre==post,
 peerStable=True,changedDefinitions=changed,manifest=result['reviewManifestSha256']),indent=2))
assert all(c['exitCode']==0 for c in commands)
