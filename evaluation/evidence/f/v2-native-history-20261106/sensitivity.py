"""Deliberate narrow in-memory bypasses: real refusal, mutant acceptance."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.tests.test_witness_native_v2 import setup, ABI
from evaluation.witness_native_v2 import verify_native_history

PATH = ROOT / 'evaluation/witness_native_v2.py'
SOURCE = PATH.read_text()


def run(fn, args):
    m,o,e,b,c=copy.deepcopy(args)
    return fn(e,manifest=m,observations=o,expected_owner=e['owner'],blocks=b,calls=c,
              abi_paths={n:ABI/(n+'.json') for n in m['abi']},compiled_max_admins='8')


cases=[]
for field in ('number','timestamp'):
    args=setup(); target=args[3][0]['raw'];target[field]=hex(int(target[field],16)+1)
    guard='actual_number == number' if field=='number' else 'timestamp is None or actual_time == timestamp'
    cases.append((field,guard,args))
for name,kind,guard in (
    ('StateCheckpoint','overtaken-checkpoint',"exists is True and checkpoint['sequence'] == death['observed']"),
    ('GovernanceAction','overtaken-governance',"nonce == death['observed']"),
    ('AccessDecision','overtaken-decision-grant',"grant['exists'] is True and grant['requestDigest'] == row['keyField']"),
    ('GrantReceipt','executed-receipt',"request['status'] == '2'")):
    args=setup(name,kind);raw=bytearray.fromhex(args[4][0]['result'][2:]);raw[:32]=bytes(32)
    args[4][0]['result']='0x'+raw.hex();cases.append((kind,guard,args))
args=setup();args[4].append(dict(chainId=args[0]['chains']['pbc']['chainId'],blockHash=args[3][0]['raw']['hash'],
                               to=args[0]['chains']['pbc']['contracts']['PSC'],data='0x12345678',result='0x'))
cases.append(('unused-call','used_calls == set(raw_calls)',args))

results=[]
for label,guard,args in cases:
    try: run(verify_native_history,args)
    except ValueError: pass
    else: raise AssertionError('Real checker admitted control: '+label)
    assert SOURCE.count(guard)==1
    changed=SOURCE.replace(guard,'True')
    spec=importlib.util.spec_from_loader('_native_mutant',loader=None)
    module=importlib.util.module_from_spec(spec)
    exec(compile(changed,str(PATH),'exec'),module.__dict__)
    run(module.verify_native_history,args)
    results.append(dict(control=label,realRefused=True,mutantAdmitted=True,
                        mutatedSourceSha256=hashlib.sha256(changed.encode()).hexdigest()))
assert PATH.read_text()==SOURCE
print(json.dumps(dict(controls=results,sourceUnchanged=True),indent=2))
