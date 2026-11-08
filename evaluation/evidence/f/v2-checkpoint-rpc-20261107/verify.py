"""Verify retained command bytes once; own receipt checked separately later."""
import gzip
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
before=json.loads((OUT/'inputs-before.json').read_text())
after=json.loads((OUT/'inputs-after.json').read_text())
assert after['unchangedOwnerPaths']==len(before['sourcePins'])
assert after['unchangedLocalInputs']==len(before['localInputs'])
assert after['unchangedHelpers']==len(before['helpers'])-len(after['changedHelpers'])
assert set(after['changedHelpers'])=={'audit.py','mutants.py','verify.py'}
receipts=[]
for path in sorted(OUT.glob('*-command.json')):
    d=json.loads(path.read_text());label=path.name.removesuffix('-command.json')
    assert d['exitCode']==(1 if label in ('red','mutants') else 0),label
    assert not d['timedOut'] and d['cwd']=='/home/karma/Documents/RIS'
    assert sha(gzip.decompress((OUT/(label+'.log.gz')).read_bytes()))==d['outputSha256'],label
    receipts.append(dict(path=path.name,sha256=sha(path.read_bytes()),exitCode=d['exitCode']))
first,last=(json.loads((OUT/p).read_text()) for p in ('communication-before.json','communication-final.json'))
assert first['branches']==last['branches'] and first['files']==last['files']
assert not any(r['ambiguous'] or r['divergentRevisions'] for r in last['files'].values())
core={p.name:sha(p.read_bytes()) for p in sorted(OUT.iterdir())
      if p.is_file() and p.name!='verification.json'}
result=dict(ownerPaths=len(before['sourcePins']),localInputs=len(before['localInputs']),
            helpers=len(before['helpers']),changedHelpers=after['changedHelpers'],
            communicationPaths=len(last['files']),commands=receipts,core=core)
path=OUT/'verification.json';assert not path.exists(),'immutable verification: use fresh evidence directory'
path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(commands=len(receipts),sha256=sha(path.read_bytes()),
                     ownerPaths=result['ownerPaths'],localInputs=result['localInputs'],
                     helpers=result['helpers'],communicationPaths=result['communicationPaths']),indent=2))
