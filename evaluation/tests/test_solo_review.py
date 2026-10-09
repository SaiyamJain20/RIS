"""Disclosed solo review mode (A1-0059, A1-0061 D-1/D-3); strict mode unchanged.

Synthetic header parser controls only. These byte strings are never stored or
used as ACKs. Git blob reads and ancestry are replaced by in-memory doubles so
no repository write happens.
"""
import hashlib
import importlib
import json

import pytest


def e1():
    return importlib.import_module('evaluation.e1')


def e2():
    return importlib.import_module('evaluation.e2')


SOLO = 'solo-correlated'


def solo_plan(freeze='S3-0005'):
    return e1().create_plan(run_id='E2-solo-test', freeze_message=freeze, review_mode=SOLO)


def ack(message_id, sender, plan_sha, freeze='S3-0005', to='agent-3 (proxy)', interface='v1', kind='ACK'):
    return (f'Message-ID: {message_id}\nFrom: {sender}\nTo: {to}\nRQ: E\nType: {kind}\n'
            f'Interface-version: {interface}\nResponds-to: {freeze}\nAccepted-plan-sha256: {plan_sha}\n').encode()


def test_solo_plan_records_mode_ports_and_unchanged_chain_ids():
    plan = solo_plan(); e1().verify_plan(plan)
    assert plan['reviewMode'] == SOLO and plan['reviewDirective'] == 'A1-0059'
    assert 'correlated' in plan['reviewDisclosure']
    assert plan['ports'] == dict(pbc=18545, dbc=18546)
    assert plan['chainIds'] == dict(pbc='18545', dbc='28545')
    assert all(18545 <= port <= 18599 for port in plan['ports'].values())
    assert plan['castHashPolicy'] == 'checkpoint'


def test_strict_plan_keeps_previous_shape():
    plan = e1().create_plan(run_id='E1-test', freeze_message='A3-0027')
    assert 'reviewMode' not in plan and 'castHashPolicy' not in plan
    assert plan['ports'] == dict(pbc=18545, dbc=28545)


@pytest.mark.parametrize('mode,freeze', [('strict', 'S3-0005'), (SOLO, 'A3-0050'), (SOLO, 'S2-0005'), ('relaxed', 'S3-0005')])
def test_freeze_identity_cannot_cross_modes(mode, freeze):
    with pytest.raises(ValueError):
        e1().create_plan(run_id='E2-solo-test', freeze_message=freeze, review_mode=mode)


@pytest.mark.parametrize('change', ['mode', 'ports', 'policy', 'disclosure'])
def test_solo_plan_fields_are_verified(change):
    plan = solo_plan()
    if change == 'mode': plan['reviewMode'] = 'strict'
    if change == 'ports': plan['ports']['dbc'] = 28545
    if change == 'policy': plan['castHashPolicy'] = 'per-call'
    if change == 'disclosure': plan['reviewDisclosure'] = 'independent review'
    with pytest.raises(ValueError):
        e1().verify_plan(plan)


def test_solo_ack_headers_accept_only_owner_identities():
    m = e1(); plan = solo_plan(); sha = 'ab'*32
    assert m.verify_ack_message(ack('A1-0062', 'agent-1', sha), agent='agent-1', plan=plan, plan_sha256=sha) == 'A1-0062'
    proxy = ack('S2-0004', 'agent-2 (proxy-2, acting for absent agent 2)', sha)
    assert m.verify_ack_message(proxy, agent='agent-2', plan=plan, plan_sha256=sha) == 'S2-0004'


@pytest.mark.parametrize('agent,raw', [
    ('agent-2', ack('A2-0040', 'agent-2', 'ab'*32)),                      # never impersonate absent agent 2
    ('agent-2', ack('S2-0004', 'agent-2', 'ab'*32)),                      # proxy must be declared
    ('agent-1', ack('S1-0001', 'agent-1', 'ab'*32)),
    ('agent-1', ack('A1-0062', 'agent-1', 'cd'*32)),                      # other plan
    ('agent-1', ack('A1-0062', 'agent-1', 'ab'*32, freeze='S3-0004')),    # other freeze
    ('agent-1', ack('A1-0062', 'agent-1', 'ab'*32, to='agent-2 (proxy)')),
    ('agent-1', ack('A1-0062', 'agent-1', 'ab'*32, interface='v1 (FREEZE f700292e..)')),
    ('agent-1', ack('A1-0062', 'agent-1', 'ab'*32, kind='REVIEW')),
    ('agent-3', ack('S3-0006', 'agent-3 (proxy)', 'ab'*32)),              # no self ACK
])
def test_solo_ack_headers_refuse_wrong_identity_scope_or_revision(agent, raw):
    with pytest.raises(ValueError):
        e1().verify_ack_message(raw, agent=agent, plan=solo_plan(), plan_sha256='ab'*32)


