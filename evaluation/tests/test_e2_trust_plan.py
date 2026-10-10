"""SL5 trust-freshness plan: six exact E02 rows, solo-only, fail-closed per row.

The owner signed-list producer (ledger/tools/sign_list.sh + script/SignList.s.sol, A1-0034, confirmed
in A1-0061 D-6) is pinned by path, sha256 and exact per-variant invocation; its argv is built only
from that template. No services: the profile executor is a control-flow double.
"""
import hashlib
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOLO = 'solo-correlated'
SIGN_LIST_SHA256 = '806e9a98a52899ca5fc4fe33e1e90e39d7607a51a4f5c6c5942c0edd21c37ded'
SIGN_SCRIPT_SHA256 = '7aa3b1dd085f5aaaa6aa7b28191d3b6d0cfd3ff02bb0b61291daead13e3ba177'
PROFILES = ('paper-strict', 'paper-minimal', 'repaired-e')
ROWS = [(p, v) for v in ('wrong-issuer', 'signed-list-rollback') for p in PROFILES]
EXPECTED = {**{(p, 'wrong-issuer'): ('SUPPORTED', 'UNAUTHORIZED_CALLER') for p in PROFILES},
            ('paper-strict', 'signed-list-rollback'): ('SPEC_GAP', None), ('paper-minimal', 'signed-list-rollback'): ('SPEC_GAP', None),
            ('repaired-e', 'signed-list-rollback'): ('REPAIR_SUPPORTED', 'STALE_ANCHOR')}
TEMPLATES = {'signed-list-rollback': ['{bash}', '{script}', '{pbcRpc}', '{deployment}', '{out}', 'crl', 'H1', '--revoke', '101'],
             'wrong-issuer': ['{bash}', '{script}', '{pbcRpc}', '{deployment}', '{out}', 'crl', 'H2']}


def module():
    return importlib.import_module('evaluation.e2')


def plan():
    return module().create_plan(run_id='E2-trust-test', freeze_message='S3-0015', trust_stress=True, review_mode=SOLO)


def test_trust_plan_pins_six_frozen_rows_and_solo_configuration():
    p = plan(); module().verify_plan(p)
    assert [(r['profile'], r['variant']) for r in p['matrix']] == ROWS
    assert p['caseIds'] == ['E02-'+v+'-'+pr for pr, v in ROWS]
    assert p['trustStress'] is True and p['fullCatalogComplete'] is False and 'workerExpected' not in p
    assert p['reviewMode'] == SOLO and p['ports'] == dict(pbc=18545, dbc=18546) and p['castHashPolicy'] == 'checkpoint'
    catalog = {c['id']: c for c in json.loads((ROOT/'evaluation/scenarios/e0_cases.json').read_text())['cases']}
    for (profile, variant), cid in zip(ROWS, p['caseIds']):
        c = catalog[cid]
        assert c['variant'] == variant and c['profile'] == profile
        assert (c['expected']['classification'], c['expected']['error']) == EXPECTED[(profile, variant)]


def test_trust_probe_pins_the_owner_signing_tool_and_conditions():
    p = plan(); tool = p['trustProbe']['signList']; ledger = p['owners']['ledger']['entries']
    assert tool['script'] == 'ledger/tools/sign_list.sh' and tool['scriptSha256'] == SIGN_LIST_SHA256 == ledger[tool['script']]
    assert tool['forgeScript'] == 'ledger/script/SignList.s.sol' and tool['forgeScriptSha256'] == SIGN_SCRIPT_SHA256 == ledger[tool['forgeScript']]
    assert tool['invocations'] == TEMPLATES and tool['cwd'] == 'materialized ledger snapshot root'
    text = ' '.join(tool['conditions'])
    for needle in ('A1-0034', 'A1-0061', 'non-zero exit', 'failed trial', 'same deployment file', 'TEST-ONLY', 'never writes keys',
                   'sha256 and first line', 'own EIP-712'):
        assert needle in text, needle
    probe = p['trustProbe']
    for needle in ('TMSC.sol:181', 'D-record N-1', 'not a repair'):
        assert needle in probe['wrongIssuer'], needle
    for needle in ('TMSC.sol:190', 'current authEpoch', 'A1-0064', 'bootstrap', 'REVOKED(19)'):
        assert needle in probe['signedListRollback'], needle
    for needle in ('prepare_request', 'every catalog step', 'D49', 'no worker operation'):
        assert needle in probe['workerPrecondition'], needle


