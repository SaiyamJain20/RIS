"""SL2 relay-stress collector over a stateful synthetic two-chain world.

The world below is a TEST-ONLY double of the pinned ledger semantics that matter
here (A1-0062; ledger 933d2a7: ACSC.policyEnf, consumeDecision/DecisionVerifier
step order, KSSC.sol:180 grant uniqueness then :182 nonce). It is not evidence of
ledger behaviour; live runs are. Each control removes or perturbs one fact the
collector and oracle must not accept.
"""
import contextlib
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.evm import AbiContract, _decode, _internal, _type
from evaluation.native import NativeReceipt
from evaluation.tests.test_access_artifacts import artifacts, sign
from evaluation.tests.test_bootstrap import inputs
from evaluation.vectors import credential_digest

ROOT = Path(__file__).resolve().parents[2]
ZERO = '0x'+'00'*32
NOW = 1791476010
RELAY_KEY = keccak(text='hmbc-e0-synthetic-key:relay')


def typed_digest(kind, message, dep):
    vectors = json.loads((ROOT/'interfaces/v1/vectors/eip712-agent1.json').read_text())['vectors']
    typed = copy.deepcopy(next(v['typedData'] for v in vectors if v['name'] == kind))
    chain = dep['chains']['pbc' if kind in ('AccessRequest', 'GrantReceipt') else 'dbc']
    typed['domain'].update(chainId=chain['chainId'], verifyingContract=chain['contracts']['PSC' if kind in ('AccessRequest', 'GrantReceipt') else 'KSSC'])
    typed['message'] = message
    encoded = encode_typed_data(full_message=typed)
    return encoded, '0x'+keccak(b'\x19'+encoded.version+encoded.header+encoded.body).hex()


class Reverted(Exception):
    def __init__(self, code):
        super().__init__(code); self.code = code