def test_strict_mode_still_refuses_proxy_acks():
    m = e1(); plan = m.create_plan(run_id='E1-test', freeze_message='A3-0027')
    raw = ack('S2-0004', 'agent-2 (proxy-2)', 'ab'*32, freeze='A3-0027', to='agent-3')
    with pytest.raises(ValueError):
        m.verify_ack_message(raw, agent='agent-2', plan=plan, plan_sha256='ab'*32)


def freeze_bytes(plan_sha, freeze='S3-0005'):
    return (f'Message-ID: {freeze}\nFrom: agent-3 (proxy)\nTo: agent-1, agent-2 (proxy)\nRQ: E\nType: FREEZE\n'
            f'Interface-version: v1\nResponds-to: A1-0061\nPlan-sha256: {plan_sha}\n').encode()


def index_for(blobs):
    return {key: dict(commit=commit, path=path, sha256=hashlib.sha256(blobs[(commit, path)]).hexdigest())
            for key, (commit, path) in {'agent-1': ('1'*40, 'communication/agent-1/outbox/0062-ack-sl1.md'),
                                         'agent-2': ('2'*40, 'communication/agent-1/solo/agent-2-proxy/outbox/0004-ack-sl1.md'),
                                         'freeze': ('3'*40, 'communication/agent-1/solo/agent-3-proxy/outbox/0005-freeze-sl1.md')}.items()}


@pytest.fixture
def solo_index(tmp_path, monkeypatch):
    m = e1(); plan = solo_plan(); raw = json.dumps(plan).encode(); sha = hashlib.sha256(raw).hexdigest()
    blobs = {('1'*40, 'communication/agent-1/outbox/0062-ack-sl1.md'): ack('A1-0062', 'agent-1', sha),
             ('2'*40, 'communication/agent-1/solo/agent-2-proxy/outbox/0004-ack-sl1.md'): ack('S2-0004', 'agent-2 (proxy-2)', sha),
             ('3'*40, 'communication/agent-1/solo/agent-3-proxy/outbox/0005-freeze-sl1.md'): freeze_bytes(sha)}
    ancestry = {'1'*40: True, '2'*40: True, '3'*40: True}
    monkeypatch.setattr(m, '_git_blob', lambda commit, path: blobs[(commit, path)])
    monkeypatch.setattr(m, '_solo_is_ancestor', lambda commit: ancestry[commit])
    return m, plan, sha, blobs, ancestry, tmp_path


def test_solo_ack_index_requires_committed_freeze_and_both_acks(solo_index):
    m, plan, sha, blobs, _, tmp_path = solo_index
    path = tmp_path/'acks.json'; path.write_text(json.dumps(index_for(blobs)))
    checked = m._acks(path, plan, sha)
    assert {k: v['messageId'] for k, v in checked.items()} == {'agent-1': 'A1-0062', 'agent-2': 'S2-0004', 'freeze': 'S3-0005'}
    assert all(v['commit'] and v['sha256'] for v in checked.values())


@pytest.mark.parametrize('change', ['missing-freeze', 'freeze-plan-hash', 'not-ancestor', 'wrong-path', 'blob-hash', 'extra-key'])
def test_solo_ack_index_refuses_unbound_or_uncommitted_records(solo_index, change):
    m, plan, sha, blobs, ancestry, tmp_path = solo_index
    index = index_for(blobs)
    if change == 'missing-freeze': index.pop('freeze')
    if change == 'freeze-plan-hash':
        key = ('3'*40, 'communication/agent-1/solo/agent-3-proxy/outbox/0005-freeze-sl1.md')
        blobs[key] = freeze_bytes('cd'*32); index = index_for(blobs)
    if change == 'not-ancestor': ancestry['2'*40] = False
    if change == 'wrong-path':
        key = ('2'*40, 'communication/agent-2/outbox/0004-ack-sl1.md'); blobs[key] = blobs[('2'*40, 'communication/agent-1/solo/agent-2-proxy/outbox/0004-ack-sl1.md')]
        index['agent-2']['path'] = key[1]
    if change == 'blob-hash': index['agent-1']['sha256'] = '00'*32
    if change == 'extra-key': index['agent-3'] = index['freeze']
    path = tmp_path/'acks.json'; path.write_text(json.dumps(index))
    with pytest.raises(ValueError):
        m._acks(path, plan, sha)


def test_solo_e2_plan_and_blocked_record_disclose_mode(tmp_path):
    m = e2(); plan = m.create_plan(run_id='E2-solo-test', freeze_message='S3-0005', review_mode=SOLO)
    m.verify_plan(plan)
    assert plan['reviewMode'] == SOLO and plan['ports'] == dict(pbc=18545, dbc=18546)
    path = tmp_path/'plan.json'; path.write_text(json.dumps(plan))
    result = m.execute(path, None, tmp_path/'out')
    assert result['status'] == 'BLOCKED' and result['servicesStarted'] == [] and result['reviewMode'] == SOLO
    assert 'correlated' in result['reviewDisclosure']
