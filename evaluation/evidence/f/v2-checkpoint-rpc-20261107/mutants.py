"""Narrow in-memory acquisition bypasses; preserve each valid control."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import types

from eth_abi import encode

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from evaluation.tests.test_checkpoint_rpc_v2 import case

SOURCE=(ROOT/'evaluation/checkpoint_rpc_v2.py').read_text()

def variant(old=None,new=None):
    source=SOURCE
    if old is not None:
        assert source.count(old)==1,old
        source=source.replace(old,new)
    module=types.ModuleType('checkpoint_rpc_deliberate_mutant')
    exec(compile(source,str(ROOT/'evaluation/checkpoint_rpc_v2.py'),'exec'),module.__dict__)
    return module

def invoke(module,args,output):
    return module.collect(**args,output=output)

def altered(name):
    args=case()
    if name=='duplicate-selection':args['selections'].append(copy.deepcopy(args['selections'][0]))
    elif name=='state':
        args['rpcs']['pbc'].rewrite=lambda m,p,r:'0x'+encode(['uint64'],[999]).hex() if m=='eth_call' else r
    elif name=='after-identity':
        hits=0
        def change(m,p,r):
            nonlocal hits
            if m=='eth_chainId':
                hits+=1
                if hits==2:return '0x999'
            return r
        args['rpcs']['pbc'].rewrite=change
    elif name=='canonical':
        rpc=args['rpcs']['pbc']
        rpc.rewrite=lambda m,p,r:r|{'hash':'0x'+'ef'*32} if m=='eth_getBlockByNumber' and p[0] not in rpc.identities else r
    elif name=='header-recheck':
        rpc=args['rpcs']['pbc'];hits={}
        def change(m,p,r):
            if m=='eth_getBlockByHash':
                hits[p[0]]=hits.get(p[0],0)+1
                if hits[p[0]]==2 and p[0]=='0x'+'ab'*32:
                    r['timestamp']=hex(int(r['timestamp'],16)+1);rpc.headers[p[0]]=copy.deepcopy(r)
            return r
        rpc.rewrite=change
    elif name=='selection-drift':
        args['rpcs']['pbc'].rewrite=lambda m,p,r:(args['selections'][0].update(reason='replaced') or r)
    return args

changes={
 'duplicate-selection':("and row['digest'] not in selected",''),
 'after-identity':("identity(chain); checkpoint(chain,'checkpoint-read-after')", "checkpoint(chain,'checkpoint-read-after')"),
 'canonical':("_require(_header(current,timestamp=True) == normalized, 'canonical block mismatch')",'pass # deliberate canonicality bypass'),
 'header-recheck':("_require(confirmed == headers[(chain_id,hash_)], 'block changed after capture')",'pass # deliberate consistency bypass'),
 'selection-drift':("_require((manifest,observations,evidence,selections) == (m,o,e,s), 'caller input changed')",'pass # deliberate drift bypass'),
}
results=[]
with tempfile.TemporaryDirectory(prefix='checkpoint-rpc-mutants-') as tmp:
    root=Path(tmp)
    for name in ('duplicate-selection','state','after-identity','canonical','header-recheck','selection-drift'):
        real=variant();mutant=variant(*changes[name]) if name in changes else variant()
        if name=='state':
            # Keep declared history/context checks; bypass only the final state join.
            from evaluation.witness_history_v2 import verify_signed_history
            def bypass(evidence,**kwargs):
                checked=verify_signed_history(evidence,**{k:kwargs[k] for k in
                    ('manifest','observations','expected_owner','compiled_max_admins')})
                return checked|dict(checkpointStateSignaturesChecked=len(kwargs['captures']))
            mutant.verify_checkpoint_history=bypass
        good_real=invoke(real,case(),root/(name+'-valid-real'))
        good_mutant=invoke(mutant,case(),root/(name+'-valid-mutant'))
        assert good_real==good_mutant,name+' broke valid control'
        try:invoke(real,altered(name),root/(name+'-refusal'))
        except ValueError:pass
        else:raise AssertionError(name+' lacks rejecting baseline')
        invoke(mutant,altered(name),root/(name+'-bypass'))
        results.append(dict(name=name,validControlPassed=True,deliberateBypassDetected=True))
print(json.dumps(results,indent=2))
