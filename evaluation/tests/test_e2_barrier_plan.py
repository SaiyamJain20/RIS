"""SL6 barrier plan: nine exact E02 rows (pre-barrier, post-barrier, expired duty), solo-only, fail-closed per row.

The owner signed-list producer (A1-0034, A1-0061 D-6) is pinned by path, sha256 and per-purpose
invocation; the short-duty window length is the only runner-computed argument and is bounded.
No services: the profile executor is a control-flow double.
"""
import hashlib
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOLO = 'solo-correlated'
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
VARIANTS = ('pre-barrier-revocation', 'post-barrier-revocation', 'expired-duty')
ROWS = [(p, v) for v in VARIANTS for p in PROFILES]
EXPECTED = {**{(p, v): ('SPEC_GAP', None) for p in PROFILES[:2] for v in VARIANTS},
            ('repaired-e', 'pre-barrier-revocation'): ('REPAIR_SUPPORTED', None),
            ('repaired-e', 'post-barrier-revocation'): ('REPAIR_SUPPORTED', 'STALE_STATE'),
            ('repaired-e', 'expired-duty'): ('REPAIR_SUPPORTED', 'EXPIRED')}
TEMPLATES = {'revoke-alice': ['{bash}', '{script}', '{pbcRpc}', '{deployment}', '{out}', 'crl', 'H1', '--revoke', '101'],
             'short-duty': ['{bash}', '{script}', '{pbcRpc}', '{deployment}', '{out}', 'tempacl', 'H1', '--duty', 'alice:60:{untilIn}']}


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-barrier-test', freeze_message='S3-0017', barrier_stress=True, review_mode=SOLO)


def test_barrier_plan_pins_nine_frozen_rows_and_solo_configuration():
    p = plan(); module().verify_plan(p)
    assert [(r['profile'], r['variant']) for r in p['matrix']] == ROWS
    assert p['caseIds'] == ['E02-'+v+'-'+pr for pr, v in ROWS]
    assert p['barrierStress'] is True and p['fullCatalogComplete'] is False and 'workerExpected' not in p
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    catalog = {c['id']: c for c in json.loads((ROOT/'evaluation/scenarios/e0_cases.json').read_text())['cases']}
    for (profile, variant), cid in zip(ROWS, p['caseIds']):
        c = catalog[cid]
        assert c['variant'] == variant and c['profile'] == profile
        assert (c['expected']['classification'], c['expected']['error']) == EXPECTED[(profile, variant)]


def test_barrier_probe_pins_tools_conditions_and_worker_precondition():
    p = plan(); tool = p['barrierProbe']['signList']; ledger = p['owners']['ledger']['entries']
    assert tool['script'] == 'ledger/tools/sign_list.sh' and tool['scriptSha256'] == ledger[tool['script']]
    assert tool['forgeScript'] == 'ledger/script/SignList.s.sol' and tool['forgeScriptSha256'] == ledger[tool['forgeScript']]
    assert tool['invocations'] == TEMPLATES and tool['untilInBounds'] == [25, 600]
    probe = p['barrierProbe']
    for needle in ('collected before the PBC update', 'exactly one collect_decision', 'A31', 'A1-0064'):
        assert needle in probe['certificateDiscipline'], needle
    for needle in ('only the DBC', 'evm_setNextBlockTimestamp', 'duty end', 'step 13', 'step 9', 'witness.py:133', 'witness.py:140',
                   'PBC clock is not moved'):
        assert needle in probe['expiredDuty'], needle
    for needle in ('STALE_STATE', 'step 10', 'ACCEPT_CHECKPOINT', 'omitted', 'line 87', 'sequence cause', 'expiresAt'):
        assert needle in probe['postBarrier'], needle
    for needle in ('window', 'intentional', 'no new checkpoint', 'REVOKE_ON_PBC before', 'authEpoch'):
        assert needle in probe['preBarrier'], needle
    for needle in ('ACSC.sol:140-167', 'CONDITIONAL', 'no record validUntil check', 'TTL'):
        assert needle in probe['paperRows'], needle
    for needle in ('25', '600', 'decision', '30 s'):
        assert needle in tool['untilInRule'], needle
    for needle in ('prepare_request', 'collect_checkpoint', 'collect_decision', 'every catalog step', 'D49'):
        assert needle in probe['workerPrecondition'], needle


