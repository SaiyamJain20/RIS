"""Narrow in-memory deliberate bypasses; author-correlated sensitivity only."""
from pathlib import Path
import sys
import types

from eth_abi import encode
from evaluation.tests import test_governance_state_v2 as controls
import evaluation.governance_state_v2 as original

SOURCE=Path(original.__file__).read_text()

def state(getter,value,kind='uint64',action='1'):
    args=controls.setup(action)
    controls.raw_call(args,getter)['result']='0x'+encode([kind],[value]).hex()
    return args


def unapproved():
    args=controls.setup();args['approvals']=[];return args


cases=[
    ('next nonce', "int(message['nonce']) == int(nonce) + 1", lambda:state('governanceNonce',6)),
    ('state witness version', "message['witnessSetVersion'] == version",lambda:state('witnessSetVersion',9)),
    ('ADD existing authority', 'authority is False',lambda:state('isAuthority',True,'bool')),
    ('ADD tombstone', 'removed is False',lambda:state('removedAuthority',True,'bool')),
    ('REMOVE/SET authority', 'authority is True',lambda:state('isAuthority',False,'bool','2')),
    ('approval tuple', '{k:message[k] for k in fields} in approvals',unapproved),
    ('expiry bound', 'ts < expiry <= ts + int(ttl)',lambda:state('maxGovernanceTtl',59)),
]
results=[]
for label,old,make in cases:
    assert SOURCE.count(old)==1,label
    mutant=types.ModuleType('evaluation.governance_state_v2')
    exec(compile(SOURCE.replace(old,'True'),'<in-memory-governance-bypass>','exec'),mutant.__dict__)
    args=make()
    try:controls.check(args)
    except ValueError:pass
    else:raise AssertionError('original failed to refuse '+label)
    try:
        sys.modules['evaluation.governance_state_v2']=mutant
        assert controls.check(controls.setup())['sourceStateChecked'],label
        assert controls.check(args)['sourceStateChecked'],label
    finally:sys.modules['evaluation.governance_state_v2']=original
    results.append(label)
print({'validControlsPassed':len(results),'deliberateBypassesDetected':len(results),'checks':results})
