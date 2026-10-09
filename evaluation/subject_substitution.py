"""Public subject stress collector for the HMBC reconstruction (E01, D35/A38).

The caller verifies historical credentials/policy/checkpoint and owns stable
public executors, fresh deployment/state, controls and full execution-plan ACKs.
The pre-release stage changes only gid and stops before release. The paper
completion stage (SL1) then releases the substituted grant through the
production adapter and completes the SAME response with the substituted and the
original subject's key references. No outcome is ever reported for the original
request. Neither stage establishes an original-paper vulnerability.
"""
import copy
import json
from pathlib import Path

from eth_utils import keccak

from evaluation.access_artifacts import require, verify_prepared, _witness
from evaluation.access_execution import _clock, _fingerprint
from evaluation.bootstrap import frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.oracles.subject import check_subject_completion, check_subject_substitution
from evaluation.vectors import credential_digest
from evaluation.worker_evidence import WorkerLog


def _save(output, name, data):
    (output/(name+'.json')).write_text(json.dumps(data, indent=2)+'\n')


def _decode(chain, logs):
    rows = []
    for log in logs:
        contract = next((c for c in chain.contracts.values() if c.address == log['address']), None)
        require(contract is not None, 'subject full history contract')
        row = contract.decode_log(log)
        require(row is not None, 'subject full history decoded event')
        rows.append(dict(name=row['name'], fields=row['fields']))
    return rows


def _snapshot(pbc, dbc, *, deployment, request, digest, target_gid, grant_id, worker_snapshot, output, name):
    """Block-anchored whole-history snapshot shared by every subject stage."""
    with dbc.read_group(tuple(dbc.contracts)) as domain:
        grant = domain.read('KSSC', 'grantDetails', grant_id)[0]
        nonce_alice = domain.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'])[0]
        nonce_bob = domain.read('KSSC', 'nonceConsumed', target_gid, request['nonce'])[0]
        count = domain.read('ACSC', 'accessLogCount')[0]
        logs_dbc = _decode(dbc, domain.logs())
    with pbc.read_group(tuple(pbc.contracts)) as proxy:
        state = proxy.read('PSC', 'getRequest', digest)[0]
        require(proxy.read('RSC', 'isRegistered', target_gid) == [True], 'registered substituted subject')
        logs_pbc = _decode(pbc, proxy.logs())
    worker = strict_json(worker_snapshot()); WorkerLog(worker, fingerprint=_fingerprint(deployment))
    payload = dict(grant=grant, request=state, nonceAlice=nonce_alice, nonceBob=nonce_bob,
                   accessLogCount=count, logs=dict(pbc=logs_pbc, dbc=logs_dbc), worker=worker)
    _save(output, name+'-blocks', dict(pbc=proxy.block, dbc=domain.block)); _save(output, name, payload)
    return payload


def collect_subject_substitution(pbc, dbc, *, deployment, request, prepared,
                                 original_native, original_bundle, forwarded, records, decision,
                                 target_gid, grant_id, worker_snapshot, output):
    """Collect authenticated calls and full block-anchored pre/post histories.

    Returns (result, oracle inputs). No worker release, completion, outcome,
    clock mutation or retry occurs here. Raw receipts, view returns and RPC
    commands remain in the public executors.
    """
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None,
                  scope='C-E2 subject pre-release stage; full case and gate incomplete', delivery='unknown')

    def mined(chain, native, role, method, args):
        tx_hash = native.receipt['transactionHash']
        tx = chain.rpc.call('eth_getTransactionByHash', [tx_hash])
        require(tx is not None and tx['hash'] == tx_hash
                and tx['input'] == chain.contracts[role].calldata(method, *args)
                and tx['to'] == chain.contracts[role].address
                and tx['from'] == deployment['fixture']['relay']['address']
                and tx['blockHash'] == native.block_hash
                and int(tx['blockNumber'], 16) == int(native.block_number), 'subject mined call identity/calldata/relay/block')
        return tx

    try:
        frozen_validate('LedgerDeployment', deployment)
        frozen_validate('Address', target_gid)
        require(target_gid != request['gid'], 'different substituted subject')
        digest = verify_prepared(prepared, request=request, deployment=deployment)
        require(original_native.success is True, 'successful original PBC request')
        frozen_validate('CredentialBundle', original_bundle)
        original_tx = mined(pbc, original_native, 'PSC', 'requestAccess',
                            [request, prepared['signature'], original_bundle])
        repaired = deployment['profile'] == 'repaired-e'
        certificate = None
        if repaired:
            frozen_validate('CollectDecisionResult', decision); _witness('AccessDecision', decision, deployment)
            require(decision['credentialRecords'] == records
                    and decision['decision']['credentialDigest'] == credential_digest(records), 'original witness credentials')
            certificate = {k: copy.deepcopy(decision[k]) for k in ('decision', 'signatures')}
        else:
            require(decision is None, 'paper profile has no decision certificate')
        altered = copy.deepcopy(request if repaired else forwarded); altered['gid'] = target_gid
        args = [altered, certificate, copy.deepcopy(records)] if repaired else [altered, copy.deepcopy(records)]
        method = 'consumeDecision' if repaired else 'policyEnf'
        _save(output, 'public-call', dict(originalTransaction=original_tx, originalRequest=request,
                                          prepared=prepared, method=method, arguments=args, originalDecision=decision))
        snap = dict(deployment=deployment, request=request, digest=digest, target_gid=target_gid,
                    grant_id=grant_id, worker_snapshot=worker_snapshot, output=output)
        before = _snapshot(pbc, dbc, name='before', **snap)
        require(before['grant']['exists'] is False and before['accessLogCount'] == '0'
                and before['nonceAlice'] is False and before['nonceBob'] is False,
                'fresh stress grant/count/nonces before submission')
        native = dbc.submit('relay', 'ACSC', method, *args, expect_success=not repaired)
        tx = mined(dbc, native, 'ACSC', method, args); _save(output, 'substituted-transaction', tx)
        code = dbc.rejection_code(native) if repaired else None
        events = _decode(dbc, native.receipt['logs'])
        after = _snapshot(pbc, dbc, name='after', **snap)
        inputs = dict(profile=deployment['profile'], original_request=request,
            request_digest=digest, forwarded=forwarded, records=records, certificate=certificate,
            submitted_arguments=args, target_gid=target_gid, grant_id=grant_id,
            credential_digest=credential_digest(records), relay=deployment['fixture']['relay']['address'],
            before=before, after=after, success=native.success, rejection_code=code,
            receipt_events=events, timestamp=native.timestamp)
        proof = check_subject_substitution(**inputs)
        result.update(proof, transactionHash=native.receipt['transactionHash'], rejectionCode=code)
        return result, inputs
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)


