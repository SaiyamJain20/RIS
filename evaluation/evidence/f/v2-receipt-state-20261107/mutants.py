"""Narrow in-memory sensitivity controls; no runtime/owner code edits."""
from pathlib import Path
import sys
import types

from eth_abi import encode, decode

from evaluation.tests import test_receipt_state_v2 as controls
import evaluation.receipt_state_v2 as original

SOURCE=Path(original.__file__).read_text()


def grant_disallowed():
    args=controls.setup();controls.change_tuple(args,0,1,False);return args


def recorded():
    args=controls.setup();controls.change_tuple(args,1,0,2);return args


def too_long():
    args=controls.setup();controls.change_tuple(args,1,7,1029);return args


def false_recipient():
    args=controls.setup();row=args['logs'][0]
    kinds=['bytes32','uint64','uint64','bytes32','bool','uint256']
    values=list(decode(kinds,bytes.fromhex(row['data'][2:])))
    values[3]=bytes.fromhex('99'*32)
    row['data']='0x'+encode(kinds,values).hex();return args


def future_event():
    args=controls.setup();args['dbc_observation']['blockNumber']='11'
    args['blocks'][1]['raw']['number']='0xb';return args


signature_call="""verify_bound_signature('GrantReceipt',message,signature,owner=owner,
        manifest=manifest,observations=observations,compiled_max_admins=compiled_max_admins)"""
cases=[
    ('allowed grant',"grant['exists'] is True and grant['allowed'] is True",grant_disallowed,None),
    ('pending request',"request['status']=='1'",recorded,None),
    ('original request expiry',"0<int(message['grantExpiresAt'])<=int(request['expiresAt'])",too_long,None),
    ('event grant equality',"fields[field]==grant[field]",false_recipient,None),
    ('observation covers event',"int(message['dbcBlockNumber'])<=int(dbc_observation['blockNumber'])",future_event,None),
    ('bound signature',signature_call,controls.setup,'0x00'),
]
results=[]
for label,old,make,signature in cases:
    assert SOURCE.count(old)==1,label
    mutant=types.ModuleType('evaluation.receipt_state_v2')
    replacement='{}' if label=='bound signature' else 'True'
    exec(compile(SOURCE.replace(old,replacement),'<in-memory-receipt-bypass>','exec'),mutant.__dict__)
    args=make()
    try:controls.check(args,signature)
    except controls.BAD:pass
    else:raise AssertionError('original did not refuse '+label)
    try:
        sys.modules['evaluation.receipt_state_v2']=mutant
        assert controls.check(controls.setup())['sourceStateChecked'],label
        assert controls.check(args,signature)['sourceStateChecked'],label
    finally:sys.modules['evaluation.receipt_state_v2']=original
    results.append(label)
print(dict(validControlsPassed=len(results),deliberateBypassesDetected=len(results),checks=results))
