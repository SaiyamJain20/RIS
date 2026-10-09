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

ZERO = '0x'+'00'*32


def check_subject_substitution(*, profile, original_request, request_digest,
                               forwarded, records, certificate, submitted_arguments,
                               target_gid, grant_id, credential_digest, relay, before, after,
                               success, rejection_code, receipt_events, timestamp):
    """Check a gid-only alteration before any original grant or worker release.

Paper accepts the relay-asserted subject in this reconstruction; the repaired
request retains its original certificate and must fail WRONG_SUBJECT (3).
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
        require(success is False and rejection_code == '3' and receipt_events == [],
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
