"""Narrow in-memory deliberate bypasses; original product files stay fixed."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from _pytest.outcomes import Failed
import evaluation.receipt_history_v2 as product
from evaluation.tests import test_receipt_history_v2 as tests

path=ROOT/'evaluation/receipt_history_v2.py'
before=hashlib.sha256(path.read_bytes()).hexdigest()
original_require=product._require
original_state=product.verify_receipt_signature
original_history=product.verify_signed_history

def valid():
    result=tests.check(tests.history())
    assert result['receiptStateSignaturesChecked']==2
    assert result['signaturesChecked']==5
    assert result['declaredSafeLedgerInterval']

cases=[
    ('skip-state',lambda:tests.test_each_receipt_uses_its_own_raw_state_and_event(0,'grant')),
    ('skip-history',lambda:tests.test_recorded_target_observation_and_complete_history_context('other-signature')),
    ('conflicting block facts',tests.test_shared_header_facts_refuse_even_when_each_receipt_passes),
    ('conflicting state call facts',tests.test_repeated_state_call_conflicts_refuse_even_in_fault_interval),
    ('conflicting grant event facts',tests.test_repeated_event_bytes_conflict_even_in_fault_interval),
    ('conflicting safe grant event',tests.test_safe_interval_refuses_two_canonical_event_locations_for_one_grant),
    ('conflicting safe block hashes',tests.test_same_height_cross_capture_fork_refuses_safe_but_fault_label_stays_explicit),
]
results=[]
for name,test in cases:
    test()  # The unmodified checker must refuse the independent negative case.
    try:
        if name=='skip-state':product.verify_receipt_signature=lambda *a,**k: {}
        elif name=='skip-history':
            product.verify_signed_history=lambda *a,**k: dict(signaturesChecked=5,recordsChecked=5,
                declaredSafeLedgerInterval=True,excludedDeathSeqs=[])
        else:
            product._require=lambda condition,message: original_require(condition or message==name,message)
        valid()  # A deny-all mutant cannot count as detected.
        try:test()
        except Failed as error:
            assert 'DID NOT RAISE' in str(error),str(error)
        else:raise AssertionError('undetected mutant: '+name)
        results.append(dict(bypass=name,negativeDetected=True,validControl=True))
    finally:
        product._require=original_require
        product.verify_receipt_signature=original_state
        product.verify_signed_history=original_history
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
print(json.dumps(dict(classification='deliberate evaluator mutation',sourceSha256=before,
                      pairs=results,filesChanged=False),indent=2))
