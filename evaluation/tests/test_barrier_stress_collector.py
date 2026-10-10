"""SL6 revocation-barrier and expired-duty collector over the stateful synthetic world (TEST-ONLY double).

Extends the SL5 trust world with: a TempACL anchor and duty windows per generation; credentials that
honour revocation and duty windows at the queried time; a separate DBC clock (evm_setNextBlockTimestamp,
evm_mine move only the DBC); a witness double whose checkpoint carries the current authEpoch and whose
decision is DENY with empty records once a record has lapsed at DBC now; and the repaired
DecisionVerifier order (step 9 expiry, 10 sequence, 11 authEpoch, 13 record freshness). Not ledger or
protocol evidence; live runs are.
"""
import copy
import importlib
import json

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.tests.test_access_artifacts import artifacts, sign
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_relay_stress_collector import FakeChain, Reverted, ok
from evaluation.tests.test_trust_stress_collector import TrustChain, TrustWorld
from evaluation.vectors import credential_digest

ONDUTY = '0x'+keccak(text='HMBC.role.OnDuty').hex()


def acl_typed(body, dep):
    vectors = json.load(open('interfaces/v1/vectors/eip712-agent1.json'))['vectors']
    typed = copy.deepcopy(next(v['typedData'] for v in vectors if v['name'] == 'TemporalAcl'))
    pbc = dep['chains']['pbc']
    typed['domain'].update(chainId=pbc['chainId'], verifyingContract=pbc['contracts']['TMSC'])
    typed['message'] = body
    encoded = encode_typed_data(full_message=typed)
    return encoded, '0x'+keccak(b'\x19'+encoded.version+encoded.header+encoded.body).hex()


def sign_acl(body, dep, label):
    encoded, digest = acl_typed(body, dep)
    return '0x'+Account.sign_message(encoded, keccak(text='hmbc-e0-synthetic-key:'+label)).signature.hex(), digest


class BarrierPbc(TrustChain):
    def read(self, role, method, *args, block=None):
        w = self.world; st = self.history[int((block or self.latest_block())['number'], 16)]
        if method == 'temporalAclState': return [copy.deepcopy(st['acl'].get(args[0], dict(published=False, version='0', validUntil='0',
                                                                                              generation='0', contentDigest='0x'+'00'*32,
                                                                                              blockNumber='0', prevBlockNumber='0')))]
        if method == 'checkCredentials': return list(w.credentials(st, args[0], int(args[2])))
        return super().read(role, method, *args, block=block)


class ClockDbc(FakeChain):
    offset = 0; next_ts = None

    def _mine(self, txs):
        block = super()._mine(txs)
        block['timestamp'] = hex(int(block['timestamp'], 16)+self.offset); self.blocks[self.number] = block
        return copy.deepcopy(block)

    def call(self, method, params=None):
        if method == 'evm_setNextBlockTimestamp':
            self.next_ts = int(params[0]); return None
        if method == 'evm_mine':
            if self.next_ts is not None:
                self.offset = self.next_ts-(self.world.ts+1); self.next_ts = None
            self._mine([]); return '0x0'
        if method == 'eth_getBlockByNumber' and params[0] == 'pending':
            return dict(self.latest_block(), timestamp=hex(self.world.ts+1+self.offset))
        return super().call(method, params)

    def execute(self, role, method, args, *, dry=False):
        self.world.ts += self.offset
        try:
            return super().execute(role, method, args, dry=dry)
        finally:
            self.world.ts -= self.offset