class World:
    """Shared synthetic state of one PBC/DBC deployment pair."""

    def __init__(self, artifacts, inputs, profile, control=None):
        self.dep, _, _, offered_cp, decision, _ = artifacts; sample, _ = inputs
        self.default_cp = offered_cp['checkpoint']
        self.dep.update(profile=profile, profileEnum={'paper-strict': '0', 'paper-minimal': '1', 'repaired-e': '2'}[profile])
        self.users = sample['users']; self.alice_records = decision['credentialRecords']
        self.bob_records = [dict(self.alice_records[0], issuer=sample['trustLists'][2]['signer'],
                                 role='0x'+keccak(text='HMBC.role.Researcher').hex(), serial='201')]
        self.record = dict(dataId='0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e',
                           owner=self.dep['fixture']['authorities'][1]['root'], payloadDigest='0x'+'55'*32)
        self.policy = dict(clauses=[[dict(role='0x'+keccak(text='HMBC.role.Doctor').hex(), kind='1', issuerMode='0'),
                                     dict(role='0x'+keccak(text='HMBC.role.OnDuty').hex(), kind='2', issuerMode='2')]])
        self.profile = profile; self.control = control; self.ts = NOW
        self.state = dict(requests={}, grants={}, nonces={}, count=0, checkpoint=None, logid=0)
        self.calls = []; self.rpc_methods = []
        self.pbc = FakeChain(self, 'pbc'); self.dbc = FakeChain(self, 'dbc')

    # ---- views shared by both chains
    def records_for(self, gid):
        return copy.deepcopy(self.alice_records if gid == self.users['alice']['gid'] else self.bob_records)

    def allowed(self, records):
        roles = {r['role'] for r in records}
        return {q['role'] for q in self.policy['clauses'][0]} <= roles

    def grant_id(self, ref):
        kssc = self.dep['chains']['dbc']['contracts']['KSSC']
        return '0x'+keccak(encode(['bytes32', 'address', 'uint256'], [bytes.fromhex(ref[2:]), kssc, int(self.dep['chains']['dbc']['chainId'])])).hex()

    # ---- adapter double (TEST-ONLY user/witness keys stay here, never in the collector)
    def exchange(self, envelope):
        op, inp = envelope['operation'], envelope['input']; self.calls.append(op)
        if op == 'prepare_request':
            req = inp['request']; label = inp['signingKeyRef'].split(':')[-1]
            sig, digest = sign('AccessRequest', req, self.dep, label)
            return ok(dict(request=req, requestDigest=digest, signature=sig, signer=req['gid']))
        if op == 'collect_checkpoint':
            src = self.pbc.latest_block(); current = self.state['checkpoint']
            cp = dict(self.default_cp, sequence=str(int(current['sequence'])+1 if current else 1),
                      sourceBlockNumber=str(self.pbc.number), sourceBlockHash=src['hash'], expiresAt=str(self.ts+50))
            return ok(dict(checkpoint=cp, signatures=[sign('StateCheckpoint', cp, self.dep, 'witness-1')[0]]))
        if op == 'collect_decision':
            digest = inp['requestDigest']; req = self.state['requests'][digest]['request']; cp = self.state['checkpoint']
            if self.state['nonces'].get((req['gid'], req['nonce'])):
                return dict(schemaVersion='v1', ok=False, result=None, error=dict(code='REPLAY', message='synthetic'))
            records = self.records_for(req['gid'])
            d = dict(requestDigest=digest, result='1' if self.allowed(records) else '0', credentialDigest=credential_digest(records),
                     stateSequence=cp['sequence'], witnessSetVersion='1', sourceBlockNumber=cp['sourceBlockNumber'],
                     sourceBlockHash=cp['sourceBlockHash'], expiresAt=str(min(int(req['expiresAt']), int(cp['expiresAt']))))
            return ok(dict(decision=d, signatures=[sign('AccessDecision', d, self.dep, 'witness-1')[0]], credentialRecords=records))
        raise AssertionError(op)

    def worker(self):
        chains = self.dep['chains']
        fp = hashlib.sha256(json.dumps(dict(pbc=[chains['pbc']['chainId'], chains['pbc']['contracts']['PSC'], chains['pbc']['contracts']['RSC']],
                                            dbc=[chains['dbc']['chainId'], chains['dbc']['contracts']['KSSC'], chains['dbc']['contracts']['ACSC']]),
                                       sort_keys=True).encode()).hexdigest()
        events, releases, n = [], [], '0'
        if self.control == 'worker-moves' and len(self.calls) >= 2:
            # A well-formed release footprint, so only the idle-worker check can reject it.
            identity = dict(requestDigest='0x'+'d1'*32, grantId='0x'+'d2'*32, gid=self.users['alice']['gid'], dataId=self.record['dataId'])
            events = [dict(type=t, timestamp=str(NOW), **identity) for t in ('RELEASE_INTENT', 'RELEASE_SENT')]
            releases = [dict(**identity, ciphertextDigest='0x'+'c1'*32, recipientKeyHash=self.users['alice']['recipientKeyHash'], keyEpoch='0',
                             tokenDigest='0x290decd9548b62a8d60345a988386fc84ba6bc95484008f6362f93160ef3e563', grantExpiresAt=str(NOW+30),
                             createdAt=str(NOW), delivery='unknown', sendAttempts=1, completedAttempts=1)]
            n = '1'
        return json.dumps(dict(schemaVersion='hmbc-worker-log/v0', adapterMode='symbolic', deploymentFingerprint=fp,
                               note='synthetic worker', events=events, releases=releases,
                               counts=dict(releaseIntentCount=n, releaseSentCount=n))).encode()


def ok(result):
    return dict(schemaVersion='v1', ok=True, error=None, result=dict(schemaVersion='v1', adapterMode='symbolic', **result))


class Group:
    def __init__(self, chain, number):
        self.chain = chain; self.number = number; self.block = chain.block(number)

    def read(self, role, method, *args):
        return self.chain.read(role, method, *args, block=self.block)

    def logs(self):
        return [copy.deepcopy(log) for log in self.chain.raw_logs if int(log['blockNumber'], 16) <= self.number]


