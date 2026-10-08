"""Independent artifact controls: dropping each join permits a false authorization.

All signing keys below are TEST-ONLY test producers. Production recovers public
signatures only. Supplied state is synthetic, never integrated gate evidence.
"""
import copy
import importlib
import json
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.tests.test_bootstrap import inputs

ROOT = Path(__file__).resolve().parents[2]


def module():
    assert importlib.util.find_spec('evaluation.access_artifacts') is not None, 'Public access artifact verifier is missing'
    return importlib.import_module('evaluation.access_artifacts')


def sign(kind, message, deployment, label):
    vectors = json.loads((ROOT/'interfaces/v1/vectors/eip712-agent1.json').read_text())['vectors']
    typed = copy.deepcopy(next(v['typedData'] for v in vectors if v['name'] == kind))
    chain = deployment['chains']['pbc' if kind in ('AccessRequest', 'GrantReceipt') else 'dbc']
    typed['domain'].update(chainId=chain['chainId'], verifyingContract=chain['contracts']['PSC' if kind in ('AccessRequest', 'GrantReceipt') else 'KSSC'])
    typed['message'] = message
    signed = Account.sign_message(encode_typed_data(full_message=typed), keccak(text='hmbc-e0-synthetic-key:'+label))
    return '0x'+signed.signature.hex(), '0x'+signed.message_hash.hex()


@pytest.fixture
def artifacts(inputs):
    sample, kwargs = inputs; dep = json.loads(kwargs['deployment_bytes'])
    request = dict(sourceChainId=dep['chains']['pbc']['chainId'], destinationChainId=dep['chains']['dbc']['chainId'],
                   psc=dep['chains']['pbc']['contracts']['PSC'], kssc=dep['chains']['dbc']['contracts']['KSSC'],
                   gid=sample['users']['alice']['gid'], dataId='0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e',
                   action='1', policyVersion='1', authEpoch='3', keyEpoch='0', nonce='1', expiresAt='1791476040',
                   recipientKeyHash=sample['users']['alice']['recipientKeyHash'])
    signature, digest = sign('AccessRequest', request, dep, 'alice')
    prepared = dict(schemaVersion='v1', adapterMode='symbolic', request=request, requestDigest=digest, signature=signature, signer=request['gid'])
    cp = dict(sequence='1', authEpoch='3', policyVersion='1', keyEpoch='0', witnessSetVersion='1',
              sourceChainId=request['sourceChainId'], psc=request['psc'], sourceBlockNumber='350',
              sourceBlockHash='0x'+'ab'*32, expiresAt='1791476070')
    cpsig, _ = sign('StateCheckpoint', cp, dep, 'witness-1')
    checkpoint = dict(schemaVersion='v1', adapterMode='symbolic', checkpoint=cp, signatures=[cpsig])
    records = [dict(issuer=sample['trustLists'][0]['signer'], role='0x'+keccak(text='HMBC.role.Doctor').hex(),
                    kind='1', serial='101', anchorVersion='1', validUntil='2100000000'),
               dict(issuer=sample['trustLists'][0]['signer'], role='0x'+keccak(text='HMBC.role.OnDuty').hex(),
                    kind='2', serial='0', anchorVersion='1', validUntil='1791504788')]
    # Digest literal independently recomputed from these records at setup below with
    # the existing cross-language verifier, not the new component under test.
    from evaluation.vectors import credential_digest
    decision = dict(requestDigest=digest, result='1', credentialDigest=credential_digest(records), stateSequence='1',
                    witnessSetVersion='1', sourceBlockNumber='350', sourceBlockHash=cp['sourceBlockHash'], expiresAt=request['expiresAt'])
    dsig, _ = sign('AccessDecision', decision, dep, 'witness-1')
    result = dict(schemaVersion='v1', adapterMode='symbolic', decision=decision, signatures=[dsig], credentialRecords=records)
    facts = dict(source_block=dict(number=hex(350), hash=cp['sourceBlockHash'], timestamp=hex(1791476010)),
                 auth_epoch='3', policy_version='1', dbc_now='1791476010', pbc_now='1791476010',
                 current_checkpoint=[False, dict(cp, sequence='0')], request_block_number='349',
                 native_records=records, credentials_code='0', policy_allowed=True, nonce_consumed=False)
    return dep, request, prepared, checkpoint, result, facts


def test_request_signature_digest_and_exact_body_bind(artifacts):
    dep, req, prepared, *_ = artifacts
    assert module().verify_prepared(prepared, request=req, deployment=dep) == prepared['requestDigest']


