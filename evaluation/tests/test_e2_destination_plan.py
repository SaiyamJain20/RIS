"""SL7 plan: six exact E01 rows (wrong destination, expiry boundary), solo-only, fail-closed per row.

Wrong destination adds a second deployment B on the same chain pair through the pinned owner commands
(deploy_local.sh, bootstrap_fixture.sh), with the funding reset recorded. No services: the profile
executor is a control-flow double.
"""
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOLO = 'solo-correlated'
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
ROWS = [(p, v) for v in ('wrong-destination', 'expiry-boundary') for p in PROFILES]
EXPECTED = {**{(p, v): ('SPEC_GAP', None) for p in PROFILES[:2] for v in ('wrong-destination', 'expiry-boundary')},
            ('repaired-e', 'wrong-destination'): ('REPAIR_SUPPORTED', 'WRONG_DESTINATION'),
            ('repaired-e', 'expiry-boundary'): ('REPAIR_SUPPORTED', 'EXPIRED')}


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-destination-test', freeze_message='S3-0019', destination_stress=True, review_mode=SOLO)


def test_destination_plan_pins_six_frozen_rows_and_solo_configuration():
    p = plan(); module().verify_plan(p)
    assert [(r['profile'], r['variant']) for r in p['matrix']] == ROWS
    assert p['caseIds'] == ['E01-'+v+'-'+pr for pr, v in ROWS]
    assert p['destinationStress'] is True and p['fullCatalogComplete'] is False and 'workerExpected' not in p
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    catalog = {c['id']: c for c in json.loads((ROOT/'evaluation/scenarios/e0_cases.json').read_text())['cases']}
    for (profile, variant), cid in zip(ROWS, p['caseIds']):
        c = catalog[cid]
        assert c['variant'] == variant and c['profile'] == profile
        assert (c['expected']['classification'], c['expected']['error']) == EXPECTED[(profile, variant)]


def test_destination_probe_states_the_ledger_conditions():
    probe = plan()['destinationProbe']
    for needle in ('step 1', 'line 60', 'step 2', 'lines 61-64', 'cannot kill MUT_NO_DESTINATION_BINDING', 'without rewriting',
                   'Rejected(3)', 'source deployment B untouched'):
        assert needle in probe['wrongDestinationRepaired'], needle
    for needle in ('pbcRequestId', 'no such request', 'chosen completion', 'compromised-relay', 'recipient 0', '+30'):
        assert needle in probe['wrongDestinationPaper'], needle
    for needle in ('same chain pair', 'same chain ids', 'other contract addresses', '1000 ETH', 'balance', 'deploy_local.sh',
                   'bootstrap_fixture.sh', 'pinned owner'):
        assert needle in probe['sourceDeployment'], needle
    for needle in ('evm_setNextBlockTimestamp', 'no evm_mine', 'next mined block', 'exactly', 'line 74', 'd.expiresAt == r.expiresAt',
                   'cp.expiresAt > r.expiresAt', 'DBC only', 'verified'):
        assert needle in probe['expiryBoundaryRepaired'], needle
    for needle in ('ACSC.sol:154', 'grantTtl', 'omits the signed request expiry'):
        assert needle in probe['expiryBoundaryPaper'], needle
    assert 'skipped' in probe['supplementaryEthCall']
    for needle in ('prepare_request', 'collect_checkpoint', 'collect_decision', 'every catalog step', 'D49', 'both deployments'):
        assert needle in probe['workerPrecondition'], needle
    for needle in ('exactly one collect_decision', 'A31'):
        assert needle in probe['certificateDiscipline'], needle


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'), dict(barrier_stress=True),
                                     dict(trust_stress=True), dict(receipt_stress=True)])
def test_destination_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-destination-test', freeze_message='S3-0019', destination_stress=True, review_mode=SOLO); kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['row', 'probe', 'classification'])
def test_changed_destination_plan_refuses(change):
    p = plan()
    if change == 'row': p['matrix'][0]['variant'] = 'expired-duty'
    if change == 'probe': p['destinationProbe']['expiryBoundaryRepaired'] = 'consume one second later'
    if change == 'classification': p['classification'] = 'HMBC vulnerability'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, destination_stress):
        assert recovery_point is None and expired_retry is False
        if mode == 'missing': return
        classification, error = EXPECTED[(profile, destination_stress)]
        proof = dict(ok=True, delivery='unknown', classification=classification, error=error, variant=destination_stress)
        if mode == 'wrong-class': proof['classification'] = 'SPEC_GAP' if classification != 'SPEC_GAP' else 'SUPPORTED'
        if mode == 'other-variant': proof['variant'] = 'expired-duty'
        (output/'destination-stress').mkdir(parents=True); (output/'destination-stress/result.json').write_text(json.dumps(proof))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-class', 'other-variant', 'complete'])
def test_destination_execution_requires_each_complete_row_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_DESTINATION_STRESS_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert len(result['cases']) == 6 and {c['status'] for c in result['cases'].values()} == {'DESTINATION_STRESS_CONTROL_PASS'}