class FakeChain:
    def __init__(self, world, name):
        self.world = world; self.name = name; self.rpc = self; self.number = 300; self.history = {}
        self.chain_id = world.dep['chains'][name]['chainId']
        pins = json.loads((ROOT/'evaluation/fixtures/e1/abi/PROVENANCE.json').read_text())['files']
        self.contracts = {role: AbiContract(ROOT/'evaluation/fixtures/e1/abi'/(role+'.json'), address, pins[role]['sha256'])
                          for role, address in world.dep['chains'][name]['contracts'].items()}
        self.raw_logs = []; self.txs = {}; self.codes = {}; self.blocks = {}
        self._mine([])

    def _mine(self, txs):
        self.number += 1; self.world.ts += 1
        self.blocks[self.number] = dict(number=hex(self.number), hash='0x'+hashlib.sha256((self.name+str(self.number)).encode()).hexdigest(),
                                        timestamp=hex(self.world.ts), transactions=txs)
        self.history[self.number] = copy.deepcopy(self.world.state)
        return self.blocks[self.number]

    def block(self, number):
        return copy.deepcopy(self.blocks[number])

    def latest_block(self):
        return self.block(self.number)

    # ---- JSON-RPC surface used directly by collectors
    def call(self, method, params=None):
        self.world.rpc_methods.append((self.name, method))
        if method == 'eth_chainId': return hex(int(self.chain_id))
        if method == 'eth_getBlockByNumber':
            if params[0] == 'pending': return dict(self.latest_block(), timestamp=hex(self.world.ts+1))
            if params[0] == 'latest': return self.latest_block()
            n = int(params[0], 16); return self.block(n) if n in self.blocks else None
        if method == 'eth_getTransactionByHash': return copy.deepcopy(self.txs.get(params[0]))
        if method == 'eth_call':
            tx, number = params; n = int(number, 16)
            contract = next(c for c in self.contracts.values() if c.address == tx['to'])
            role = next(r for r, c in self.contracts.items() if c is contract)
            spec = next(f for f in contract.abi if f['type'] == 'function' and '0x'+keccak(text=contract._signature(f))[:4].hex() == tx['data'][:10])
            args = _decode(spec['inputs'], bytes.fromhex(tx['data'][10:]))
            if spec['stateMutability'] in ('view', 'pure'):
                return self.observe(role, spec['name'], *args, block=self.block(n))['returnData']
            if self.world.control == 'simulation-reverts': raise RuntimeError('RPC CLI failed with exit 1; synthetic revert')
            saved = copy.deepcopy(self.world.state)
            try:
                values, _ = self.execute(role, spec['name'], args, dry=True)
            except Reverted as error:
                raise RuntimeError('RPC CLI failed with exit 1; reverted '+str(error.code))
            finally:
                self.world.state = saved
            return '0x'+encode([_type(s) for s in spec['outputs']], [_internal(s, v) for s, v in zip(spec['outputs'], values)]).hex()
        raise AssertionError(method)

    @contextlib.contextmanager
    def read_group(self, roles, block=None):
        number = self.number if block is None else int(block)
        yield Group(self, number)

    def observe(self, role, method, *args, block=None):
        c = self.contracts[role]; block = block or self.latest_block(); specs = c._function(method)['outputs']
        values = self.read(role, method, *args, block=block)
        return dict(chainId=self.chain_id, address=c.address, blockHash=block['hash'], blockNumber=str(int(block['number'], 16)),
                    calldata=c.calldata(method, *args),
                    returnData='0x'+encode([_type(s) for s in specs], [_internal(s, v) for s, v in zip(specs, values, strict=True)]).hex())

    def read(self, role, method, *args, block=None):
        w = self.world; dep = w.dep
        st = self.history[int((block or self.latest_block())['number'], 16)]
        if method == 'profile': return [dep['profileEnum']]
        if method == 'mutations': return ['0']
        if method == 'policyVersion': return ['1']
        if method == 'authEpoch': return ['3']
        if method in ('relay', 'pscRelay'): return [dep['fixture']['relay']['address']]
        if method == 'witnesses': return [dep['fixture']['witnessSet']['witnesses']]
        if method in ('witnessSetVersion', 'threshold'): return ['1']
        if method == 'isRegistered': return [True]
        if method == 'recipientKeyHash': return [next(u['recipientKeyHash'] for u in w.users.values() if u['gid'] == args[0])]
        if method == 'dataEntry': return [dict(exists=True, owner=w.record['owner'], policyId='1')]
        if method == 'policy': return [w.policy['clauses']]
        if method == 'getRequest':
            r = st['requests'].get(args[0]); return [copy.deepcopy(r['state']) if r else dict(status='0')]
        if method == 'checkCredentials': return ['0', w.records_for(args[0])]
        if method == 'evaluate': return [w.allowed(args[1])]
        if method == 'currentCheckpoint':
            cp = st['checkpoint']; return [cp is not None, copy.deepcopy(cp or dict(w.default_cp, sequence='0'))]
        if method == 'nonceConsumed': return [bool(st['nonces'].get((args[0], args[1])))]
        if method == 'grantDetails':
            g = st['grants'].get(args[0])
            return [copy.deepcopy(g) if g else dict(exists=False, allowed=False, requestDigest=ZERO, dataId=ZERO, gid='0x'+'00'*20,
                                                    keyEpoch='0', expiresAt='0', recipientKeyHash=ZERO, issuedAt='0')]
        if method == 'accessLogCount': return [str(st['count'])]
        raise AssertionError((role, method))

    # ---- transactions
    def execute(self, role, method, args, *, dry=False):
        w = self.world; st = w.state; dep = w.dep; ts = w.ts+1; repaired = w.profile == 'repaired-e'
        relay = dep['fixture']['relay']['address']
        if (role, method) == ('PSC', 'requestAccess'):
            req, sig, bundle = args
            _, digest = typed_digest('AccessRequest', req, dep)
            if digest in st['requests']: raise Reverted('8')
            if not ts < int(req['expiresAt']) <= ts+30: raise Reverted('7')
            records = w.records_for(req['gid']); st['logid'] += 1
            state = dict(status='1', gid=req['gid'], dataId=req['dataId'], destinationChainId=req['destinationChainId'], kssc=req['kssc'],
                         credentialDigest=credential_digest(records), decidedAt=str(ts), expiresAt=req['expiresAt'],
                         requestLogId=str(st['logid']), outcomeLogId='0')
            st['requests'][digest] = dict(request=copy.deepcopy(req), state=state)
            return None, [('LSC', 'LogRecorded', dict(logId=str(st['logid']), kind='3', subject=digest, detailsHash=ZERO, details='0x')),
                          ('PSC', 'AccessForwarded', dict(requestDigest=digest, gid=req['gid'], dataId=req['dataId'],
                           destinationChainId=req['destinationChainId'], kssc=req['kssc'], credentialDigest=credential_digest(records),
                           verifiedAttributes=records, expiresAt=req['expiresAt'], requestLogId=str(st['logid'])))]
        if (role, method) == ('KSSC', 'acceptState'):
            st['checkpoint'] = copy.deepcopy(args[0]); cp = st['checkpoint']
            return None, [('KSSC', 'StateAccepted', {k: cp[k] for k in ('sequence', 'authEpoch', 'policyVersion', 'keyEpoch',
                                                                    'witnessSetVersion', 'sourceBlockNumber', 'sourceBlockHash', 'expiresAt')})]
        if (role, method) == ('ACSC', 'policyEnf'):
            if repaired: raise Reverted('21')
            fwd, records = args; allowed = w.allowed(records) and w.control != 'paper-deny'
            gid_ = ZERO; events = []
            if allowed:
                gid_ = w.grant_id(fwd['pbcRequestId'])
                if gid_ in st['grants']: raise Reverted('8')
                st['grants'][gid_] = dict(exists=True, allowed=True, requestDigest=fwd['pbcRequestId'], dataId=fwd['dataId'], gid=fwd['gid'],
                                          keyEpoch='0', expiresAt=str(ts+30), recipientKeyHash=ZERO, issuedAt=str(ts))
                events.append(('KSSC', 'GrantIssued', dict(grantId=gid_, requestDigest=fwd['pbcRequestId'], gid=fwd['gid'], dataId=fwd['dataId'],
                                                          keyEpoch='0', expiresAt=str(ts+30), recipientKeyHash=ZERO, nonceConsumed=False, nonce='0')))
            st['count'] += 1
            events.append(('ACSC', 'AccessLog', dict(accessLogId=str(st['count']), requestRef=fwd['pbcRequestId'], gid=fwd['gid'], dataId=fwd['dataId'],
                                                    allowed=allowed, code='0' if allowed else '9', credentialDigest=credential_digest(records),
                                                    grantId=gid_, submitter=relay)))
            return [allowed, gid_], events
        if (role, method) == ('ACSC', 'consumeDecision'):
            if not repaired: raise Reverted('21')
            req, cert, records = args; _, digest = typed_digest('AccessRequest', req, dep); d = cert['decision']
            if d['requestDigest'] != digest: raise Reverted('2')
            encoded, _ = typed_digest('AccessDecision', d, dep)
            signer = Account.recover_message(encoded, signature=cert['signatures'][0]).lower()
            if signer not in dep['fixture']['witnessSet']['witnesses'] and w.control != 'grant-all': raise Reverted('1')
            if credential_digest(records) != d['credentialDigest']: raise Reverted('2')
            if ts >= int(d['expiresAt']) or ts >= int(req['expiresAt']) or w.control == 'expired-second' and st['grants']: raise Reverted('7')
            cp = st['checkpoint']
            if cp is None or d['stateSequence'] != cp['sequence']: raise Reverted('6')
            gid_ = w.grant_id(digest)
            if gid_ in st['grants']: raise Reverted('10' if w.control == 'replay-other-code' else '8')
            if st['nonces'].get((req['gid'], req['nonce'])) and w.control != 'no-nonce': raise Reverted('8')
            st['nonces'][(req['gid'], req['nonce'])] = True
            expiry = str(min(int(d['expiresAt']), int(req['expiresAt'])))
            st['grants'][gid_] = dict(exists=True, allowed=True, requestDigest=digest, dataId=req['dataId'], gid=req['gid'], keyEpoch='0',
                                      expiresAt=expiry, recipientKeyHash=req['recipientKeyHash'], issuedAt=str(ts))
            st['count'] += 1
            return [gid_], [('KSSC', 'GrantIssued', dict(grantId=gid_, requestDigest=digest, gid=req['gid'], dataId=req['dataId'], keyEpoch='0',
                                                        expiresAt=expiry, recipientKeyHash=req['recipientKeyHash'], nonceConsumed=True, nonce=req['nonce'])),
                            ('ACSC', 'AccessLog', dict(accessLogId=str(st['count']), requestRef=digest, gid=req['gid'], dataId=req['dataId'],
                                                      allowed=True, code='0', credentialDigest=d['credentialDigest'], grantId=gid_, submitter=relay))]
        raise AssertionError((role, method))

    def submit(self, signer, role, method, *args, expect_success=True):
        assert signer == 'relay'
        relay = self.world.dep['fixture']['relay']['address']; tx = '0x'+hashlib.sha256(f'{self.name}{self.number}{method}'.encode()).hexdigest()
        saved = copy.deepcopy(self.world.state)
        try:
            _, events = self.execute(role, method, copy.deepcopy(list(args))); code = None
        except Reverted as error:
            self.world.state = saved; events = []; code = error.code
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
                            blockHash=block['hash'], **{'from': relay})
        self.codes[tx] = code
        receipt = dict(status='0x1' if code is None else '0x0', transactionHash=tx, blockHash=block['hash'], blockNumber=block['number'],
                       transactionIndex='0x0', gasUsed='0x1234', logs=logs)
        native = NativeReceipt(receipt=receipt, transaction=dict(hash=tx, chainId=hex(int(self.chain_id)), blockHash=block['hash'],
                               blockNumber=block['number'], transactionIndex='0x0'), block=block, chain_id=self.chain_id)
        if native.success != expect_success:
            raise ValueError('Native transaction status differs from expected control')
        return native

    def rejection_code(self, native):
        code = self.codes[native.receipt['transactionHash']]
        if native.success or code is None: raise ValueError('Owned mined rejection receipt required')
        return code