@pytest.mark.parametrize('variant', ['signed-list-rollback', 'wrong-issuer'])
def test_sign_list_argv_is_built_only_from_the_pinned_template(variant):
    e1 = module().e1; tool = plan()['trustProbe']['signList']
    argv = e1.sign_list_argv(tool, variant=variant, bash='/usr/bin/bash', script=Path('/s/ledger/tools/sign_list.sh'),
                             pbc_rpc='http://127.0.0.1:18545', deployment=Path('/s/deployment.json'), out=Path('/o/trust-sign-list-00.json'))
    tail = ['crl', 'H1', '--revoke', '101'] if variant == 'signed-list-rollback' else ['crl', 'H2']
    assert argv == ['/usr/bin/bash', '/s/ledger/tools/sign_list.sh', 'http://127.0.0.1:18545', '/s/deployment.json', '/o/trust-sign-list-00.json']+tail


@pytest.mark.parametrize('change', ['variant', 'rpc', 'out', 'template', 'extra-version'])
def test_sign_list_argv_refuses_anything_else(change):
    e1 = module().e1; tool = plan()['trustProbe']['signList']
    kwargs = dict(variant='wrong-issuer', bash='/usr/bin/bash', script=Path('/s/ledger/tools/sign_list.sh'), pbc_rpc='http://127.0.0.1:18545',
                  deployment=Path('/s/deployment.json'), out=Path('/o/trust-sign-list-00.json'))
    if change == 'variant': kwargs['variant'] = 'receipt-binding-control'
    if change == 'rpc': kwargs['pbc_rpc'] = 'http://127.0.0.1:19545'
    if change == 'out': kwargs['out'] = Path('relative.json')
    if change == 'template': tool = dict(tool, invocations=dict(tool['invocations'], **{'wrong-issuer': TEMPLATES['wrong-issuer'][:-1]}))
    if change == 'extra-version':
        tool = dict(tool, invocations=dict(tool['invocations'], **{'wrong-issuer': TEMPLATES['wrong-issuer']+['--version', '1']}))
    with pytest.raises(ValueError):
        e1.sign_list_argv(tool, **kwargs)


@pytest.mark.parametrize('options', [dict(review_mode='strict', freeze_message='A3-0050'), dict(receipt_stress=True),
                                     dict(audit_stress=True), dict(relay_stress=True), dict(subject_substitution=True)])
def test_trust_plan_refuses_strict_mode_and_combined_probes(options):
    kwargs = dict(run_id='E2-trust-test', freeze_message='S3-0015', trust_stress=True, review_mode=SOLO); kwargs.update(options)
    with pytest.raises(ValueError):
        module().create_plan(**kwargs)


@pytest.mark.parametrize('change', ['row', 'tool-sha', 'invocation', 'classification'])
def test_changed_trust_plan_refuses(change):
    p = plan()
    if change == 'row': p['matrix'][0]['variant'] = 'fabricated-outcome'
    if change == 'tool-sha': p['trustProbe']['signList']['scriptSha256'] = hashlib.sha256(b'other').hexdigest()
    if change == 'invocation': p['trustProbe']['signList']['invocations']['wrong-issuer'].append('--version')
    if change == 'classification': p['classification'] = 'HMBC vulnerability'
    with pytest.raises(ValueError):
        module().verify_plan(p)


def supplied(mode):
    def profile(plan, profile, output, record, *, recovery_point, expired_retry, trust_stress):
        assert recovery_point is None and expired_retry is False
        if mode == 'missing': return
        classification, error = EXPECTED[(profile, trust_stress)]
        proof = dict(ok=True, delivery='unknown', classification=classification, error=error, variant=trust_stress)
        if mode == 'wrong-class': proof['classification'] = 'SPEC_GAP' if classification != 'SPEC_GAP' else 'SUPPORTED'
        if mode == 'other-variant': proof['variant'] = 'forged-tuple'
        (output/'trust-stress').mkdir(parents=True); (output/'trust-stress/result.json').write_text(json.dumps(proof))
    return profile


@pytest.mark.parametrize('mode', ['missing', 'wrong-class', 'other-variant', 'complete'])
def test_trust_execution_requires_each_complete_row_proof(tmp_path, monkeypatch, mode):
    m = module(); path = tmp_path/'plan.json'; path.write_text(json.dumps(plan()))
    monkeypatch.setattr(m.e1, '_acks', lambda *args: {'TEST_ONLY': 'not peer evidence'})
    monkeypatch.setattr(m.e1, '_profile', supplied(mode))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == ('E2_TRUST_STRESS_SLICE_PASS' if mode == 'complete' else 'FAILED')
    if mode == 'complete':
        assert len(result['cases']) == 6 and {c['status'] for c in result['cases'].values()} == {'TRUST_STRESS_CONTROL_PASS'}