def execute_subject_substitution(pbc, dbc, **kwargs):
    """Pre-release stage only; see collect_subject_substitution."""
    return collect_subject_substitution(pbc, dbc, **kwargs)[0]


def execute_subject_completion(pbc, dbc, provider, *, deployment, pre_release, ciphertext_digest,
                               original_label, target_label, worker_snapshot, output):
    """Paper profiles: release the substituted grant once, then complete it twice.

    `provider` is the caller's frozen-schema adapter wrapper. The release
    response stays in memory; only redacted exchanges/commitments are written.
    Whole native and worker snapshots use the pre-release snapshot shape, so the
    oracle can require that release adds exactly one worker cache/intent/send
    delta and that completions change nothing. No outcome is reported.
    """
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, delivery='unknown',
                  scope='C-E2 paper subject completion stage; catalog row needs the separate controls')
    try:
        frozen_validate('LedgerDeployment', deployment)
        require(deployment['profile'] in ('paper-strict', 'paper-minimal')
                and pre_release['profile'] == deployment['profile'], 'paper subject completion only')
        request, target_gid, grant_id = pre_release['original_request'], pre_release['target_gid'], pre_release['grant_id']
        expected = {label: '0x'+keccak(text='HMBC.recipient-key.'+label).hex() for label in (original_label, target_label)}
        require(original_label != target_label and request['recipientKeyHash'] == expected[original_label],
                'fixture recipient labels (A35)')
        with pbc.read_group(('RSC',)) as proxy:
            registered = proxy.read('RSC', 'recipientKeyHash', target_gid)[0]
            original_registered = proxy.read('RSC', 'recipientKeyHash', request['gid'])[0]
        require(registered == expected[target_label] and original_registered == expected[original_label],
                'registered PBC recipient keys for both subjects')
        _save(output, 'recipients', dict(block=proxy.block, target=registered, original=original_registered))
        snap = dict(deployment=deployment, request=request, digest=pre_release['request_digest'],
                    target_gid=target_gid, grant_id=grant_id, worker_snapshot=worker_snapshot, output=output)
        response = provider.call('release', dict(grantId=grant_id))
        dbc_now = _clock(dbc)
        after_release = _snapshot(pbc, dbc, name='after-release', **snap)
        target = provider.response('finish_decryption', dict(response=response, userKeyRef='keyref:user:'+target_label))
        original = provider.response('finish_decryption', dict(response=response, userKeyRef='keyref:user:'+original_label))
        after_completion = _snapshot(pbc, dbc, name='after-completion', **snap)
        proof = check_subject_completion(pre_release=pre_release, registered_recipient=registered,
            original_recipient=request['recipientKeyHash'], ciphertext_digest=ciphertext_digest,
            response=response, bob_completion=target, alice_completion=original,
            after_release=after_release, after_completion=after_completion, dbc_now=dbc_now,
            fingerprint=_fingerprint(deployment))
        result.update(proof, dbcClockAfterRelease=dbc_now, targetLabel=target_label, originalLabel=original_label,
                      targetCompletion=dict(ok=target['ok'], decryptable=target['result']['decryptable']),
                      originalCompletion=dict(ok=original['ok'], error=original['error']['code']))
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); _save(output, 'result', result)