class BarrierWorld(TrustWorld):
    def __init__(self, artifacts, inputs, profile, control=None):
        super().__init__(artifacts, inputs, profile, control)
        alice = self.users['alice']['gid']
        acl = next(it for it in self.bootstrap['trustLists'] if it['kind'] == 'TemporalAcl')
        body = acl['list']; entry = next(e for e in body['entries'] if e['gid'] == alice)
        self.state.update(acl={self.h1: dict(published=True, version=body['version'], validUntil=body['validUntil'], generation='1',
                                             contentDigest=acl_typed(body, self.dep)[1], blockNumber='299', prevBlockNumber='0')},
                          duty={(self.h1, '1'): (int(entry['validFrom']), int(entry['validUntil']))})
        self.pbc = BarrierPbc(self, 'pbc'); self.dbc = ClockDbc(self, 'dbc')
        base_pbc, base_dbc = self.pbc.execute, self.dbc.execute

        def pbc_execute(role, method, args, *, dry=False):
            if (role, method) == ('TMSC', 'updateRevocationList'):
                if self.control == 'revocation-not-applied': args = [dict(args[0], revokedSerials=[]), args[1]]
                return self.update(*args)
            if (role, method) == ('TMSC', 'updateTemporalAcl'): return self.update_acl(*args)
            if (role, method) == ('PSC', 'requestAccess'):
                denied = self.denial(args[0])
                if denied is not None: return denied
            return base_pbc(role, method, args, dry=dry)

        def dbc_execute(role, method, args, *, dry=False):
            if (role, method) == ('ACSC', 'consumeDecision'): self.verifier(*args)
            return base_dbc(role, method, args, dry=dry)
        self.pbc.execute = pbc_execute; self.dbc.execute = dbc_execute

    # ---- TMSC TempACL and credentials
    def update_acl(self, body, signature):
        st = self.state; root = body['authority']; ts = self.ts+1
        if self.admins.get(root) != self.sender: raise Reverted('16')
        encoded, digest = acl_typed(body, self.dep)
        if self.profile != 'paper-minimal' and Account.recover_message(encoded, signature=signature).lower() != root: raise Reverted('1')
        a = st['acl'].get(root)
        if self.profile == 'repaired-e' and a and int(body['version']) <= int(a['version']): raise Reverted('5')
        generation = str(int(a['generation'])+1 if a else 1); prev = a['blockNumber'] if a else '0'
        for e in body['entries']:
            if e['gid'] == self.users['alice']['gid'] and e['role'] == ONDUTY:
                st['duty'][(root, generation)] = (int(e['validFrom']), int(e['validUntil']))
        st['acl'][root] = dict(published=True, version=body['version'], validUntil=body['validUntil'], generation=generation,
                               contentDigest=digest, blockNumber=str(self.pbc.number+1), prevBlockNumber=prev)
        st['epoch'] += 1; st['logid'] += 1
        return [generation], [('LSC', 'LogRecorded', dict(logId=str(st['logid']), kind='2', subject='0x'+'5a'*32, detailsHash='0x'+'5b'*32,
                                                         details='0x')),
                              ('TMSC', 'TrustAnchorUpdated', dict(authority=root, kind='2', version=body['version'], validUntil=body['validUntil'],
                                                                  generation=generation, contentDigest=digest, prevBlockNumber=prev,
                                                                  authEpoch=str(st['epoch']), submitter=self.sender))]

    def records_for(self, gid):
        records = super().records_for(gid)
        if gid == self.users['alice']['gid']:
            a = self.state['acl'][self.h1]; window = self.state['duty'].get((self.h1, a['generation']))
            for r in records:
                if r['kind'] == '2':
                    r['anchorVersion'] = a['version']
                    until = window[1] if window else 0
                    r['validUntil'] = str(min(until, int(a['validUntil'])) if self.profile == 'repaired-e' else until)
        return records

    def credentials(self, st, gid, at=None):
        code, records = super().credentials(st, gid)
        if code != '0' or gid != self.users['alice']['gid']: return code, records
        a = st['acl'][self.h1]; window = st['duty'].get((self.h1, a['generation']))
        at = self.ts+1 if at is None else at
        if window is None: return '19', []
        if not window[0] <= at < window[1]: return '7', []
        return code, records

    # ---- witness double (checkpoint authEpoch, lapsed-record DENY)
    def exchange(self, envelope):
        op, inp = envelope['operation'], envelope['input']
        if op == 'collect_checkpoint':
            self.calls.append(op)
            src = self.pbc.latest_block(); current = self.state['checkpoint']; dbc_now = self.ts+1+self.dbc.offset
            cp = dict(self.default_cp, sequence=str(int(current['sequence'])+1 if current else 1), authEpoch=str(self.state['epoch']),
                      sourceBlockNumber=str(self.pbc.number), sourceBlockHash=src['hash'], expiresAt=str(dbc_now+50))
            return ok(dict(checkpoint=cp, signatures=[sign('StateCheckpoint', cp, self.dep, 'witness-1')[0]]))
        if op == 'collect_decision':
            reply = super().exchange(envelope)
            d = reply['result']['decision']; records = reply['result']['credentialRecords']
            dbc_now = self.ts+1+self.dbc.offset
            if any(int(r['validUntil']) <= dbc_now for r in records):
                d = dict(d, result='0', credentialDigest=credential_digest([]))
                reply = ok(dict(decision=d, signatures=[sign('AccessDecision', d, self.dep, 'witness-1')[0]], credentialRecords=[]))
            return reply
        return super().exchange(envelope)

    def verifier(self, req, cert, records):
        """DecisionVerifier steps 9, 10, 11, 13 in order (earlier steps are in the base double)."""
        d = cert['decision']; ts = self.ts+1+self.dbc.offset; cp = self.state['checkpoint']
        if ts >= int(d['expiresAt']) or ts >= int(req['expiresAt']): raise Reverted('7')
        barrier = self.control != 'barrier-ignored'
        if cp is None or ts >= int(cp['expiresAt']) or (barrier and d['stateSequence'] != cp['sequence']): raise Reverted('6')
        if barrier and req['authEpoch'] != cp['authEpoch']: raise Reverted('6')
        if self.control != 'freshness-ignored' and any(ts >= int(r['validUntil']) for r in records): raise Reverted('7')
        if self.control == 'barrier-ignored' and cp: self.state['checkpoint'] = dict(cp, sequence=d['stateSequence'])

    # ---- producer double
    def sign_list(self, purpose, until_in=None):
        self.signed.append((purpose, until_in))
        if self.control == 'tool-fails': return dict(exitCode=1, output=b'error: PBC chain id differs from deployment.json\n')
        if purpose == 'revoke-alice':
            answer = TrustWorld.sign_list(self, 'signed-list-rollback'); self.signed.pop()
            return answer
        t = self.ts; root = self.h1; a = self.state['acl'][root]
        until = 1 if self.control == 'duty-too-short' else int(until_in)
        body = dict(authority=root, version=str(int(a['version'])+1), validUntil=str(t+86400),
                    entries=[dict(gid=self.users['alice']['gid'], role=ONDUTY, validFrom=str(t-60), validUntil=str(t+until))])
        signature, _ = sign_acl(body, self.dep, 'H1-root')
        doc = json.loads(TrustWorld.sign_list(self, 'signed-list-rollback')['output']); self.signed.pop()
        doc['item'] = dict(kind='TemporalAcl', call='TMSC.updateTemporalAcl', submitterRole='H1-ca-admin', submitter=self.auth['H1']['caAdmins'][0],
                           list=body, signature=signature, signer=root)
        doc['binding']['blockTimestamp'] = str(t)
        return dict(exitCode=0, output=json.dumps(doc).encode())


