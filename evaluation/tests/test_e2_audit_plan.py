"""SL3 audit-stress plan: six exact rows, solo-only, fail-closed per row.

No services: the profile executor is a control-flow double writing supplied proof files.
"""
import importlib
import json

import pytest

SOLO = 'solo-correlated'
ROWS = [(p, v) for v in ('dropped-outcome', 'fabricated-outcome') for p in ('paper-strict', 'paper-minimal', 'repaired-e')]
EXPECTED = {('paper-strict', 'dropped-outcome'): ('SUPPORTED', None), ('paper-minimal', 'dropped-outcome'): ('SUPPORTED', None),
            ('repaired-e', 'dropped-outcome'): ('REPAIR_SUPPORTED', None),
            ('paper-strict', 'fabricated-outcome'): ('SPEC_GAP', None), ('paper-minimal', 'fabricated-outcome'): ('SPEC_GAP', None),
            ('repaired-e', 'fabricated-outcome'): ('REPAIR_SUPPORTED', 'WRONG_PROFILE')}


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-audit-test', freeze_message='S3-0011', audit_stress=True, review_mode=SOLO)


def test_audit_plan_pins_six_frozen_rows_and_solo_configuration():
    p = plan(); module().verify_plan(p)
    assert [(r['profile'], r['variant']) for r in p['matrix']] == ROWS
    assert p['caseIds'] == ['E03-'+v+'-'+pr for pr, v in ROWS]
    assert p['auditStress'] is True and p['fullCatalogComplete'] is False and 'workerExpected' not in p
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    probe = p['auditProbe']
    assert 'RELEASE' in probe['droppedOutcome'] and 'PENDING' in probe['droppedOutcome']
    assert 'WRONG_PROFILE(21)' in probe['fabricatedOutcome'] and 'NOT_COMMITTED' in probe['fabricatedOutcome']


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'), dict(relay_stress=True),
                                     dict(subject_substitution=True), dict(nonce_replay=True)])
def test_audit_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-audit-test', freeze_message='S3-0011', audit_stress=True, review_mode=SOLO); kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['row', 'probe', 'classification'])
def test_changed_audit_plan_refuses(change):
    p = plan()
    if change == 'row': p['matrix'][0]['variant'] = 'duplicate-outcome'
    if change == 'probe': p['auditProbe']['droppedOutcome'] = 'report the outcome'
    if change == 'classification': p['classification'] = 'HMBC vulnerability'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, audit_stress):
        assert recovery_point is None and expired_retry is False
        if mode == 'missing': return
        classification, error = EXPECTED[(profile, audit_stress)]
        proof = dict(ok=True, delivery='unknown', classification=classification, error=error, variant=audit_stress)
        if mode == 'wrong-class': proof['classification'] = 'SPEC_GAP' if classification != 'SPEC_GAP' else 'SUPPORTED'
        if mode == 'other-variant': proof['variant'] = 'forged-tuple'
        (output/'audit-stress').mkdir(parents=True); (output/'audit-stress/result.json').write_text(json.dumps(proof))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-class', 'other-variant', 'complete'])
def test_audit_execution_requires_each_complete_row_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_AUDIT_STRESS_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert len(result['cases']) == 6 and {c['status'] for c in result['cases'].values()} == {'AUDIT_STRESS_CONTROL_PASS'}
