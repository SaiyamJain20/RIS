"""SL4 receipt-control collector over the stateful synthetic world (TEST-ONLY double).

Adds the honest witness attest_grant, PSC.reportAttestedOutcome with the pinned check order
(binding before destination/epoch/expiry/quorum; MUT_NO_RECEIPT_BINDING as a control), and a
deviate() double standing in for `python -m testtools.deviating_witness` (one JSON line on
success, non-zero exit on refusal). Not ledger/protocol evidence; live runs are.
"""
import importlib
import json

import pytest
from eth_abi import encode
from eth_account import Account
from eth_utils import keccak

from evaluation.evm import _internal, _type
from evaluation.tests.test_access_artifacts import artifacts, sign
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_audit_stress_collector import AuditWorld
from evaluation.tests.test_relay_stress_collector import Reverted, ok, typed_digest
from evaluation.tests.test_receipt_oracle import altered, receipt_spec

ZERO = '0x'+'00'*32


class ReceiptWorld(AuditWorld):
    def __init__(self, artifacts, inputs, control=None):
        super().__init__(artifacts, inputs, 'repaired-e', control)
        base = self.pbc.execute

        def execute(role, method, args, *, dry=False):
            if (role, method) == ('PSC', 'reportAttestedOutcome'):
                return self.report_attested(*args)
            return base(role, method, args, dry=dry)
        self.pbc.execute = execute
        self.deviations = []

    def honest_receipt(self, grant_id, block=None):
        g = self.state['grants'][grant_id]; dbc = self.dep['chains']['dbc']
        number = self.dbc.number if block is None else int(block)
        return dict(requestDigest=g['requestDigest'], grantId=grant_id, gid=g['gid'], dataId=g['dataId'], keyEpoch=g['keyEpoch'],
                    grantExpiresAt=g['expiresAt'], witnessSetVersion='1', dbcChainId=dbc['chainId'], kssc=dbc['contracts']['KSSC'],
                    dbcBlockNumber=str(number), dbcBlockHash=self.dbc.blocks[number]['hash'])

    def exchange(self, envelope):
        op, inp = envelope['operation'], envelope['input']
        if op == 'attest_grant' and inp['grantId'] in self.state['grants']:
            self.calls.append(op); receipt = self.honest_receipt(inp['grantId'])
            if self.control == 'worker-appears': self.worker_state = dict(events=[], releases=[])   # would break the D49 precondition
            return ok(dict(receipt=receipt, signatures=[sign('GrantReceipt', receipt, self.dep, 'witness-1')[0]]))
        return super().exchange(envelope)

    def deviate(self, grant_id, field, at_block):
        """Double of the TEST-ONLY tool: exit code and its single JSON line."""
        self.deviations.append((grant_id, field, at_block))
        if self.control == 'tool-refuses':
            return dict(exitCode=1, output=b'refusing: no allowed grant with this id exists on the DBC at that block\n')
        receipt = self.honest_receipt(grant_id, at_block); original = receipt[field]
        receipt[field] = altered(field, original)
        if self.control == 'tool-two-fields':
            other = 'dataId' if field != 'dataId' else 'gid'; receipt[other] = altered(other, receipt[other])
        label = 'relay' if self.control == 'tool-wrong-signer' else 'witness-1'
        artifact = dict(schemaVersion='hmbc-test-deviating-witness/v0', testOnly=True,
                        deviation=dict(field=field, original=original, altered=receipt[field]), receipt=receipt,
                        signatures=[sign('GrantReceipt', receipt, self.dep, label)[0]])
        return dict(exitCode=0, output=(json.dumps(artifact)+'\n').encode())

    def report_attested(self, digest, outcome, receipt, sigs):
        st = self.state; rec = st['requests'].get(digest); relay = self.dep['fixture']['relay']['address']
        if rec is None: raise Reverted('2')
        if rec['state']['status'] == '2': raise Reverted('8')
        r = rec['request']
        if self.control != 'no-receipt-binding' and (receipt['requestDigest'] != digest or receipt['gid'] != r['gid'] or receipt['dataId'] != r['dataId']):
            raise Reverted('2')
        dbc = self.dep['chains']['dbc']
        if receipt['dbcChainId'] != dbc['chainId'] or receipt['kssc'] != dbc['contracts']['KSSC'] or receipt['grantId'] != self.grant_id(digest):
            raise Reverted('3')
        if receipt['keyEpoch'] != '0': raise Reverted('12')
        if receipt['grantExpiresAt'] == '0' or int(receipt['grantExpiresAt']) > int(r['expiresAt']): raise Reverted('20')
        if receipt['witnessSetVersion'] != '1': raise Reverted('6')
        if not sigs: raise Reverted('10')                       # QuorumLib: counted 0 < threshold 1
        encoded, _ = typed_digest('GrantReceipt', receipt, self.dep)
        if Account.recover_message(encoded, signature=sigs[0]).lower() not in self.dep['fixture']['witnessSet']['witnesses']:
            raise Reverted('1')                                 # SigLib.sol:47
        st['logid'] += 1; logid = str(st['logid']); spec = receipt_spec()
        details = '0x'+encode(['bytes32', 'bytes32', _type(spec), 'address'],
                              [bytes.fromhex(digest[2:]), bytes.fromhex(outcome[2:]), _internal(spec, receipt), relay]).hex()
        rec['state'].update(status='2', outcomeLogId=logid)
        return [logid], [('LSC', 'LogRecorded', dict(logId=logid, kind='4', subject=digest,
                                                    detailsHash='0x'+keccak(bytes.fromhex(details[2:])).hex(), details=details)),
                         ('PSC', 'AttestedOutcomeRecorded', dict(requestDigest=digest, grantId=receipt['grantId'], outcomeDigest=outcome,
                                                                  dbcBlockNumber=receipt['dbcBlockNumber'], logId=logid))]


