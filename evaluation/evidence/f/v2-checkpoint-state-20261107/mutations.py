"""Narrow in-memory bypasses; no source edits or services."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from evaluation import checkpoint_state_v2 as subject
from evaluation.tests import test_checkpoint_state_v2 as tests

real=subject._require
trials=[
    ('source-state','source state authEpoch',lambda:tests.test_valid_signature_does_not_make_wrong_or_stale_state_true('authEpoch','source',12)),
    ('freshness','semantic freshness authEpoch',lambda:tests.test_valid_signature_does_not_make_wrong_or_stale_state_true('authEpoch','head',12)),
    ('sequence','next sequence',lambda:tests.test_valid_signature_cannot_skip_or_repeat_current_sequence('9')),
    ('expiry','expiry window',lambda:tests.test_exact_target_window_boundaries('1061',False)),
    ('regression','source block regression',lambda:tests.test_signed_but_invalid_checkpoint_rejected('regressed-source')),
    ('unused-call','unused state call',lambda:tests.test_call_selection_and_complete_canonical_bytes('unused')),
    ('same-height','source/head hash mismatch',lambda:tests.test_signed_but_invalid_checkpoint_rejected('same-height-fork')),
]
rows=[]
for name,label,test in trials:
    subject._require=lambda condition,message,label=label: None if message==label else real(condition,message)
    try:
        tests.test_valid_checkpoint_signature_joins_exact_state_without_mutation('3',True,False)
        try:
            test()
        except BaseException as error:
            # Detection must be the intended missing refusal, not another error.
            assert type(error).__name__=='Failed' and 'DID NOT RAISE' in str(error),repr(error)
            rows.append(dict(name=name,positiveControl=True,detected=True,diagnostic=str(error)))
        else:
            raise AssertionError('Undetected bypass: '+name)
    finally:
        subject._require=real
print(json.dumps(dict(classification='deliberate in-memory mutations',trials=rows),indent=2))
