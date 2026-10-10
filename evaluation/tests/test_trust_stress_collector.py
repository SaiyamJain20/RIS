"""SL5 trust-freshness collector over the stateful synthetic world (TEST-ONLY double).

Adds TMSC trust-anchor state to the SL2 world, mirroring the pinned ledger (933d2a7, TMSC.sol):
_authorizeUpdate (unknown authority 4, issuer-scoped CA-admin caller 16, root signature 1 except
paper-minimal), MALFORMED ordering, _checkFreshness only in repaired-e (STALE_ANCHOR 5 for a version
not strictly increasing or an expired list), _advance (generation, authEpoch, LSC TRUST_UPDATE log,
TrustAnchorUpdated) and revocation per generation; PSC.requestAccess denies a revoked credential
(AccessDenied, REVOKED 19) and, in repaired-e, a stale authEpoch (STALE_STATE 6). sign_list() stands
in for ledger/tools/sign_list.sh. Not ledger evidence; live runs are.
"""
import copy
import hashlib
import importlib
import json

import pytest
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.evm import _internal, _type
from evaluation.native import NativeReceipt
from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_audit_stress_collector import AuditWorld
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_relay_stress_collector import FakeChain, Reverted, World, typed_digest
from evaluation.tests.test_trust_oracle import ROOT_KEYS, SERIAL, sign_list

ZERO = '0x'+'00'*32
UNPUBLISHED = dict(published=False, version='0', validUntil='0', generation='0', contentDigest=ZERO, blockNumber='0', prevBlockNumber='0')


def list_typed(body, dep):
    vectors = json.load(open('interfaces/v1/vectors/eip712-agent1.json'))['vectors']
    typed = copy.deepcopy(next(v['typedData'] for v in vectors if v['name'] == 'RevocationList'))
    pbc = dep['chains']['pbc']
    typed['domain'].update(chainId=pbc['chainId'], verifyingContract=pbc['contracts']['TMSC'])
    typed['message'] = body
    encoded = encode_typed_data(full_message=typed)
    return encoded, '0x'+keccak(b'\x19'+encoded.version+encoded.header+encoded.body).hex()


class TrustChain(FakeChain):
    def call(self, method, params=None):
        if method == 'eth_call':
            self.world.sender = params[0].get('from')
        return super().call(method, params)

    def read(self, role, method, *args, block=None):
        w = self.world; st = self.history[int((block or self.latest_block())['number'], 16)]
        if (role, method) == ('TMSC', 'authEpoch'): return [str(st['epoch'])]
        if method == 'revocationListState': return [copy.deepcopy(st['anchors'].get(args[0], UNPUBLISHED))]
        if method == 'isRevoked':
            a = st['anchors'].get(args[0]); return [bool(a) and (args[0], a['generation'], args[1]) in st['revoked']]
        if method == 'isCaAdmin': return [w.admins.get(args[0]) == args[1]]
        if method == 'checkCredentials': return list(w.credentials(st, args[0]))
        if method == 'denialCount': return [str(st['denials'].get(args[0], 0))]
        return super().read(role, method, *args, block=block)

    def submit(self, signer, role, method, *args, expect_success=True):
        w = self.world
        sender = w.dep['fixture']['relay']['address'] if signer == 'relay' else w.roles[signer]
        w.sender = sender
        tx = '0x'+hashlib.sha256(f'{self.name}{self.number}{method}{signer}'.encode()).hexdigest()
        saved = copy.deepcopy(w.state)
        try:
            _, events = self.execute(role, method, copy.deepcopy(list(args))); code = None
        except Reverted as error:
            w.state = saved; events = []; code = error.code
        block = self._mine([tx]); logs = []
        for i, (contract_role, name, fields) in enumerate(events):
            c = self.contracts[contract_role]; spec = next(x for x in c.abi if x.get('name') == name and x['type'] == 'event')
            topics = ['0x'+keccak(text=c._signature(spec)).hex()]; data = []
            for s in spec['inputs']:
                v = _internal(s, fields[s['name']])
                if s['indexed']: topics.append('0x'+encode([_type(s)], [v]).hex())
                else: data.append((s, v))
            logs.append(dict(address=c.address, removed=False, topics=topics, data='0x'+encode([_type(s) for s, _ in data], [v for _, v in data]).hex(),
                             blockNumber=block['number'], blockHash=block['hash'], transactionHash=tx, transactionIndex='0x0', logIndex=hex(i)))
        self.raw_logs += logs
        self.txs[tx] = dict(hash=tx, input=self.contracts[role].calldata(method, *args), to=self.contracts[role].address, blockNumber=block['number'],
                            blockHash=block['hash'], **{'from': sender})
        self.codes[tx] = code
        receipt = dict(status='0x1' if code is None else '0x0', transactionHash=tx, blockHash=block['hash'], blockNumber=block['number'],
                       transactionIndex='0x0', gasUsed='0x1234', logs=logs)
        native = NativeReceipt(receipt=receipt, transaction=dict(hash=tx, chainId=hex(int(self.chain_id)), blockHash=block['hash'],
                               blockNumber=block['number'], transactionIndex='0x0'), block=block, chain_id=self.chain_id)
        if native.success != expect_success:
            raise ValueError('Native transaction status differs from expected control')
        return native


