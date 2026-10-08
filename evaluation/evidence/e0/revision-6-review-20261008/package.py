import hashlib,json
from pathlib import Path
root=Path('/home/karma/Documents/RIS')
def sha(p):return hashlib.sha256((root/p).read_bytes()).hexdigest()
base=json.loads((root/'interfaces/proposals/v1/review-manifest.json').read_text())
extra=['evaluation/scenarios/e0_supplement_cases.json','evaluation/tests/test_revision6_review.py','interfaces/proposals/v1/revision6/DELTA.md']
paths=sorted(set(base['files'])|set(extra))
files={p:sha(p) for p in paths}
manifest=dict(status='candidate v1 revision6, NOT frozen',respondsTo=['A1-0020','A1-0021','A2-0010','A2-0011'],
 base=dict(commit='3e0300a341aa577db8659d5e2e2d4792259dda4a',manifestSha256=sha('interfaces/proposals/v1/review-manifest.json')),
 files=files,changedPaths=[p for p,h in base['files'].items() if files[p]!=h],newPaths=extra,
 changedDefinitions=['E0CaseStep','E0CaseFixture'],newDefinitions=[],
 unchangedScope='All85 other definitions, signed vectors, eight production operations, root lock/toolchain, source-map and positive oracles.',
 ledgerPin=dict(commit='e6cf4ff3a25bfe9f12da6e7f5c6b1563a194c07e',manifestSha256='5866921aa8ba4716a24afb4144123295f0e5f809296ed488a06bc84f07c277a9',entries=100),
 protocolE0Pin=dict(commit='a4dcade3dc3bf01e172a4a5ba30a40fc7ad97292',manifestSha256='6631d61369fab446d503053181ad9b2f1f9df73608ebe085e1907cb7844c8070',entries=94,serviceReady=False,paperRelease='production refuses; option(c) spike only'),
 caseExecutionStatus='48 amended +8 supplement schedules: NOT_RUN. Native mutant counterparts specified prospectively in qualifications.',
 scope='Exact affected reviews pending; no normative v1, INTERFACE_READY, E1 unlock, service/freeze or gate.')
out=root/'interfaces/proposals/v1/revision6/review-manifest.json'
out.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(manifestSha256=sha(str(out.relative_to(root))),files=len(files),changed=manifest['changedPaths'],new=extra),indent=2))