def collector():
    module = importlib.import_module('evaluation.relay_stress')
    assert hasattr(module, 'execute_relay_stress'), 'relay stress collector missing'
    return module.execute_relay_stress


def run(world, tmp_path, variant):
    return collector()(world.pbc, world.dbc, world, deployment_bytes=json.dumps(world.dep).encode(), user_label='alice',
                       user=world.users['alice'], record=world.record, policy=world.policy, variant=variant,
                       worker_snapshot=world.worker, output=tmp_path/'stress')


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
def test_paper_forged_tuple_grants_without_any_pbc_request(artifacts, inputs, tmp_path, profile):
    w = World(artifacts, inputs, profile)
    result = run(w, tmp_path, 'forged-tuple')
    assert result['ok'] and result['classification'] == 'SPEC_GAP' and result['grantWithoutPbcLog'] is True
    assert w.calls == [] and w.state['requests'] == {} and len(w.state['grants']) == 1
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is True


def test_repaired_forged_tuple_simulates_honest_then_mines_non_witness_signature(artifacts, inputs, tmp_path):
    w = World(artifacts, inputs, 'repaired-e')
    result = run(w, tmp_path, 'forged-tuple')
    assert result['ok'] and result['classification'] == 'REPAIR_SUPPORTED' and result['error'] == 'BAD_SIGNATURE'
    assert w.calls == ['prepare_request', 'collect_checkpoint', 'collect_decision']
    assert ('dbc', 'eth_call') in w.rpc_methods and w.state['grants'] == {} and w.state['nonces'] == {}
    forged = json.loads((tmp_path/'stress/forged-certificate.json').read_text())
    assert forged['recoveredSigner'] == w.dep['fixture']['relay']['address'] and forged['honestSimulationGrantId'] != ZERO
    # A1-0064: the relay signs exactly the digest the honest witness signature recovers under (runner's own domain).
    assert forged['honestDigest'] == forged['forgedDigest'] and forged['signedDigestEqual'] is True
    assert forged['honestSigner'] == w.dep['fixture']['witnessSet']['witnesses'][0]
    timeline = result['timeline']
    assert int(timeline['stressTimestamp']) < int(timeline['requestExpiresAt']) and timeline['marginSeconds'] > 0


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_new_reference_replay(artifacts, inputs, tmp_path, profile):
    w = World(artifacts, inputs, profile)
    result = run(w, tmp_path, 'new-reference-replay')
    assert result['ok']
    if profile == 'repaired-e':
        assert result['error'] == 'REPLAY' and len(w.state['grants']) == 1
        assert int(result['timeline']['stressTimestamp']) < int(result['timeline']['requestExpiresAt'])
    else:
        assert result['classification'] == 'SPEC_GAP' and len(w.state['grants']) == 2 and len(w.state['requests']) == 1