def collector():
    module = importlib.import_module('evaluation.barrier_stress')
    assert hasattr(module, 'execute_barrier_stress'), 'barrier stress collector missing'
    return module.execute_barrier_stress


def run(world, tmp_path, variant):
    return collector()(world.pbc, world.dbc, world, deployment_bytes=json.dumps(world.dep).encode(), bootstrap=world.bootstrap,
                       user_label='alice', user=world.users['alice'], record=world.record, policy=world.policy, variant=variant,
                       worker_snapshot=world.worker, sign_list=world.sign_list, output=tmp_path/'stress')


PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']
VARIANTS = ['pre-barrier-revocation', 'post-barrier-revocation', 'expired-duty']
EXPECTED = {**{(p, v): ('SPEC_GAP', None) for p in PROFILES[:2] for v in VARIANTS},
            ('repaired-e', 'pre-barrier-revocation'): ('REPAIR_SUPPORTED', None),
            ('repaired-e', 'post-barrier-revocation'): ('REPAIR_SUPPORTED', 'STALE_STATE'),
            ('repaired-e', 'expired-duty'): ('REPAIR_SUPPORTED', 'EXPIRED')}


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('variant', VARIANTS)
def test_barrier_rows(artifacts, inputs, tmp_path, profile, variant):
    w = BarrierWorld(artifacts, inputs, profile)
    result = run(w, tmp_path, variant)
    assert result['ok'] and (result['classification'], result['error']) == EXPECTED[(profile, variant)]
    repaired = profile == 'repaired-e'
    assert w.calls.count('collect_decision') == (1 if repaired else 0)   # A31: exactly one per request, never re-collected
    assert 'release' not in w.calls and 'encrypt_record' not in w.calls
    steps = {'pre-barrier-revocation': ['REQUEST_ACCESS', 'REVOKE_ON_PBC', 'FORWARD_OR_CONSUME'],
             'post-barrier-revocation': ['REQUEST_ACCESS', 'REVOKE_ON_PBC']+(['ACCEPT_CHECKPOINT'] if repaired else [])+['FORWARD_OR_CONSUME'],
             'expired-duty': ['INSTALL_SHORT_DUTY', 'REQUEST_ACCESS', 'ADVANCE_CLOCK', 'FORWARD_OR_CONSUME']}[variant]
    assert [s['step'] for s in result['workerSteps']] == ['baseline']+steps
    if variant == 'expired-duty':
        assert w.dbc.offset > 0 and w.signed[0][0] == 'short-duty' and 25 <= int(w.signed[0][1]) <= 600
    else:
        assert w.dbc.offset == 0 and w.signed == [('revoke-alice', None)]
    if repaired and variant == 'post-barrier-revocation':
        assert w.calls.count('collect_checkpoint') == 2
    granted = (not repaired) or variant == 'pre-barrier-revocation'
    assert bool(w.state['grants']) is granted
    facts = json.loads((tmp_path/'stress/facts.json').read_text())
    if repaired:   # A1: the checkpoint current at consumption is recorded (first one, or the post-revocation one)
        assert facts['current_checkpoint'] == facts['checkpoints'][-1]
    timing = result['timing']; assert timing['consumeTimestamp'] == json.loads((tmp_path/'stress/timeline.json').read_text())['consumeTimestamp']
    if (profile, variant) == ('repaired-e', 'post-barrier-revocation'): assert result['staleCause'] == 'sequence'
    if (profile, variant) == ('repaired-e', 'expired-duty'): assert result['expiredStep'] == 13


@pytest.mark.parametrize('profile,variant,control', [
    ('repaired-e', 'pre-barrier-revocation', 'tool-fails'),
    ('paper-strict', 'expired-duty', 'tool-fails'),
    ('repaired-e', 'post-barrier-revocation', 'barrier-ignored'),
    ('repaired-e', 'expired-duty', 'freshness-ignored'),
    ('paper-minimal', 'pre-barrier-revocation', 'revocation-not-applied'),
    ('repaired-e', 'expired-duty', 'duty-too-short'),
    ('repaired-e', 'pre-barrier-revocation', 'worker-appears'),
])
def test_false_observations_fail_visibly(artifacts, inputs, tmp_path, profile, variant, control):
    w = BarrierWorld(artifacts, inputs, profile, control)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is False


@pytest.mark.parametrize('variant', ['wrong-issuer', 'signed-list-rollback', 'receipt-binding-control'])
def test_unsupported_variant_refuses_before_side_effects(artifacts, inputs, tmp_path, variant):
    w = BarrierWorld(artifacts, inputs, 'repaired-e')
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert w.calls == [] and w.signed == [] and w.pbc.txs == {} and w.dbc.txs == {}