class TrustWorld(World):
    def __init__(self, artifacts, inputs, profile, control=None):
        super().__init__(artifacts, inputs, profile, control)
        sample, _ = inputs
        self.bootstrap = copy.deepcopy(sample)
        self.auth = {a['id']: a for a in self.dep['fixture']['authorities']}
        self.admins = {a['root']: a['caAdmins'][0] for a in self.auth.values()}
        self.roles = {a['id']+'-ca-admin': a['caAdmins'][0] for a in self.auth.values()}
        self.h1 = self.auth['H1']['root']
        anchors = {}
        for it in self.bootstrap['trustLists']:
            if it['kind'] == 'RevocationList':
                body = it['list']
                anchors[body['authority']] = dict(published=True, version=body['version'], validUntil=body['validUntil'], generation='1',
                                                  contentDigest=list_typed(body, self.dep)[1], blockNumber='299', prevBlockNumber='0')
        self.state.update(anchors=anchors, revoked=set(), epoch=3, denials={})
        self.sender = None; self.signed = []; self.worker_state = None
        self.pbc = TrustChain(self, 'pbc')
        base = self.pbc.execute

        def execute(role, method, args, *, dry=False):
            if (role, method) == ('TMSC', 'updateRevocationList'):
                return self.update(*args)
            if (role, method) == ('PSC', 'requestAccess'):
                denied = self.denial(args[0])
                if denied is not None: return denied
            return base(role, method, args, dry=dry)
        self.pbc.execute = execute

    # ---- TMSC double
    def records_for(self, gid):
        records = super().records_for(gid)
        if gid == self.users['alice']['gid']:
            version = self.state['anchors'][self.h1]['version']
            for r in records:
                if r['kind'] == '1': r['anchorVersion'] = version
        return records

    def credentials(self, st, gid):
        a = st['anchors'][self.h1]
        if gid == self.users['alice']['gid'] and (self.h1, a['generation'], SERIAL) in st['revoked']:
            return '19', []
        saved = self.state; self.state = st
        try:
            return '0', self.records_for(gid)
        finally:
            self.state = saved

    def update(self, body, signature):
        st = self.state; root = body['authority']; ts = self.ts+1
        if root not in self.admins: raise Reverted('4')
        if self.admins[root] != self.sender and self.control != 'caller-unchecked': raise Reverted('16')
        encoded, digest = list_typed(body, self.dep)
        if self.profile != 'paper-minimal' and Account.recover_message(encoded, signature=signature).lower() != root: raise Reverted('1')
        serials = [int(x) for x in body['revokedSerials']]
        if any(b <= a for a, b in zip(serials, serials[1:])): raise Reverted('20')
        monotone = self.profile == 'repaired-e'
        if self.control == 'no-version-monotone': monotone = False
        if self.control == 'paper-version-check': monotone = True
        a = st['anchors'].get(root)
        if monotone and a and int(body['version']) <= int(a['version']): raise Reverted('5')
        if self.profile == 'repaired-e' and ts >= int(body['validUntil']): raise Reverted('5')
        generation = str(int(a['generation'])+1 if a else 1); prev = a['blockNumber'] if a else '0'
        for s in body['revokedSerials']: st['revoked'].add((root, generation, s))
        st['anchors'][root] = dict(published=True, version=body['version'], validUntil=body['validUntil'], generation=generation,
                                   contentDigest=digest, blockNumber=str(self.pbc.number+1), prevBlockNumber=prev)
        st['epoch'] += 1; st['logid'] += 1
        subject = '0x'+keccak(encode(['address', 'uint8'], [root, 1])).hex()
        details = '0x'+encode(['address', 'uint8', 'uint64', 'uint64', 'uint64', 'bytes32', 'address'],
                              [root, 1, int(body['version']), int(body['validUntil']), int(generation), bytes.fromhex(digest[2:]), self.sender]).hex()
        return [generation], [('LSC', 'LogRecorded', dict(logId=str(st['logid']), kind='2', subject=subject,
                                                         detailsHash='0x'+keccak(bytes.fromhex(details[2:])).hex(), details=details)),
                              ('TMSC', 'TrustAnchorUpdated', dict(authority=root, kind='1', version=body['version'], validUntil=body['validUntil'],
                                                                  generation=generation, contentDigest=digest, prevBlockNumber=prev,
                                                                  authEpoch=str(st['epoch']), submitter=self.sender))]

    def denial(self, req):
        st = self.state; _, digest = typed_digest('AccessRequest', req, self.dep)
        code = '6' if self.profile == 'repaired-e' and req['authEpoch'] != str(st['epoch']) else self.credentials(st, req['gid'])[0]
        if code == '0': return None
        st['logid'] += 1; st['denials'][digest] = st['denials'].get(digest, 0)+1
        return None, [('LSC', 'LogRecorded', dict(logId=str(st['logid']), kind='3', subject=digest, detailsHash=ZERO, details='0x')),
                      ('PSC', 'AccessDenied', dict(requestDigest=digest, claimedGid=req['gid'], code=code, requestLogId=str(st['logid'])))]

    # ---- owner signed-list producer double (ledger/tools/sign_list.sh)
    def sign_list(self, variant):
        self.signed.append(variant)
        if self.control == 'tool-fails':
            return dict(exitCode=1, output=b'error: PBC chain id differs from deployment.json\n')
        hid, revoke = ('H1', [SERIAL]) if variant == 'signed-list-rollback' else ('H2', [])
        root = self.auth[hid]['root']; a = self.state['anchors'][root]
        body = dict(authority=root, version=str(int(a['version'])+1), validUntil=str(self.ts+86400), revokedSerials=revoke)
        label = {'H1': 'H2-root', 'H2': 'H1-root'}[hid] if self.control == 'wrong-signer' else ROOT_KEYS[hid]
        signature, _ = sign_list(body, self.dep, label)
        pbc = self.dep['chains']['pbc']
        doc = dict(schemaVersion='hmbc-ledger-signed-list/v0', producer='agent-1 ledger/tools/sign_list.sh (script/SignList.s.sol)', testOnly=True,
                   binding=dict(pbcChainId=pbc['chainId'], tmsc=pbc['contracts']['TMSC'], rsc=pbc['contracts']['RSC'], blockNumber=str(self.pbc.number),
                                blockTimestamp=str(self.ts), deploymentSha256=hashlib.sha256(json.dumps(self.dep).encode()).hexdigest(),
                                profile=self.dep['profileEnum']),
                   item=dict(kind='RevocationList', call='TMSC.updateRevocationList', submitterRole=hid+'-ca-admin',
                             submitter=self.auth[hid]['caAdmins'][0], list=body, signature=signature, signer=root))
        return dict(exitCode=0, output=json.dumps(doc).encode())

    def exchange(self, envelope):
        if envelope['operation'] == 'prepare_request' and self.control == 'worker-appears':
            self.worker_state = dict(events=[], releases=[])
        return super().exchange(envelope)

    # Verified never-instantiated record, or a valid idle export once instantiated (same double as SL3).
    worker = AuditWorld.worker