@pytest.mark.parametrize('change', ['body', 'digest', 'signer', 'domain', 'extra'])
def test_prepare_cannot_substitute_request_or_domain(artifacts, change):
    dep, req, prepared, *_ = artifacts
    if change == 'body': prepared['request'] = dict(req, nonce='2')
    if change == 'digest': prepared['requestDigest'] = '0x'+'11'*32
    if change == 'signer': prepared['signer'] = '0x'+'11'*20
    if change == 'domain': dep['chains']['pbc']['contracts']['PSC'] = '0x'+'11'*20
    if change == 'extra': prepared['key'] = 'forbidden'
    with pytest.raises(ValueError): module().verify_prepared(prepared, request=req, deployment=dep)


def checkpoint_facts(facts):
    return {k: facts[k] for k in ('source_block', 'auth_epoch', 'policy_version', 'dbc_now', 'current_checkpoint', 'request_block_number')}


def test_checkpoint_requires_native_source_and_current_sequence(artifacts):
    dep, _, _, cp, _, facts = artifacts
    assert module().verify_checkpoint(cp, deployment=dep, **checkpoint_facts(facts)) == cp['checkpoint']


@pytest.mark.parametrize('change', ['hash', 'number', 'epoch', 'policy', 'sequence', 'predates', 'expired', 'ttl', 'signature', 'source', 'profile'])
def test_checkpoint_native_join_mutations_refuse(artifacts, change):
    dep, _, _, cp, _, facts = artifacts
    if change == 'hash': facts['source_block']['hash'] = '0x'+'11'*32
    if change == 'number': facts['source_block']['number'] = hex(351)
    if change == 'epoch': facts['auth_epoch'] = '4'
    if change == 'policy': facts['policy_version'] = '2'
    if change == 'sequence': facts['current_checkpoint'] = [True, cp['checkpoint']]
    if change == 'predates': facts['request_block_number'] = '351'
    if change == 'expired': facts['dbc_now'] = cp['checkpoint']['expiresAt']
    if change == 'ttl': cp['checkpoint']['expiresAt'] = '1791476071'
    if change == 'signature': cp['signatures'] = [artifacts[2]['signature']]
    if change == 'source': cp['checkpoint']['psc'] = '0x'+'11'*20
    if change == 'profile': dep['profile'] = 'paper-strict'
    with pytest.raises(ValueError): module().verify_checkpoint(cp, deployment=dep, **checkpoint_facts(facts))


def decision_facts(facts, cp):
    return {**{k: facts[k] for k in ('source_block', 'dbc_now', 'pbc_now', 'request_block_number', 'native_records',
                                   'credentials_code', 'policy_allowed', 'nonce_consumed')}, 'checkpoint': cp['checkpoint']}


def test_allow_and_policy_deny_are_independently_checked(artifacts):
    dep, req, prepared, cp, result, facts = artifacts
    verified = module().verify_decision(result, request=req, request_digest=prepared['requestDigest'], deployment=dep, **decision_facts(facts, cp))
    assert verified['decision']['result'] == '1'
    result['decision']['result'] = '0'; facts['policy_allowed'] = False
    result['signatures'] = [sign('AccessDecision', result['decision'], dep, 'witness-1')[0]]
    assert module().verify_decision(result, request=req, request_digest=prepared['requestDigest'], deployment=dep, **decision_facts(facts, cp))['decision']['result'] == '0'


@pytest.mark.parametrize('change', ['request', 'credential', 'native-records', 'grant-all', 'deny-all', 'sequence', 'source',
                                    'signature', 'nonce', 'expired', 'pbc-expired', 'predates', 'epoch', 'record-expired', 'ttl'])
def test_decision_cannot_pass_forged_or_vacuous_facts(artifacts, change):
    dep, req, prepared, cp, result, facts = artifacts
    if change == 'request': result['decision']['requestDigest'] = '0x'+'11'*32
    if change == 'credential': result['decision']['credentialDigest'] = '0x'+'11'*32
    if change == 'native-records': facts['native_records'] = []
    if change == 'grant-all': facts['policy_allowed'] = False
    if change == 'deny-all': result['decision']['result'] = '0'
    if change == 'sequence': result['decision']['stateSequence'] = '2'
    if change == 'source': facts['source_block']['hash'] = '0x'+'11'*32
    if change == 'signature': result['signatures'] = [prepared['signature']]
    if change == 'nonce': facts['nonce_consumed'] = True
    if change == 'expired': facts['dbc_now'] = req['expiresAt']
    if change == 'pbc-expired': facts['pbc_now'] = req['expiresAt']
    if change == 'predates': facts['request_block_number'] = '351'
    if change == 'epoch': req['authEpoch'] = '2'
    if change == 'record-expired': facts['dbc_now'] = result['credentialRecords'][1]['validUntil']
    if change == 'ttl': result['decision']['expiresAt'] = '1791476041'
    with pytest.raises(ValueError): module().verify_decision(result, request=req, request_digest=prepared['requestDigest'], deployment=dep, **decision_facts(facts, cp))