def test_same_nonce_distinct_digests_reaches_nonce_guard(artifacts, inputs, tmp_path):
    w = World(artifacts, inputs, 'repaired-e')
    result = run(w, tmp_path, 'same-nonce-distinct-digests')
    assert result['ok'] and result['error'] == 'REPLAY' and result['nonceGuardReached'] is True
    assert w.calls == ['prepare_request', 'prepare_request', 'collect_checkpoint', 'collect_decision', 'collect_decision']
    assert len(w.state['requests']) == 2 and len(w.state['grants']) == 1
    timeline = json.loads((tmp_path/'stress/timeline.json').read_text())
    assert timeline == result['timeline']
    # A1-0064: every timestamp recorded against both 30 s request lifetimes, in causal order.
    order = ['firstRequestTimestamp', 'secondRequestTimestamp', 'checkpointTimestamp', 'firstConsumeTimestamp', 'secondConsumeTimestamp']
    assert [int(timeline[k]) for k in order] == sorted(int(timeline[k]) for k in order)
    assert int(timeline['secondConsumeTimestamp']) < min(int(timeline['firstExpiresAt']), int(timeline['secondExpiresAt']))
    assert timeline['marginSeconds'] == min(int(timeline['firstExpiresAt']), int(timeline['secondExpiresAt']))-int(timeline['secondConsumeTimestamp'])
    assert len(timeline['decisionCollectedAtDbcBlocks']) == 2
    pinned = json.loads((tmp_path/'stress/before-second-blocks.json').read_text())
    assert int(pinned['dbc']['number'], 16) == int(json.loads((tmp_path/'stress/after-second-blocks.json').read_text())['dbc']['number'], 16)-1


