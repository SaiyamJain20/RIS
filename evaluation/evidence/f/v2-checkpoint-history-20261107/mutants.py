"""Narrow in-memory bypasses; every variant must preserve its valid control."""
import copy
import json
from pathlib import Path
import sys
import types

from eth_abi import encode
from jsonschema import ValidationError

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from evaluation.tests.test_checkpoint_history_v2 import history, forked_heads
from evaluation.tests.test_witness_history_v2 import fingerprint
from evaluation.witness_history_v2 import verify_signed_history

source=(ROOT/'evaluation/checkpoint_history_v2.py').read_text()

def variant(old=None,new=None):
    text=source
    if old is not None:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    module=types.ModuleType('checkpoint_history_deliberate_mutant')
    exec(compile(text,str(ROOT/'evaluation/checkpoint_history_v2.py'),'exec'),module.__dict__)
    return module

def refuses(module,args):
    try:module.verify_checkpoint_history(**args)
    except (ValueError,ValidationError):return True
    return False

results=[]
for name in ('coverage','state','history','block-fact','call-fact','safe-height','fault-label','death-exclusions'):
    good=history(3,2) if name=='coverage' else history(1,2)
    bad=copy.deepcopy(good);mutant=variant()
    if name=='coverage':
        bad['captures'].pop(0)
        mutant=variant('_require(set(selected) == expected,', '_require(set(selected) <= expected,')
        text=source.replace('_require(set(selected) == expected,','_require(set(selected) <= expected,')
        text=text.replace("            capture = selected[signed['digest']]", "            if signed['digest'] not in selected: continue\n            capture = selected[signed['digest']]")
        exec(compile(text,'deliberate-coverage-bypass','exec'),mutant.__dict__)
    elif name=='state':
        for capture in bad['captures']:
            capture['calls'][-1]['result']='0x'+encode(['uint64'],[1]).hex()
        mutant.verify_checkpoint_signature=lambda *a,**k:None
    elif name=='history':
        bad['evidence']['conflicts'][0]['digests'][0]['signature']='0x'+'00'*65
        fingerprint(bad['evidence'])
        def known_valid(*a,**k):
            return verify_signed_history(good['evidence'],manifest=good['manifest'],observations=good['observations'],
                expected_owner=good['expected_owner'],compiled_max_admins='8')
        mutant.verify_signed_history=known_valid
    elif name=='block-fact':
        bad['captures'][1]['blocks'][0]['raw']['timestamp']='0x3dc'
        mutant=variant("_require(key not in headers or headers[key] == value, 'conflicting block facts')",'pass # deliberate header-consistency bypass')
    elif name=='call-fact':
        bad['captures'][1]['calls'][-1]['result']='0x'+encode(['uint64'],[59]).hex()
        mutant=variant("_require(key not in calls or calls[key] == call['result'], 'conflicting state call facts')",'pass # deliberate call-consistency bypass')
    elif name=='safe-height':
        bad=forked_heads()
        mutant=variant("_require(height not in heights or heights[height] == raw['hash'], 'conflicting safe block hashes')",'pass # deliberate safe-height bypass')
    elif name=='fault-label':
        bad=forked_heads(True)
        mutant=variant('return checked | dict(checkpointStateSignaturesChecked=len(expected))',
                       'return checked | dict(checkpointStateSignaturesChecked=len(expected), declaredSafeLedgerInterval=True)')
    else:
        from evaluation.tests.test_witness_history_v2 import supersede
        from evaluation.binding_context_v2 import reconstruct
        from evaluation.schema_v2 import _binding_digest
        bad['manifest']['mutations']='32'
        for chain in bad['observations'].values():
            for views in chain['views'].values():
                if 'mutations' in views:views['mutations']['value']='32'
        doc=reconstruct(bad['manifest'],bad['observations'],compiled_max_admins='8')
        bad['evidence']['binding']=dict(document=doc,binding_v2=_binding_digest(doc))
        bad['evidence']['marker']['binding_v2']=bad['evidence']['binding']['binding_v2']
        supersede(bad['manifest'],bad['evidence'],'GrantReceipt',kind='executed-receipt')
        mutant=variant('return checked | dict(checkpointStateSignaturesChecked=len(expected))',
                       'return checked | dict(checkpointStateSignaturesChecked=len(expected), excludedDeathSeqs=[])')
    real=variant()
    valid=mutant.verify_checkpoint_history(**good)
    assert valid==real.verify_checkpoint_history(**good),name+' broke valid control'
    if name=='fault-label':
        assert real.verify_checkpoint_history(**bad)['declaredSafeLedgerInterval'] is False
        assert mutant.verify_checkpoint_history(**bad)['declaredSafeLedgerInterval'] is True
    elif name=='death-exclusions':
        assert real.verify_checkpoint_history(**bad)['excludedDeathSeqs']==['1']
        assert mutant.verify_checkpoint_history(**bad)['excludedDeathSeqs']==[]
    else:
        assert refuses(real,bad),name+' lacks rejecting baseline'
        assert not refuses(mutant,bad),name+' bypass did not reach intended invariant'
    results.append(dict(name=name,validControlPassed=True,deliberateBypassDetected=True))
print(json.dumps(results,indent=2))
