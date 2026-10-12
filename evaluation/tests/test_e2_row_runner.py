"""The P2 slice row runner as one shared function (A1-0082 P4-1).

`e2.execute` and the gate call the same `run_row`. Case directory names and slice pass statuses stay
exactly as in the slices, so the agent 1 review tools still find their rows. No services: the profile
executor and the plan verifier are control-flow doubles where needed.
"""
import importlib
import json

import pytest

SOLO = 'solo-correlated'
P = ('paper-strict', 'paper-minimal', 'repaired-e')
RECEIPT = ['repaired-e-receipt-binding-control-'+f for f in ('requestDigest', 'gid', 'dataId')]
RECEIPT += ['repaired-e-receipt-signature-control-'+f for f in ('requestDigest', 'gid', 'dataId')]
RECEIPT += ['repaired-e-receipt-binding-positive']
CASES = {
    'expired_retry': [p+'-'+point for p in P for point in ('after_intent', 'after_send')],
    'duplicate_outcome': [p+'-duplicate-outcome' for p in P],
    'nonce_replay': [p+'-nonce-replay' for p in P],
    'subject_substitution': [p+'-subject-substitution' for p in P],
    'relay_stress': [p+'-forged-tuple' for p in P]+[p+'-new-reference-replay' for p in P]+['repaired-e-same-nonce-distinct-digests'],
    'audit_stress': [p+'-'+v for v in ('dropped-outcome', 'fabricated-outcome') for p in P],
    'receipt_stress': RECEIPT,
    'trust_stress': [p+'-'+v for v in ('wrong-issuer', 'signed-list-rollback') for p in P],
    'barrier_stress': [p+'-'+v for v in ('pre-barrier-revocation', 'post-barrier-revocation', 'expired-duty') for p in P],
    'destination_stress': [p+'-'+v for v in ('wrong-destination', 'expiry-boundary') for p in P],
}
STATUS = {'expired_retry': 'E2_RECOVERY_EXPIRY_SLICE_PASS', 'duplicate_outcome': 'E2_DUPLICATE_OUTCOME_SLICE_PASS',
          'nonce_replay': 'E2_NONCE_REPLAY_SLICE_PASS', 'subject_substitution': 'E2_SUBJECT_SUBSTITUTION_SLICE_PASS',
          'relay_stress': 'E2_RELAY_STRESS_SLICE_PASS', 'audit_stress': 'E2_AUDIT_STRESS_SLICE_PASS',
          'receipt_stress': 'E2_RECEIPT_STRESS_SLICE_PASS', 'trust_stress': 'E2_TRUST_STRESS_SLICE_PASS',
          'barrier_stress': 'E2_BARRIER_STRESS_SLICE_PASS', 'destination_stress': 'E2_DESTINATION_STRESS_SLICE_PASS'}
MODE = {'expired_retry': 'two-chain-e2-recovery-slice', 'duplicate_outcome': 'two-chain-e2-duplicate-outcome-slice',
        'nonce_replay': 'two-chain-e2-nonce-replay-slice', 'subject_substitution': 'two-chain-e2-subject-substitution-slice',
        'relay_stress': 'two-chain-e2-relay-stress-slice', 'audit_stress': 'two-chain-e2-audit-stress-slice',
        'receipt_stress': 'two-chain-e2-receipt-stress-slice', 'trust_stress': 'two-chain-e2-trust-stress-slice',
        'barrier_stress': 'two-chain-e2-barrier-stress-slice', 'destination_stress': 'two-chain-e2-destination-stress-slice'}


def e2():
    return importlib.import_module('evaluation.e2')


@pytest.fixture(scope='module')
def plans():
    return {flag: e2().create_plan(run_id='E2-row-test', freeze_message='S3-0021', review_mode=SOLO, **{flag: True}) for flag in CASES}


@pytest.mark.parametrize('flag', list(CASES))
def test_case_names_keep_every_slice_layout(plans, flag):
    p = plans[flag]
    assert [e2().case_name(p, item) for item in p['matrix']] == CASES[flag]


@pytest.mark.parametrize('flag', list(CASES))
def test_slice_status_and_mode_are_the_slice_values(plans, flag):
    assert e2().slice_status(plans[flag]) == STATUS[flag]
    mode, limitation = e2().slice_mode(plans[flag])
    assert mode == MODE[flag] and 'no complete catalog or RQ gate' in limitation


def test_execute_delegates_every_matrix_item_to_run_row_once(tmp_path, monkeypatch, plans):
    m = e2(); p = plans['destination_stress']; path = tmp_path/'plan.json'; path.write_text(json.dumps(p))
    monkeypatch.setattr(m, 'verify_plan', lambda plan: None)
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    seen = []

    def row(plan, item, output, record, case_records):
        case = m.case_name(plan, item); seen.append(case)
        record['cases'][case] = dict(status='DESTINATION_STRESS_CONTROL_PASS')
        return case
    monkeypatch.setattr(m, 'run_row', row)
    result = m.execute(path, None, tmp_path/'out')
    assert seen == CASES['destination_stress'] and result['status'] == 'E2_DESTINATION_STRESS_SLICE_PASS'
    assert result['executionMode'] == MODE['destination_stress'] and result['sourceStable'] is True


def test_execute_stops_the_slice_at_the_first_failed_row(tmp_path, monkeypatch, plans):
    m = e2(); p = plans['trust_stress']; path = tmp_path/'plan.json'; path.write_text(json.dumps(p))
    monkeypatch.setattr(m, 'verify_plan', lambda plan: None)
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    seen = []

    def row(plan, item, output, record, case_records):
        seen.append(m.case_name(plan, item)); raise ValueError('TEST-ONLY row failure')
    monkeypatch.setattr(m, 'run_row', row)
    result = m.execute(path, None, tmp_path/'out')
    assert seen == CASES['trust_stress'][:1] and result['status'] == 'FAILED'
    assert result['failure'] == dict(type='ValueError', message='TEST-ONLY row failure')


def test_run_row_refuses_a_row_without_its_proof(tmp_path, monkeypatch, plans):
    m = e2(); p = plans['trust_stress']
    monkeypatch.setattr(m, 'verify_plan', lambda plan: None)
    monkeypatch.setattr(m.e1, '_profile', lambda *args, **kwargs: None)  # writes no proof file
    record = dict(cases={}); out = tmp_path/'slice'; out.mkdir()
    with pytest.raises(OSError):
        m.run_row(p, p['matrix'][0], out, record, {})
    assert record['cases']['paper-strict-wrong-issuer']['status'] == 'RUNNING'
    assert (out/'paper-strict-wrong-issuer').is_dir() and (out/'manifest.json').is_file()
