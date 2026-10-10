"""SL3 audit-stress collector over the stateful synthetic world (TEST-ONLY double).

Extends the SL2 world with the production behaviours SL3 touches: lazy worker creation
by encrypt_record, release routing (paper: RSC registered key; repaired: grant recipient),
PSC.reportOutcome (paper accepts without DBC state; repaired WRONG_PROFILE) and the honest
witness attest_grant refusal (NOT_COMMITTED). Not ledger/protocol evidence; live runs are.
"""
import copy
import hashlib
import importlib
import json

import pytest
from eth_abi import encode
from eth_utils import keccak

from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_relay_stress_collector import NOW, World, Reverted, ok

ZERO = '0x'+'00'*32


class AuditWorld(World):
    def __init__(self, artifacts, inputs, profile, control=None):
        super().__init__(artifacts, inputs, profile, control)
        self.worker_state = None  # lazily created by encrypt_record, like the production adapter
        base = self.pbc.execute

        def execute(role, method, args, *, dry=False):
            if (role, method) == ('PSC', 'reportOutcome'):
                return self.report_outcome(*args)
            return base(role, method, args, dry=dry)
        self.pbc.execute = execute

    def report_outcome(self, digest, grant_id, outcome_digest):
        st = self.state; ts = self.ts+1
        if self.profile == 'repaired-e': raise Reverted('16' if self.control == 'other-code' else '21')
        if self.control == 'outcome-rejected': raise Reverted('8')
        rec = st['requests'].get(digest)
        if rec is None: raise Reverted('2')
        if rec['state']['status'] == '2': raise Reverted('8')
        if grant_id != self.grant_id(digest): raise Reverted('3')
        st['logid'] += 1; logid = str(st['logid'])
        relay = self.dep['fixture']['relay']['address']
        details = '0x'+encode(['bytes32', 'bytes32', 'bytes32', 'address'],
                              [bytes.fromhex(digest[2:]), bytes.fromhex(grant_id[2:]), bytes.fromhex(outcome_digest[2:]), relay]).hex()
        rec['state'].update(status='2', outcomeLogId=logid)
        return [logid], [('LSC', 'LogRecorded', dict(logId=logid, kind='4', subject=digest,
                                                    detailsHash='0x'+keccak(bytes.fromhex(details[2:])).hex(), details=details)),
                         ('PSC', 'OutcomeRecorded', dict(requestDigest=digest, grantId=grant_id, outcomeDigest=outcome_digest, logId=logid))]

    def exchange(self, envelope):
        op, inp = envelope['operation'], envelope['input']
        if op == 'encrypt_record':
            self.calls.append(op); rec, pol = inp['record'], inp['policy']
            pd = '0x'+keccak(encode(['(bytes32,uint8,uint8)[][]'], [[[(bytes.fromhex(q['role'][2:]), int(q['kind']), int(q['issuerMode']))
                                                                    for q in c] for c in pol['clauses']]])).hex()
            self.cipher = '0x'+keccak(encode(['bytes32', 'bytes32', 'address', 'bytes32', 'bytes32', 'uint64'],
                                             [keccak(text='HMBCSymbolicRecord/v1'), bytes.fromhex(rec['dataId'][2:]), rec['owner'],
                                              bytes.fromhex(rec['payloadDigest'][2:]), bytes.fromhex(pd[2:]), 0])).hex()
            if self.worker_state is None: self.worker_state = dict(events=[], releases=[])
            return ok(dict(dataId=rec['dataId'], keyEpoch='0', ciphertextDigest=self.cipher, policyDigest=pd))
        if op == 'release':
            self.calls.append(op); g = self.state['grants'].get(inp['grantId'])
            if g is None or self.control == 'release-expired' or self.ts+1 >= int(g['expiresAt']):
                return dict(schemaVersion='v1', ok=False, result=None, error=dict(code='EXPIRED', message='synthetic'))
            paper = self.profile != 'repaired-e'
            recipient = next(u['recipientKeyHash'] for u in self.users.values() if u['gid'] == g['gid']) if paper else g['recipientKeyHash']
            if self.control == 'wrong-recipient': recipient = '0x'+'b0'*32
            identity = dict(requestDigest=g['requestDigest'], grantId=inp['grantId'], gid=g['gid'], dataId=g['dataId'])
            sends = 2 if self.control == 'double-send' else 1
            self.worker_state['events'] += [dict(type='RELEASE_INTENT', timestamp=str(self.ts), **identity)] + \
                [dict(type='RELEASE_SENT', timestamp=str(self.ts), **identity)]*sends
            self.worker_state['releases'].append(dict(**identity, ciphertextDigest=self.cipher, recipientKeyHash=recipient, keyEpoch='0',
                                                      tokenDigest='0x290decd9548b62a8d60345a988386fc84ba6bc95484008f6362f93160ef3e563',
                                                      grantExpiresAt=g['expiresAt'], createdAt=str(self.ts), delivery='unknown',
                                                      sendAttempts=sends, completedAttempts=1))
            if self.control == 'outcome-leak':
                # Someone records an outcome between the release snapshots: pending must not hold.
                next(iter(self.state['requests'].values()))['state'].update(status='2', outcomeLogId='99')
                self.pbc.history[self.pbc.number] = copy.deepcopy(self.state)
            return ok(dict(requestDigest=g['requestDigest'], grantId=inp['grantId'], dataId=g['dataId'], ciphertextDigest=self.cipher,
                           recipientKeyHash=recipient, keyEpoch='0', responseEnvelope=dict(kind='symbolic-partial/v1', token=ZERO)))
        if op == 'attest_grant':
            self.calls.append(op)
            if self.profile != 'repaired-e':
                return dict(schemaVersion='v1', ok=False, result=None, error=dict(code='WRONG_PROFILE', message='synthetic'))
            if inp['grantId'] not in self.state['grants'] and self.control != 'attest-signs':
                return dict(schemaVersion='v1', ok=False, result=None, error=dict(code='NOT_COMMITTED', message='synthetic'))
            return dict(schemaVersion='v1', ok=False, result=None, error=dict(code='WRONG_SUBJECT', message='synthetic deviation'))
        return super().exchange(envelope)

    def worker(self):
        state = '/tmp/p3/synthetic-audit-state'
        if self.worker_state is None:
            return dict(instantiated=False, exitCode=1, message=f'no worker.sqlite in {state} (looked in <dir>/worker/ and in <dir>)\n',
                        checkedAbsent=[state+'/worker/worker.sqlite', state+'/worker.sqlite'])
        chains = self.dep['chains']
        fp = hashlib.sha256(json.dumps(dict(pbc=[chains['pbc']['chainId'], chains['pbc']['contracts']['PSC'], chains['pbc']['contracts']['RSC']],
                                            dbc=[chains['dbc']['chainId'], chains['dbc']['contracts']['KSSC'], chains['dbc']['contracts']['ACSC']]),
                                       sort_keys=True).encode()).hexdigest()
        ev, rel = self.worker_state['events'], self.worker_state['releases']
        counts = dict(releaseIntentCount=str(sum(e['type'] == 'RELEASE_INTENT' for e in ev)),
                      releaseSentCount=str(sum(e['type'] == 'RELEASE_SENT' for e in ev)))
        return dict(instantiated=True, export=json.dumps(dict(schemaVersion='hmbc-worker-log/v0', adapterMode='symbolic', deploymentFingerprint=fp,
                                                              note='synthetic worker', events=ev, releases=rel, counts=counts)).encode())


