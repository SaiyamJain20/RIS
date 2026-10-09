"""Independent pre-release E01 subject-substitution evidence checks.

Expectations: frozen subject-substitution cases, SPEC4/E01 and D35/A38.
Compromising the configured relay violates the paper isolation assumption.
This oracle checks observations; it cannot authenticate RPC or signatures.
The future collector must verify the original user/witness signatures, native
transaction/calldata/deployment/relay and block-anchored ABI observations.
Histories here are decoded contract events in canonical transaction/log order.
Release, registered-recipient routing, decryption, positive/denial controls and
the complete execution recipe are separate mandatory collector work. Synthetic
acceptance of these observations is never an integrated catalog result.
"""
import copy

from evaluation.access_artifacts import require
from evaluation.bootstrap import frozen_validate
from evaluation.worker_evidence import WorkerLog

ZERO = '0x'+'00'*32


def check_subject_substitution(*, profile, original_request, request_digest,
                               forwarded, records, certificate, submitted_arguments,
                               target_gid, grant_id, credential_digest, relay, before, after,
                               success, rejection_code, receipt_events, timestamp):
    """Check a gid-only alteration before any original grant or worker release.

Paper accepts the relay-asserted subject in this reconstruction; the repaired
request retains its original certificate and must fail WRONG_SUBJECT (2).
Never rewrite a decision digest or relabel this as a signature-failure case.
    """
    require(profile in ('paper-strict', 'paper-minimal', 'repaired-e'), 'E reconstruction profile')
    require(target_gid != original_request['gid'] and bool(target_gid), 'different target subject')
    require(original_request['action'] == '1', 'READ action')
    require(isinstance(records, list) and bool(records), 'original verified credential records')
    require(forwarded == dict(pbcRequestId=request_digest, gid=original_request['gid'],
                             dataId=original_request['dataId'], action=original_request['action']),
            'original forward binding')
    repaired = profile == 'repaired-e'
    changed = copy.deepcopy(original_request if repaired else forwarded)
    changed['gid'] = target_gid
    expected_args = [changed, copy.deepcopy(certificate), copy.deepcopy(records)] if repaired else [changed, copy.deepcopy(records)]
    require(submitted_arguments == expected_args, 'only subject altered; original credentials and certificate retained')
    if repaired:
        require(certificate['decision']['requestDigest'] == request_digest
                and certificate['decision']['result'] == '1'
                and isinstance(certificate['signatures'], list) and bool(certificate['signatures']),
                'original ALLOW certificate')
    request = before['request']
    require(request['gid'] == original_request['gid'] and request['dataId'] == original_request['dataId']
            and request['expiresAt'] == original_request['expiresAt'] and request['status'] == '1'
            and int(request['requestLogId']) > 0 and request['outcomeLogId'] == '0',
            'original logged FORWARDED request remains pending')
    require(0 <= int(request['decidedAt']) <= int(timestamp) < int(original_request['expiresAt']), 'live original request')
    require(before['grant']['exists'] is False and before['grant']['allowed'] is False
            and before['accessLogCount'] == '0'
            and before['nonceAlice'] is False and before['nonceBob'] is False, 'fresh unconsumed stress scenario')
    require(set(before['logs']) == {'pbc', 'dbc'}
            and all(isinstance(rows, list) for rows in before['logs'].values())
            and bool(before['logs']['pbc']), 'complete decoded two-chain histories')
    if repaired:
        require(success is False and rejection_code == '2' and receipt_events == [],
                'mined WRONG_SUBJECT without events')
        require(after == before, 'whole native and worker state unchanged')
    else:
        require(success is True and rejection_code is None, 'paper tuple authorized; deny-all is not this observation')
        expiry = str(int(timestamp)+30)
        grant = dict(exists=True, allowed=True, requestDigest=request_digest, gid=target_gid,
                     dataId=original_request['dataId'], recipientKeyHash=ZERO,
                     keyEpoch='0', issuedAt=timestamp, expiresAt=expiry)
        require(after['grant'] == grant, 'paper grant uses substituted subject and canonical TTL/zero recipient')
        require(len(receipt_events) == 2 and [e['name'] for e in receipt_events] == ['GrantIssued', 'AccessLog'],
                'exact grant and access event order')
        grant_event = dict(grantId=grant_id, requestDigest=request_digest, gid=target_gid,
                           dataId=original_request['dataId'], keyEpoch='0', expiresAt=expiry,
                           recipientKeyHash=ZERO, nonceConsumed=False, nonce='0')
        require(receipt_events[0]['fields'] == grant_event, 'complete grant event/state join')
        access = receipt_events[1]['fields']
        require(all(access[k] == v for k, v in dict(requestRef=request_digest, gid=target_gid,
                    dataId=original_request['dataId'], allowed=True, code='0', grantId=grant_id,
                    credentialDigest=credential_digest, submitter=relay).items()), 'access tuple, relay and original credential digest')
        expected_after = copy.deepcopy(before)
        expected_after.update(grant=grant, accessLogCount='1')
        expected_after['logs']['dbc'] += receipt_events
        require(after == expected_after, 'only one native grant/access delta; proxy, nonces and worker unchanged')
    return dict(ok=True, classification='REPAIR_SUPPORTED' if repaired else 'SPEC_GAP',
                error='WRONG_SUBJECT' if repaired else None, delivery='unknown',
                workerUnchanged=True, releaseTested=False,
                qualification='pre-release reconstruction observation under compromised-relay stress; not an HMBC vulnerability or integrated gate')