@pytest.mark.parametrize('profile,variant,control', [
    ('paper-strict', 'forged-tuple', 'paper-deny'),
    ('repaired-e', 'forged-tuple', 'grant-all'),
    ('repaired-e', 'forged-tuple', 'simulation-reverts'),
    ('repaired-e', 'forged-tuple', 'worker-moves'),
    ('paper-minimal', 'new-reference-replay', 'paper-deny'),
    ('repaired-e', 'new-reference-replay', 'replay-other-code'),
    ('repaired-e', 'same-nonce-distinct-digests', 'no-nonce'),
    ('repaired-e', 'same-nonce-distinct-digests', 'expired-second'),
])
def test_false_or_masked_observations_fail_visibly(artifacts, inputs, tmp_path, profile, variant, control):
    w = World(artifacts, inputs, profile, control)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is False


@pytest.mark.parametrize('profile,variant', [('paper-strict', 'same-nonce-distinct-digests'), ('repaired-e', 'subject'),
                                             ('paper-minimal', 'identical-replay')])
def test_unsupported_selection_refuses_before_side_effects(artifacts, inputs, tmp_path, profile, variant):
    w = World(artifacts, inputs, profile)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant)
    assert w.calls == [] and w.state['requests'] == {} and w.state['grants'] == {}