def collector():
    module = importlib.import_module('evaluation.receipt_stress')
    assert hasattr(module, 'execute_receipt_stress'), 'receipt stress collector missing'
    return module.execute_receipt_stress


def run(world, tmp_path, variant, field):
    return collector()(world.pbc, world.dbc, world, deployment_bytes=json.dumps(world.dep).encode(), user_label='alice',
                       user=world.users['alice'], record=world.record, policy=world.policy, variant=variant, field=field,
                       worker_snapshot=world.worker, deviate=world.deviate, output=tmp_path/'stress')


ROWS = [('receipt-binding-control', f) for f in ('requestDigest', 'gid', 'dataId')]+[('receipt-signature-control', f) for f in ('requestDigest', 'gid', 'dataId')]+[('receipt-binding-positive', None)]


@pytest.mark.parametrize('variant,field', ROWS)
def test_receipt_rows(artifacts, inputs, tmp_path, variant, field):
    w = ReceiptWorld(artifacts, inputs)
    result = run(w, tmp_path, variant, field)
    status = next(iter(w.state['requests'].values()))['state']['status']
    assert result['ok'] and result['delivery'] == 'unknown'
    assert 'release' not in w.calls and 'encrypt_record' not in w.calls and w.calls.count('attest_grant') == 1
    assert len(w.deviations) == (1 if variant == 'receipt-binding-control' else 0)
    assert status == ('2' if variant == 'receipt-binding-positive' else '1')
    for name in ('before', 'after'):
        assert json.loads((tmp_path/'stress'/(name+'.json')).read_text())['worker']['instantiated'] is False
    # Worker-DB precondition re-checked after every catalog step (A1 SL4 instruction), not only before/after.
    step = {'receipt-binding-control': ['RESIGN_RECEIPT_FIELD'], 'receipt-signature-control': ['ALTER_RECEIPT_KEEP_SIGNATURE'],
            'receipt-binding-positive': []}[variant]
    assert [s['step'] for s in result['workerSteps']] == ['baseline', 'REQUEST_ACCESS', 'FORWARD_OR_CONSUME', 'ATTEST_GRANT']+step+['REPORT_OUTCOME']
    assert {s['worker'] for s in result['workerSteps']} == {'never-instantiated (verified)'}
    if variant == 'receipt-binding-control':
        artifact = json.loads((tmp_path/'stress/deviation.json').read_text())
        assert artifact['testOnly'] is True and artifact['deviation']['field'] == field and artifact['label'].startswith('A40')
        assert w.deviations[0][2] == json.loads((tmp_path/'stress/honest-receipt.json').read_text())['receipt']['dbcBlockNumber']


@pytest.mark.parametrize('variant,field,control', [
    ('receipt-binding-control', 'gid', 'tool-refuses'),
    ('receipt-binding-control', 'dataId', 'tool-two-fields'),
    ('receipt-binding-control', 'requestDigest', 'tool-wrong-signer'),
    ('receipt-binding-control', 'gid', 'no-receipt-binding'),
    ('receipt-signature-control', 'dataId', 'no-receipt-binding'),
    ('receipt-binding-positive', None, 'worker-appears'),
    ('receipt-signature-control', 'gid', 'worker-appears'),
])
def test_unverified_artifacts_or_mutant_behaviour_fail_visibly(artifacts, inputs, tmp_path, variant, field, control):
    w = ReceiptWorld(artifacts, inputs, control)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant, field)
    assert json.loads((tmp_path/'stress/result.json').read_text())['ok'] is False


@pytest.mark.parametrize('variant,field', [('receipt-binding-control', None), ('receipt-binding-positive', 'gid'), ('receipt-binding-control', 'grantId'),
                                           ('dropped-outcome', None)])
def test_unsupported_selection_refuses_before_side_effects(artifacts, inputs, tmp_path, variant, field):
    w = ReceiptWorld(artifacts, inputs)
    with pytest.raises(ValueError):
        run(w, tmp_path, variant, field)
    assert w.calls == [] and w.state['requests'] == {} and w.deviations == []