def collector():
    module = importlib.import_module('evaluation.audit_stress')
    assert hasattr(module, 'execute_audit_stress'), 'audit stress collector missing'
    return module.execute_audit_stress


def run(world, tmp_path, variant):
    return collector()(world.pbc, world.dbc, world, deployment_bytes=json.dumps(world.dep).encode(), user_label='alice',
                       user=world.users['alice'], record=world.record, policy=world.policy, variant=variant,
                       worker_snapshot=world.worker, output=tmp_path/'stress')


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_dropped_outcome_releases_once_and_stays_pending(artifacts, inputs, tmp_path, profile):
    w = AuditWorld(artifacts, inputs, profile)
    result = run(w, tmp_path, 'dropped-outcome')
    assert result['ok'] and result['outcome'] == 'PENDING'
    assert result['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SUPPORTED')
    assert w.calls.count('release') == 1 and 'attest_grant' not in w.calls and w.calls[0] == 'encrypt_record'
    assert next(iter(w.state['requests'].values()))['state']['status'] == '1'
    assert json.loads((tmp_path/'stress/before-release.json').read_text())['worker']['instantiated'] is True
    timeline = result['timeline']
    assert int(timeline['releaseDbcClock']) < int(timeline['grantExpiresAt'])


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_fabricated_outcome(artifacts, inputs, tmp_path, profile):
    w = AuditWorld(artifacts, inputs, profile)
    result = run(w, tmp_path, 'fabricated-outcome')
    assert result['ok'] and w.state['grants'] == {} and 'release' not in w.calls and 'encrypt_record' not in w.calls
    status = next(iter(w.state['requests'].values()))['state']['status']
    if profile == 'repaired-e':
        assert result['error'] == 'WRONG_PROFILE' and status == '1' and w.calls[-1] == 'attest_grant'
    else:
        assert result['classification'] == 'SPEC_GAP' and status == '2' and 'attest_grant' not in w.calls
    assert json.loads((tmp_path/'stress/before.json').read_text())['worker']['instantiated'] is False


@pytest.mark.parametrize('profile,variant,control', [
    ('paper-strict', 'dropped-outcome', 'outcome-leak'),
    ('repaired-e', 'dropped-outcome', 'release-expired'),
    ('paper-minimal', 'dropped-outcome', 'wrong-recipient'),
    ('repaired-e', 'dropped-outcome', 'double-send'),
    ('paper-strict', 'fabricated-outcome', 'outcome-rejected'),
    ('repaired-e', 'fabricated-outcome', 'other-code'),
    ('repaired-e', 'fabricated-outcome', 'attest-signs'),
])
def test_false_observations_fail_visibly(artifacts, inputs, tmp_path, profile, variant, control):
    w = AuditWorld(artifacts, inputs, profile, control)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is False


@pytest.mark.parametrize('variant', ['forged-tuple', 'duplicate-outcome', 'subject'])
def test_unsupported_variant_refuses_before_side_effects(artifacts, inputs, tmp_path, variant):
    w = AuditWorld(artifacts, inputs, 'paper-strict')
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert w.calls == [] and w.state['requests'] == {}