def check_subject_completion(*, pre_release, registered_recipient, original_recipient,
                             ciphertext_digest, response, bob_completion, alice_completion,
                             after_release, after_completion, dbc_now, fingerprint):
    """Check paper-profile response/cache routing and symbolic completion facts.

    The collector must authenticate the pre-release calls, collect the registered
    keys and ciphertext commitment independently, submit the same response to
    Bob/Alice key references, and retain block-anchored snapshots at each stage.
    This checker cannot authenticate those observations or prove encryption,
    delivery, storage durability or a completed catalog case. No outcome is
    submitted: the original pending Alice request must stay unchanged.
    """
    require(pre_release['profile'] in ('paper-strict', 'paper-minimal'),
            'paper subject completion only; repaired rejection has no release')
    check_subject_substitution(**pre_release)
    grant = pre_release['after']['grant']
    original = pre_release['original_request']
    for value in (registered_recipient, original_recipient, ciphertext_digest):
        frozen_validate('Hash', value)
    frozen_validate('Uint64', dbc_now)
    require(registered_recipient != ZERO and original_recipient != ZERO
            and registered_recipient != original_recipient
            and original_recipient == original['recipientKeyHash'],
            'distinct registered target and original recipient commitments')
    before_worker = pre_release['after']['worker']
    WorkerLog(before_worker, fingerprint=fingerprint)
    require(before_worker['events'] == [] and before_worker['releases'] == []
            and before_worker['counts'] == dict(releaseIntentCount='0', releaseSentCount='0'),
            'fresh stress worker before release')
    frozen_validate('ReleaseResult', response)
    expected = dict(requestDigest=pre_release['request_digest'], grantId=pre_release['grant_id'],
                    dataId=original['dataId'], ciphertextDigest=ciphertext_digest,
                    recipientKeyHash=registered_recipient, keyEpoch='0')
    require(all(response[k] == v for k, v in expected.items()),
            'subject response binds original reference/data and substituted registered recipient')
    worker = after_release['worker']
    checked = WorkerLog(worker, fingerprint=fingerprint)
    row = checked.check_response(response)
    events = checked.events_for(pre_release['grant_id'])
    issued, expires, observed = map(int, (grant['issuedAt'], grant['expiresAt'], dbc_now))
    require(row['gid'] == pre_release['target_gid']
            and row['grantExpiresAt'] == grant['expiresAt']
            and issued <= int(row['createdAt']) <= observed < expires
            and row['sendAttempts'] == row['completedAttempts'] == 1
            and [e['type'] for e in events] == ['RELEASE_INTENT', 'RELEASE_SENT']
            and all(issued <= int(e['timestamp']) <= observed < expires for e in events),
            'one target-subject release intent/send within original native lifetime')
    expected_worker = copy.deepcopy(before_worker)
    expected_worker.update(events=events, releases=[row],
                           counts=dict(releaseIntentCount='1', releaseSentCount='1'))
    require(worker == expected_worker, 'only one worker release/cache delta')
    expected_after = copy.deepcopy(pre_release['after']); expected_after['worker'] = expected_worker
    require(after_release == expected_after,
            'release preserves original pending request, native zero recipient, nonces and both histories')
    for completion in (bob_completion, alice_completion):
        frozen_validate('FinishDecryptionResponse', completion)
    expected_bob = dict(schemaVersion='v1', adapterMode='symbolic', decryptable=True,
                        dataId=original['dataId'], ciphertextDigest=ciphertext_digest)
    require(bob_completion['ok'] is True and bob_completion['result'] == expected_bob,
            'substituted subject symbolic completion for the same record')
    require(alice_completion['ok'] is False and alice_completion['error']['code'] == 'WRONG_SUBJECT',
            'original subject wrong-recipient refusal')
    require(after_completion == after_release, 'both completions leave whole native/worker state unchanged')
    return dict(ok=True, classification='SPEC_GAP', adapterMode='symbolic', delivery='unknown',
                bobDecryptable=True, aliceError='WRONG_SUBJECT', outcomeTested=False,
                integratedCaseComplete=False,
                qualification='observed reconstruction routing/completion under compromised-relay stress; '
                              'collector authentication, independent fresh controls and integrated gate remain separate')
