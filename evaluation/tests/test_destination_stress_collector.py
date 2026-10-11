"""SL7 wrong-destination and expiry-boundary collector over stateful synthetic worlds (TEST-ONLY doubles).

Wrong destination uses two worlds: A (the receiver, "here") and B (a second deployment on the same chain
ids with other contract addresses), mirroring the second-deployment recipe (A1-0039). The receiver double
applies the pinned DecisionVerifier order: step 1 source chain/PSC (line 60) then step 2 destination
chain/KSSC (lines 61-64, skipped by MUT_NO_DESTINATION_BINDING), then the base request binding.
Expiry boundary uses one world whose DBC clock can be pinned with evm_setNextBlockTimestamp (no evm_mine),
so the consumption is the next mined block at exactly the requested time. Not ledger evidence.
"""
import copy
import hashlib
import importlib
import json

import pytest

from evaluation.tests.test_access_artifacts import artifacts, sign
from evaluation.tests.test_audit_stress_collector import AuditWorld
from evaluation.tests.test_barrier_stress_collector import ClockDbc
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_relay_stress_collector import Reverted, World, ok


class PinClockDbc(ClockDbc):
    """evm_setNextBlockTimestamp pins the next mined block (and its execution time) without evm_mine."""

    def call(self, method, params=None):
        if method == 'evm_setNextBlockTimestamp':
            extra = 1 if self.world.control == 'clock-plus-one' else 0
            self.offset = int(params[0])+extra-(self.world.ts+1); return None
        return super().call(method, params)


class DestWorld(World):
    worker = AuditWorld.worker

    def __init__(self, artifacts, inputs, profile, control=None):
        super().__init__(artifacts, inputs, profile, control)
        self.worker_state = None
        self.dbc = PinClockDbc(self, 'dbc')
        base = self.dbc.execute

        def dbc_execute(role, method, args, *, dry=False):
            if (role, method) == ('ACSC', 'consumeDecision'):
                req = args[0]; pbc, dbc = self.dep['chains']['pbc'], self.dep['chains']['dbc']
                if self.control != 'source-binding-ignored' and (req['sourceChainId'] != pbc['chainId'] or req['psc'] != pbc['contracts']['PSC']):
                    raise Reverted('3')                                               # DecisionVerifier step 1 (line 60)
                if self.control not in ('source-binding-ignored', 'destination-binding-ignored') and (
                        req['destinationChainId'] != dbc['chainId'] or req['kssc'] != dbc['contracts']['KSSC']):
                    raise Reverted('3')                                               # step 2 (lines 61-64)
                if self.control == 'equality-accepted':
                    self.ts -= 1
                    try:
                        return base(role, method, args, dry=dry)
                    finally:
                        self.ts += 1
            return base(role, method, args, dry=dry)
        self.dbc.execute = dbc_execute

    def exchange(self, envelope):
        op = envelope['operation']
        if op == 'prepare_request' and self.control == 'worker-appears':
            self.worker_state = dict(events=[], releases=[])
        reply = super().exchange(envelope)
        if op == 'collect_checkpoint':
            cp = dict(reply['result']['checkpoint'], expiresAt=str(self.ts+1+self.dbc.offset+50))
            reply = ok(dict(checkpoint=cp, signatures=[sign('StateCheckpoint', cp, self.dep, 'witness-1')[0]]))
        if op == 'collect_decision' and self.control == 'decision-capped':
            d = dict(reply['result']['decision']); d['expiresAt'] = str(int(d['expiresAt'])-1)
            reply = ok(dict(decision=d, signatures=[sign('AccessDecision', d, self.dep, 'witness-1')[0]],
                            credentialRecords=reply['result']['credentialRecords']))
        return reply


def relocated(artifacts):
    """Deployment B: same chain ids, other contract addresses (a second deployment on the same chain pair)."""
    arts = list(copy.deepcopy(artifacts)); dep = arts[0]
    for name in ('pbc', 'dbc'):
        for role in list(dep['chains'][name]['contracts']):
            dep['chains'][name]['contracts'][role] = '0x'+hashlib.sha256(('B'+name+role).encode()).hexdigest()[:40]
    cp = arts[3]['checkpoint']; cp['psc'] = dep['chains']['pbc']['contracts']['PSC']
    return tuple(arts)


def collector():
    module = importlib.import_module('evaluation.destination_stress')
    assert hasattr(module, 'execute_destination_stress'), 'destination stress collector missing'
    return module.execute_destination_stress


def run(a, tmp_path, variant, b=None):
    source = None if b is None else dict(pbc=b.pbc, dbc=b.dbc, adapter=b, deployment_bytes=json.dumps(b.dep).encode(), user=b.users['alice'],
                                         worker_snapshot=b.worker)
    return collector()(a.pbc, a.dbc, a, deployment_bytes=json.dumps(a.dep).encode(), user_label='alice', user=a.users['alice'], record=a.record,
                       policy=a.policy, variant=variant, worker_snapshot=a.worker, source=source, output=tmp_path/'stress')


PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']


@pytest.mark.parametrize('profile', PROFILES)
def test_wrong_destination(artifacts, inputs, tmp_path, profile):
    a = DestWorld(artifacts, inputs, profile); b = DestWorld(relocated(artifacts), inputs, profile)
    result = run(a, tmp_path, 'wrong-destination', b)
    repaired = profile == 'repaired-e'
    assert result['ok'] and (result['classification'], result['error']) == (('REPAIR_SUPPORTED', 'WRONG_DESTINATION') if repaired else ('SPEC_GAP', None))
    assert a.calls == [] and b.calls == ['prepare_request']+(['collect_checkpoint', 'collect_decision'] if repaired else [])
    assert b.state['grants'] == {} and bool(a.state['grants']) is (not repaired) and a.state['requests'] == {}
    assert [s['step'] for s in result['workerSteps']] == ['baseline', 'REQUEST_ACCESS', 'SUBSTITUTE_DESTINATION', 'FORWARD_OR_CONSUME']
    sub = json.loads((tmp_path/'stress/substitution.json').read_text())
    assert sub['request']['psc'] == b.dep['chains']['pbc']['contracts']['PSC'] and sub['receiver']['psc'] == a.dep['chains']['pbc']['contracts']['PSC']
    assert sub['signedFieldsRewritten'] is False
    if repaired: assert result['firingStep'] == 1 and result['step2Mismatch'] is True and result['decisionCollections'] == 1


def test_wrong_destination_cannot_kill_the_destination_binding_mutant(artifacts, inputs, tmp_path):
    # A1-0039 G-3 / A1 condition 2: step 1 still fires when step 2 is removed, so this row passes unchanged.
    a = DestWorld(artifacts, inputs, 'repaired-e', 'destination-binding-ignored'); b = DestWorld(relocated(artifacts), inputs, 'repaired-e')
    result = run(a, tmp_path, 'wrong-destination', b)
    assert result['ok'] and result['error'] == 'WRONG_DESTINATION' and result['firingStep'] == 1


@pytest.mark.parametrize('profile', PROFILES)
def test_expiry_boundary(artifacts, inputs, tmp_path, profile):
    a = DestWorld(artifacts, inputs, profile)
    result = run(a, tmp_path, 'expiry-boundary')
    repaired = profile == 'repaired-e'
    assert result['ok'] and (result['classification'], result['error']) == (('REPAIR_SUPPORTED', 'EXPIRED') if repaired else ('SPEC_GAP', None))
    t = json.loads((tmp_path/'stress/timeline.json').read_text())
    assert t['consumeTimestamp'] == t['requestExpiresAt'] and a.dbc.offset > 0
    assert [s['step'] for s in result['workerSteps']] == ['baseline', 'REQUEST_ACCESS', 'ADVANCE_CLOCK', 'FORWARD_OR_CONSUME']
    assert a.calls.count('collect_decision') == (1 if repaired else 0)
    if repaired: assert result['firingStep'] == 9 and not a.state['grants']
    else: assert next(iter(a.state['grants'].values()))['expiresAt'] == str(int(t['requestExpiresAt'])+30)


@pytest.mark.parametrize('profile,variant,control', [
    ('repaired-e', 'wrong-destination', 'source-binding-ignored'),
    ('paper-strict', 'wrong-destination', 'paper-deny'),
    ('repaired-e', 'expiry-boundary', 'clock-plus-one'),
    ('paper-minimal', 'expiry-boundary', 'clock-plus-one'),
    ('repaired-e', 'expiry-boundary', 'decision-capped'),
    ('repaired-e', 'expiry-boundary', 'equality-accepted'),
    ('repaired-e', 'wrong-destination', 'worker-appears'),
])
def test_false_observations_fail_visibly(artifacts, inputs, tmp_path, profile, variant, control):
    a = DestWorld(artifacts, inputs, profile, control)
    b = DestWorld(relocated(artifacts), inputs, profile, control if control == 'worker-appears' else None) if variant == 'wrong-destination' else None
    with pytest.raises(ValueError):
        run(a, tmp_path, variant, b)
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is False


@pytest.mark.parametrize('variant,with_source', [('expired-duty', False), ('wrong-issuer', False), ('wrong-destination', False),
                                                 ('expiry-boundary', True)])
def test_unsupported_selection_refuses_before_side_effects(artifacts, inputs, tmp_path, variant, with_source):
    a = DestWorld(artifacts, inputs, 'repaired-e'); b = DestWorld(relocated(artifacts), inputs, 'repaired-e')
    with pytest.raises(ValueError):
        run(a, tmp_path, variant, b if with_source else None)
    assert a.calls == [] and b.calls == [] and a.pbc.txs == {} and a.dbc.txs == {} and b.pbc.txs == {}