def collector():
    module = importlib.import_module('evaluation.trust_stress')
    assert hasattr(module, 'execute_trust_stress'), 'trust stress collector missing'
    return module.execute_trust_stress


def run(world, tmp_path, variant):
    return collector()(world.pbc, world.dbc, world, deployment_bytes=json.dumps(world.dep).encode(), bootstrap=world.bootstrap,
                       user_label='alice', user=world.users['alice'], record=world.record, policy=world.policy, variant=variant,
                       worker_snapshot=world.worker, sign_list=world.sign_list, output=tmp_path/'stress')


PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']


@pytest.mark.parametrize('profile', PROFILES)
def test_wrong_issuer_rejected_without_state_change(artifacts, inputs, tmp_path, profile):
    w = TrustWorld(artifacts, inputs, profile)
    before = copy.deepcopy(w.state['anchors']); epoch = w.state['epoch']
    result = run(w, tmp_path, 'wrong-issuer')
    assert result['ok'] and (result['classification'], result['error']) == ('SUPPORTED', 'UNAUTHORIZED_CALLER')
    assert w.state['anchors'] == before and w.state['epoch'] == epoch and w.signed == ['wrong-issuer'] and w.calls == []
    assert [s['step'] for s in result['workerSteps']] == ['baseline', 'WRONG_ISSUER_UPDATE']
    produced = json.loads((tmp_path/'stress/signed-list.json').read_text())
    assert produced['item']['submitterRole'] == 'H2-ca-admin' and produced['testOnly'] is True
    simulation = json.loads((tmp_path/'stress/right-admin-simulation.json').read_text())
    assert simulation['generation'] == '2' and simulation['mined'] is False


