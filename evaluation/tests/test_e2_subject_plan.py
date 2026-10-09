"""SL1 subject plan: solo-only, exact, and fail-closed on incomplete proofs.

No services: the profile executor is replaced by a control-flow double that
writes supplied proof files. These doubles are never peer or gate evidence.
"""
import importlib
import json

import pytest

SOLO = 'solo-correlated'


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-subject-test', freeze_message='S3-0005', subject_substitution=True, review_mode=SOLO)


def test_subject_plan_pins_three_fresh_rows_controls_and_solo_disclosure():
    p = plan(); module().verify_plan(p)
    assert p['subjectSubstitution'] is True and p['fullCatalogComplete'] is False
    assert p['caseIds'] == ['E01-subject-substitution-'+x for x in ('paper-strict', 'paper-minimal', 'repaired-e')]
    assert [r['point'] for r in p['matrix']] == [None]*3 and 'workerExpected' not in p
    assert 'fresh-second-deployment-subject-stress' in p['controls']
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    assert 'WRONG_SUBJECT(2)' in p['classification'] and 'never an HMBC exploit' in p['classification']


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'),
                                     dict(nonce_replay=True), dict(duplicate_outcome=True), dict(expired_retry=True)])
def test_subject_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-subject-test', freeze_message='S3-0005', subject_substitution=True, review_mode=SOLO)
    kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['probe', 'classification', 'controls', 'freshness'])
def test_changed_subject_plan_refuses_before_services(change):
    p = plan()
    if change == 'probe': p['subjectProbe']['completion'] = 'release to original subject'
    if change == 'classification': p['classification'] = 'paper vulnerability'
    if change == 'controls': p['controls'].remove('fresh-second-deployment-subject-stress')
    if change == 'freshness': p['freshness'] = 'reuse the control deployment'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def test_subject_plan_without_solo_records_is_blocked_before_services(tmp_path):
    path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    result = module().execute(path, None, tmp_path/'out')
    assert result['status'] == 'BLOCKED' and result['servicesStarted'] == [] and result['cases'] == {}
    assert result['reviewMode'] == SOLO


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, subject_substitution):
        assert recovery_point is None and expired_retry is False and subject_substitution is True
        if mode == 'missing': return
        repaired = profile == 'repaired-e'
        stress = output/'subject-stress'; (stress/'subject-substitution').mkdir(parents=True)
        pre = dict(ok=True, delivery='unknown', workerUnchanged=True,
                   classification='REPAIR_SUPPORTED' if repaired else 'SPEC_GAP', error='WRONG_SUBJECT' if repaired else None)
        if mode == 'wrong-code' and repaired: pre['error'] = 'WRONG_DESTINATION'
        if mode == 'paper-reject' and not repaired: pre['classification'] = 'REPAIR_SUPPORTED'
        (stress/'subject-substitution/result.json').write_text(json.dumps(pre))
        if repaired:
            if mode == 'repaired-release':
                (stress/'subject-completion').mkdir(); (stress/'subject-completion/result.json').write_text('{}')
            return
        if mode == 'no-completion': return
        done = dict(ok=True, classification='SPEC_GAP', delivery='unknown', bobDecryptable=True,
                    aliceError='WRONG_SUBJECT', outcomeTested=False)
        if mode == 'alice-decrypts': done['aliceError'] = None
        if mode == 'outcome': done['outcomeTested'] = True
        (stress/'subject-completion').mkdir(); (stress/'subject-completion/result.json').write_text(json.dumps(done))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-code', 'paper-reject', 'repaired-release', 'no-completion',
                                  'alice-decrypts', 'outcome', 'complete'])
def test_subject_execution_requires_each_complete_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_SUBJECT_SUBSTITUTION_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert {c['status'] for c in result['cases'].values()} == {'SUBJECT_SUBSTITUTION_CONTROL_PASS'} and len(result['cases']) == 3
