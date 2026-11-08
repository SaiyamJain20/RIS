"""Narrow in-memory bypasses, baseline refusals and valid controls; no source edits."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import types

from eth_abi import encode
from jsonschema import ValidationError

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from evaluation.tests.test_governance_rpc_v2 import case

source=(ROOT/'evaluation/governance_rpc_v2.py').read_text()

def variant(old=None,new=None):
    text=source
    if old is not None:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    module=types.ModuleType('governance_rpc_deliberate_mutant')
    exec(compile(text,str(ROOT/'evaluation/governance_rpc_v2.py'),'exec'),module.__dict__)
    return module

def run(module,args):
    with tempfile.TemporaryDirectory() as d:
        return module.collect(**args,output=Path(d)/'capture')

def refuses(module,args):
    try:run(module,args)
    except (ValueError,ValidationError):return True
    return False

def poisoned(name):
    args=case()
    client=args['rpcs']['pbc']
    if name=='state':
        client.rewrite=lambda m,p,r:'0x'+encode(['uint64'],[999]).hex() if m=='eth_call' else r
    elif name=='identity':
        client.rewrite=lambda m,p,r:'0x999' if m=='eth_chainId' else r
    elif name=='after-identity':
        def alter(m,p,r):
            client.identities['0x0']['hash']='0x'+'ef'*32
            return r
        args['rpcs']['dbc'].rewrite=alter
    elif name=='header-recheck':
        hits=0
        def alter(m,p,r):
            nonlocal hits
            if m=='eth_getBlockByHash':
                hits+=1
                if hits==2:
                    r['timestamp']=hex(int(r['timestamp'],16)+1)
                    client.headers[p[0]]=copy.deepcopy(r)
            return r
        client.rewrite=alter
    elif name=='approval-drift':
        def alter(m,p,r):
            args['approvals'].clear()
            return r
        client.rewrite=alter
    elif name=='canonical':
        client.rewrite=lambda m,p,r:r|{'hash':'0x'+'ef'*32} if m=='eth_getBlockByNumber' and p[0] not in client.identities else r
    return args

changes={
    'identity':("        _require(_quantity(rpc(chain, 'eth_chainId', [])) == m['chains'][chain]['chainId'],\n                 chain+' chain ID mismatch')",
                "        rpc(chain, 'eth_chainId', []) # deliberate chain-ID equality bypass"),
    'after-identity':("            identity(chain)\n            checkpoint(chain, 'governance-read-after')",
                      "            checkpoint(chain, 'governance-read-after') # deliberate after-identity bypass"),
    'header-recheck':("        for at,fact in required_blocks.items():\n            header(at, *fact)",
                      '        pass # deliberate final header-read bypass'),
    'approval-drift':("        _require((manifest,observations,evidence,approvals) == (m,o,e,a), 'caller input changed')",
                      '        pass # deliberate caller input bracket bypass'),
    'canonical':("            _require(_header(current,timestamp=True) == normalized, 'canonical block mismatch')",
                  '            pass # deliberate canonical equality bypass'),
}

results=[]
for name in ('state','identity','after-identity','header-recheck','approval-drift','canonical'):
    real=variant()
    mutant=variant(*changes[name]) if name in changes else variant()
    if name=='state':
        valid=run(real,case())['verification']
        mutant.verify_governance_history=lambda *a,**k:valid
    assert run(real,case())==run(mutant,case()),name+' broke valid control'
    assert refuses(real,poisoned(name)),name+' lacks baseline refusal'
    assert not refuses(mutant,poisoned(name)),name+' did not bypass intended invariant'
    results.append(dict(name=name,validControlPassed=True,deliberateBypassDetected=True))
print(json.dumps(results,indent=2))
