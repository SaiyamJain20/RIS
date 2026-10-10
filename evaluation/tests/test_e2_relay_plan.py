"""SL2 relay-stress plan: seven exact rows, solo-only, fail-closed per row.

No services: the profile executor is a control-flow double writing supplied
proof files. Never peer or gate evidence.
"""
import importlib
import json

import pytest

SOLO = 'solo-correlated'
ROWS = [('paper-strict', 'forged-tuple'), ('paper-minimal', 'forged-tuple'), ('repaired-e', 'forged-tuple'),
        ('paper-strict', 'new-reference-replay'), ('paper-minimal', 'new-reference-replay'), ('repaired-e', 'new-reference-replay'),
        ('repaired-e', 'same-nonce-distinct-digests')]
CASES = ['E01-forged-tuple-paper-strict', 'E01-forged-tuple-paper-minimal', 'E01-forged-tuple-repaired-e',
         'E01-new-reference-replay-paper-strict', 'E01-new-reference-replay-paper-minimal', 'E01-new-reference-replay-repaired-e',
         'E01-same-nonce-distinct-digests-repaired-e']


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-relay-test', freeze_message='S3-0007', relay_stress=True, review_mode=SOLO)


def test_relay_plan_pins_seven_frozen_rows_and_solo_configuration():
    p = plan(); module().verify_plan(p)
    assert [(r['profile'], r['variant']) for r in p['matrix']] == ROWS and p['caseIds'] == CASES
    assert p['relayStress'] is True and p['fullCatalogComplete'] is False and 'workerExpected' not in p
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    assert 'fresh-second-deployment-relay-stress' in p['controls']
    probe = p['relayProbe']
    assert 'BAD_SIGNATURE(1)' in probe['forgedTuple'] and 'eth_call' in probe['forgedTuple']
    assert 'KSSC.sol:180' in probe['newReferenceReplay'] and 'KSSC.sol:182' in probe['sameNonce']


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'), dict(subject_substitution=True),
                                     dict(nonce_replay=True), dict(duplicate_outcome=True), dict(expired_retry=True)])
def test_relay_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-relay-test', freeze_message='S3-0007', relay_stress=True, review_mode=SOLO); kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['row', 'probe', 'classification', 'freshness'])
def test_changed_relay_plan_refuses(change):
    p = plan()
    if change == 'row': p['matrix'][6]['profile'] = 'paper-strict'
    if change == 'probe': p['relayProbe']['sameNonce'] = 'consume the second after re-collection'
    if change == 'classification': p['classification'] = 'HMBC vulnerability'
    if change == 'freshness': p['freshness'] = 'reuse D1'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def test_relay_plan_without_solo_records_is_blocked(tmp_path):
    path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    result = module().execute(path, None, tmp_path/'out')
    assert result['status'] == 'BLOCKED' and result['servicesStarted'] == [] and result['cases'] == {}


EXPECTED = {('paper-strict', 'forged-tuple'): ('SPEC_GAP', None), ('paper-minimal', 'forged-tuple'): ('SPEC_GAP', None),
            ('repaired-e', 'forged-tuple'): ('REPAIR_SUPPORTED', 'BAD_SIGNATURE'),
            ('paper-strict', 'new-reference-replay'): ('SPEC_GAP', None), ('paper-minimal', 'new-reference-replay'): ('SPEC_GAP', None),
            ('repaired-e', 'new-reference-replay'): ('REPAIR_SUPPORTED', 'REPLAY'),
            ('repaired-e', 'same-nonce-distinct-digests'): ('REPAIR_SUPPORTED', 'REPLAY')}


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, relay_stress):
        assert recovery_point is None and expired_retry is False
        if mode == 'missing': return
        classification, error = EXPECTED[(profile, relay_stress)]
        proof = dict(ok=True, delivery='unknown', classification=classification, error=error, variant=relay_stress)
        if mode == 'wrong-error' and error: proof['error'] = 'EXPIRED'
        if mode == 'paper-repaired' and not error: proof['classification'] = 'REPAIR_SUPPORTED'
        if mode == 'other-variant': proof['variant'] = 'subject'
        if mode == 'not-ok': proof['ok'] = False
        (output/'relay-stress').mkdir(parents=True); (output/'relay-stress/result.json').write_text(json.dumps(proof))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-error', 'paper-repaired', 'other-variant', 'not-ok', 'complete'])
def test_relay_execution_requires_each_complete_row_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_RELAY_STRESS_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert len(result['cases']) == 7 and {c['status'] for c in result['cases'].values()} == {'RELAY_STRESS_CONTROL_PASS'}
