"""Seven deliberate in-memory guard removals; no runtime source is modified."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from evaluation.tests.test_history_rpc_v2 import case, ABI
from evaluation.history_rpc_v2 import collect

PATH=ROOT/'evaluation/history_rpc_v2.py'
SOURCE=PATH.read_text()


def run(fn,label,folder):
    args=case();m,o,e,_,_,clients=args
    over={}
    if label=='origin':clients['pbc'].url='http://127.0.0.1:19999'
    elif label=='call-budget':over['max_calls']=1
    elif label=='identity':clients['pbc'].identities['0x0']['hash']='0x'+'ff'*32
    elif label=='canonical':
        c=clients['pbc']
        c.rewrite=lambda method,p,r:{**r,'hash':'0x'+'ef'*32} if method=='eth_getBlockByNumber' and p[0] not in c.identities else r
    elif label=='input-drift':
        def drift(method,p,r):
            m['mutantNote']='changed during collection';return r
        clients['pbc'].rewrite=drift
    elif label=='death-fact':clients['dbc'].rewrite=lambda method,p,r:'0x'+'00'*352 if method=='eth_call' else r
    elif label=='post-header':
        c=clients['dbc'];seen={}
        def alter(method,p,r):
            if method=='eth_getBlockByHash':
                seen[p[0]]=seen.get(p[0],0)+1
                if seen[p[0]]==2:
                    r['timestamp']=hex(int(r['timestamp'],16)+1);c.headers[p[0]]=copy.deepcopy(r)
            return r
        c.rewrite=alter
    return fn(e,manifest=m,observations=o,expected_owner=e['owner'],
        abi_paths={n:ABI/(n+'.json') for n in m['abi']},rpcs=clients,
        output=folder,compiled_max_admins='8',**over)


replacements={
 'origin':("all(origins[c] == m['chains'][c]['rpcUrl'] for c in clients)", 'True'),
 'call-budget':("len(transcript['calls']) < max_calls", 'True'),
 'identity':('_header(raw) == pin','True'),
 'canonical':('_header(current, timestamp=True) == normalized','True'),
 'input-drift':('manifest==m and observations==o and evidence==e','True'),
 'post-header':('confirmed == headers[(chain_id,hash_)]','True'),
 'death-fact':('verified = verify_native_history(e, manifest=m, observations=o, expected_owner=expected_owner,\n            abi_paths=paths, blocks=blocks, calls=calls, compiled_max_admins=compiled_max_admins)',
               'verified = checked'),
}
results=[]
with tempfile.TemporaryDirectory(prefix='history-rpc-sensitivity-') as tmp:
    for label,(old,new) in replacements.items():
        try:run(collect,label,Path(tmp)/(label+'-real'))
        except ValueError:pass
        else:raise AssertionError('real collector admitted '+label)
        assert SOURCE.count(old)==1,(label,SOURCE.count(old))
        modified=SOURCE.replace(old,new)
        spec=importlib.util.spec_from_loader('_history_rpc_mutant',loader=None)
        mod=importlib.util.module_from_spec(spec)
        exec(compile(modified,str(PATH),'exec'),mod.__dict__)
        run(mod.collect,label,Path(tmp)/(label+'-mutant'))
        results.append(dict(control=label,realRefused=True,mutantAdmitted=True,
                            mutatedSourceSha256=hashlib.sha256(modified.encode()).hexdigest()))
assert PATH.read_text()==SOURCE
print(json.dumps(dict(controls=results,sourceUnchanged=True),indent=2))