@pytest.mark.parametrize('purpose,until_in', [('revoke-alice', None), ('short-duty', '31')])
def test_barrier_sign_argv_is_built_only_from_the_pinned_template(purpose, until_in):
    e1 = module().e1; tool = plan()['barrierProbe']['signList']
    argv = e1.barrier_sign_argv(tool, purpose=purpose, bash='/usr/bin/bash', script=Path('/s/ledger/tools/sign_list.sh'),
                                pbc_rpc='http://127.0.0.1:18545', deployment=Path('/s/deployment.json'), out=Path('/o/x.json'), until_in=until_in)
    tail = ['crl', 'H1', '--revoke', '101'] if purpose == 'revoke-alice' else ['tempacl', 'H1', '--duty', 'alice:60:31']
    assert argv == ['/usr/bin/bash', '/s/ledger/tools/sign_list.sh', 'http://127.0.0.1:18545', '/s/deployment.json', '/o/x.json']+tail


@pytest.mark.parametrize('change', ['purpose', 'until-low', 'until-high', 'until-text', 'until-on-crl', 'until-missing', 'template'])
def test_barrier_sign_argv_refuses_anything_else(change):
    e1 = module().e1; tool = plan()['barrierProbe']['signList']
    kwargs = dict(purpose='short-duty', bash='/usr/bin/bash', script=Path('/s/ledger/tools/sign_list.sh'), pbc_rpc='http://127.0.0.1:18545',
                  deployment=Path('/s/deployment.json'), out=Path('/o/x.json'), until_in='31')
    if change == 'purpose': kwargs['purpose'] = 'wrong-issuer'
    if change == 'until-low': kwargs['until_in'] = '24'
    if change == 'until-high': kwargs['until_in'] = '601'
    if change == 'until-text': kwargs['until_in'] = '30;rm'
    if change == 'until-on-crl': kwargs['purpose'] = 'revoke-alice'
    if change == 'until-missing': kwargs['until_in'] = None
    if change == 'template': tool = dict(tool, invocations=dict(tool['invocations'], **{'short-duty': TEMPLATES['short-duty'][:-1]}))
    with pytest.raises(ValueError):
        e1.barrier_sign_argv(tool, **kwargs)


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'), dict(trust_stress=True),
                                     dict(receipt_stress=True), dict(audit_stress=True)])
def test_barrier_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-barrier-test', freeze_message='S3-0017', barrier_stress=True, review_mode=SOLO); kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['row', 'tool-sha', 'invocation', 'bounds', 'classification'])
def test_changed_barrier_plan_refuses(change):
    p = plan()
    if change == 'row': p['matrix'][0]['variant'] = 'wrong-issuer'
    if change == 'tool-sha': p['barrierProbe']['signList']['scriptSha256'] = hashlib.sha256(b'other').hexdigest()
    if change == 'invocation': p['barrierProbe']['signList']['invocations']['revoke-alice'].append('--version')
    if change == 'bounds': p['barrierProbe']['signList']['untilInBounds'] = [1, 3600]
    if change == 'classification': p['classification'] = 'HMBC vulnerability'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, barrier_stress):
        assert recovery_point is None and expired_retry is False
        if mode == 'missing': return
        classification, error = EXPECTED[(profile, barrier_stress)]
        proof = dict(ok=True, delivery='unknown', classification=classification, error=error, variant=barrier_stress)
        if mode == 'wrong-class': proof['classification'] = 'SPEC_GAP' if classification != 'SPEC_GAP' else 'SUPPORTED'
        if mode == 'other-variant': proof['variant'] = 'wrong-issuer'
        (output/'barrier-stress').mkdir(parents=True); (output/'barrier-stress/result.json').write_text(json.dumps(proof))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-class', 'other-variant', 'complete'])
def test_barrier_execution_requires_each_complete_row_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_BARRIER_STRESS_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert len(result['cases']) == 9 and {c['status'] for c in result['cases'].values()} == {'BARRIER_STRESS_CONTROL_PASS'}