@pytest.mark.parametrize('profile', PROFILES)
def test_signed_list_rollback(artifacts, inputs, tmp_path, profile):
    w = TrustWorld(artifacts, inputs, profile)
    result = run(w, tmp_path, 'signed-list-rollback')
    paper = profile != 'repaired-e'
    assert result['ok']
    assert (result['classification'], result['error'], result['outcome']) == (('SPEC_GAP', None, 'ACCEPT') if paper else ('REPAIR_SUPPORTED', 'STALE_ANCHOR', 'REJECT'))
    h1 = w.state['anchors'][w.h1]
    assert h1['version'] == ('1' if paper else '2') and w.state['epoch'] == (5 if paper else 4)
    assert w.calls == ['prepare_request'] and w.signed == ['signed-list-rollback']
    assert [s['step'] for s in result['workerSteps']] == ['baseline', 'INSTALL_NEW_LIST', 'REPLAY_OLD_LIST', 'REQUEST_ACCESS']
    request = json.loads((tmp_path/'stress/request.json').read_text())
    assert request['authEpoch'] == str(w.state['epoch'])   # A1-0064: the request carries the current authEpoch
    assert [e['name'] for e in request['events']][-1] == ('AccessForwarded' if paper else 'AccessDenied')


@pytest.mark.parametrize('profile,variant,control', [
    ('paper-strict', 'signed-list-rollback', 'tool-fails'),
    ('repaired-e', 'wrong-issuer', 'tool-fails'),
    ('paper-minimal', 'wrong-issuer', 'wrong-signer'),
    ('repaired-e', 'signed-list-rollback', 'wrong-signer'),
    ('paper-strict', 'signed-list-rollback', 'paper-version-check'),
    ('repaired-e', 'signed-list-rollback', 'no-version-monotone'),
    ('paper-minimal', 'wrong-issuer', 'caller-unchecked'),
    ('repaired-e', 'wrong-issuer', 'caller-unchecked'),
    ('paper-strict', 'signed-list-rollback', 'worker-appears'),
])
def test_false_observations_fail_visibly(artifacts, inputs, tmp_path, profile, variant, control):
    w = TrustWorld(artifacts, inputs, profile, control)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is False
    if control == 'tool-fails':
        refusal = json.loads((tmp_path/'stress/sign-list-refusal.json').read_text())
        assert set(refusal) == {'exitCode', 'outputSha256', 'firstLine', 'note'} and refusal['exitCode'] == 1


@pytest.mark.parametrize('variant', ['receipt-binding-control', 'forged-tuple', 'dropped-outcome'])
def test_unsupported_variant_refuses_before_side_effects(artifacts, inputs, tmp_path, variant):
    w = TrustWorld(artifacts, inputs, 'paper-strict')
    anchors = copy.deepcopy(w.state['anchors'])
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert w.calls == [] and w.signed == [] and w.state['anchors'] == anchors and w.pbc.txs == {}
