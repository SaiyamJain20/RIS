"""Synthetic boundary controls for the native bootstrap executor.

The test double supplies already-decoded public evidence; it cannot establish
live integration. Production receipt/ABI validation is tested separately.
"""
import copy
import importlib
from types import SimpleNamespace

import pytest

from evaluation.tests.test_bootstrap import inputs


def execute(chain, sample, deployment):
    assert importlib.util.find_spec('evaluation.bootstrap_execution') is not None, 'Native bootstrap execution is missing'
    return importlib.import_module('evaluation.bootstrap_execution').execute_bootstrap(chain, sample, deployment_bytes=deployment)


class Evidence:
    def __init__(self, success, events, number='339'):
        self.success = success; self.events = events; self.block_number = number
        self.block_hash = '0x'+'ab'*32; self.timestamp = '1791475989'
        self.receipt = {'transactionHash': '0x'+'cd'*32}

    def decoded(self, contract): return self.events


class Boundary:
    def __init__(self, sample, kwargs):
        self.sample = sample; self.versions = kwargs['versions']; self.calls = []
        self.states = {}; self.registrations = {}; self.epoch = '0'; self.clock = '1791475988'
        self.control = None; self.rpc = self
        self.contracts = {x: SimpleNamespace(address=sample['binding'][x.lower()]) for x in ('TMSC', 'RSC')}
        self.chain_id = '18545'
        for root in self.versions:
            for method in ('revocationListState', 'temporalAclState'):
                self.states[(method, root)] = dict(published=False, version='0', validUntil='0', generation='0',
                                                  contentDigest='0x'+'00'*32, blockNumber='0', prevBlockNumber='0')

    def call(self, method, params=None):
        assert method == 'eth_getBlockByNumber'
        return dict(number='0x152', timestamp=hex(int(self.clock)), hash='0x'+'ab'*32)

    def latest_block(self): return self.call('eth_getBlockByNumber')

    def read(self, role, method, *args, block=None):
        if method == 'tmsc': return [self.contracts['TMSC'].address]
        if method == 'pbcChainId': return ['18545']
        if method == 'profile': return ['2']
        if method == 'mutations': return ['0']
        if method == 'isCaAdmin':
            root, admin = args
            return [any(item['signer'] == root and item['submitter'] == admin for item in self.sample['trustLists'])]
        if method == 'authEpoch': return [self.epoch]
        if method in ('revocationListState', 'temporalAclState'): return [copy.deepcopy(self.states[(method, args[0])])]
        if method == 'isRegistered': return [args[0] in self.registrations]
        if method == 'recipientKeyHash': return [self.registrations[args[0]]]
        raise AssertionError((role, method, args))

    def rejection_code(self, evidence): return '5' if self.control == 'wrong-reason' else '16'

    def submit(self, signer, role, method, *args, expect_success=True):
        self.calls.append((signer, role, method, expect_success))
        if not expect_success:
            if self.control == 'grant-all': return Evidence(True, [])
            if self.control == 'wrong-state': self.epoch = '1'
            return Evidence(False, [])
        if self.control == 'deny-all': return Evidence(False, [])
        if role == 'TMSC':
            body, sig = args; state_method = 'revocationListState' if method == 'updateRevocationList' else 'temporalAclState'
            old = self.states[(state_method, body['authority'])]; self.epoch = str(int(self.epoch)+1)
            # Public owner sample digests independently checked in the prior pin evidence.
            digest = {'updateTemporalAcl': '0x4b41a2225959cffa13ee6b93d4c5b056a8d63ff787b330d5a5aef699b86ff137'}.get(method)
            if digest is None:
                digest = ('0x0b34f0383b32e7a52798f0d957a7dc57fe05797fd983b7fc57e9747fe8dc757a' if body['authority'] == self.sample['trustLists'][0]['signer'] else '0x7e5d8846b4720ebd2fc224479cb4838b1d8a586ba9da982bf55d78ffd1ac0946')
            state = dict(published=True, version=body['version'], validUntil=body['validUntil'], generation=str(int(old['generation'])+1),
                         contentDigest=digest, blockNumber='339', prevBlockNumber=old['blockNumber'])
            self.states[(state_method, body['authority'])] = state
            fields = {k: state[k] for k in ('version', 'validUntil', 'generation', 'contentDigest', 'prevBlockNumber')}
            fields.update(authority=body['authority'], kind='1' if method == 'updateRevocationList' else '2', authEpoch=self.epoch,
                          submitter=next(x['submitter'] for x in self.sample['trustLists'] if x['submitterRole'] == signer))
            if self.control == 'wrong-event': fields['authority'] = '0x'+'11'*20
            return Evidence(True, [{'name': 'TrustAnchorUpdated', 'fields': fields, 'logIndex': '0'}])
        reg, sig, cert = args
        self.registrations[reg['gid']] = reg['recipientKeyHash']
        fields = dict(gid=reg['gid'], issuer=cert['cert']['issuer'], certDigest=reg['certDigest'], recipientKeyHash=reg['recipientKeyHash'], logId='1')
        if self.control == 'wrong-recipient': self.registrations[reg['gid']] = '0x'+'11'*32
        return Evidence(True, [{'name': 'Registered', 'fields': fields, 'logIndex': '0'}])


def test_wrong_admin_precedes_legitimate_h2_and_both_users_register(inputs):
    sample, kwargs = inputs; chain = Boundary(sample, kwargs)
    result = execute(chain, sample, kwargs['deployment_bytes'])
    assert chain.calls == [('H1-ca-admin', 'TMSC', 'updateRevocationList', False),
                           ('H1-ca-admin', 'TMSC', 'updateRevocationList', True),
                           ('H1-ca-admin', 'TMSC', 'updateTemporalAcl', True),
                           ('H2-ca-admin', 'TMSC', 'updateRevocationList', True),
                           ('relay', 'RSC', 'register', True), ('relay', 'RSC', 'register', True)]
    assert result['wrongAdminCode'] == '16' and len(chain.registrations) == 2
    assert result['registeredUsers'] == ['alice', 'bob']


@pytest.mark.parametrize('control', ['grant-all', 'deny-all', 'wrong-reason', 'wrong-state', 'wrong-event', 'wrong-recipient'])
def test_invalid_bootstrap_provider_cannot_satisfy_controls(inputs, control):
    sample, kwargs = inputs; chain = Boundary(sample, kwargs); chain.control = control
    with pytest.raises(ValueError): execute(chain, sample, kwargs['deployment_bytes'])


def test_metadata_mismatch_prevents_any_transaction(inputs):
    sample, kwargs = inputs; chain = Boundary(sample, kwargs)
    sample['binding']['deploymentSha256'] = 'f'*64
    with pytest.raises(ValueError): execute(chain, sample, kwargs['deployment_bytes'])
    assert chain.calls == []
