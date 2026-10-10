"""Independent E01 relay-stress oracles (SL2) for the paper-derived reconstruction.

Expectations: frozen catalog rows E01-forged-tuple, E01-new-reference-replay and
E01-same-nonce-distinct-digests-repaired-e, SPEC4/E01 and the pinned ledger
facts in A1-0062 (ledger 933d2a7). Compromising the configured relay is outside
the paper secure-isolation assumption (A01): paper results are specification
gaps of the reconstruction, never HMBC exploits. Snapshots are whole decoded
contract histories plus selected views; the collector authenticates them.
"""
import copy

from evaluation.access_artifacts import require

ZERO = '0x'+'00'*32
_STATE = ('grants', 'requests', 'accessLogCount', 'nonces', 'logs')


def _idle(worker):
    require(worker['events'] == [] and worker['releases'] == []
            and worker['counts'] == dict(releaseIntentCount='0', releaseSentCount='0'), 'idle worker (no release in E01 relay stress)')


def _whole(snapshot, keys=_STATE):
    return {k: copy.deepcopy(snapshot[k]) for k in keys}


def _paper_grant(*, ref, grant_id, gid, data_id, relay, credential_digest, count, timestamp, events):
    """Exact paper policyEnf observation: one GrantIssued then one AccessLog."""
    require([e['name'] for e in events] == ['GrantIssued', 'AccessLog'], 'exact grant then access event order')
    expiry = str(int(timestamp)+30)
    require(events[0]['fields'] == dict(grantId=grant_id, requestDigest=ref, gid=gid, dataId=data_id, keyEpoch='0',
                                        expiresAt=expiry, recipientKeyHash=ZERO, nonceConsumed=False, nonce='0'),
            'paper grant event: relay reference, zero recipient, TTL +30 s, no nonce')
    require(events[1]['fields'] == dict(accessLogId=str(count), requestRef=ref, gid=gid, dataId=data_id, allowed=True, code='0',
                                        credentialDigest=credential_digest, grantId=grant_id, submitter=relay),
            'paper access log: allowed, relay submitter, verified credential digest')
    return dict(exists=True, allowed=True, requestDigest=ref, dataId=data_id, gid=gid, keyEpoch='0', expiresAt=expiry,
                recipientKeyHash=ZERO, issuedAt=str(timestamp))


def check_forged_tuple(*, profile, before, after, gid, data_id, relay, fabricated_ref, grant_id, credential_digest,
                       success, rejection_code, receipt_events, timestamp, forged=None):
    """Paper: a relay-fabricated tuple with no PBC request/log is granted (SPEC_GAP).
    Repaired-e: an otherwise identical certificate signed by a non-witness is
    rejected BAD_SIGNATURE (1) after the honest certificate simulates successfully."""
    require(profile in ('paper-strict', 'paper-minimal', 'repaired-e'), 'E reconstruction profile')
    _idle(before['worker']); _idle(after['worker']); require(before['worker'] == after['worker'], 'worker unchanged')
    require(before['grants'][grant_id]['exists'] is False, 'no prior grant for the stress reference')
    if profile == 'repaired-e':
        require(isinstance(forged, dict), 'forged certificate facts')
        require(before['requests'][fabricated_ref]['status'] == '1', 'honest PBC request exists for the repaired control')
        require(forged['honestSimulationGrantId'] == grant_id, 'honest certificate simulates the expected grant (eth_call, not mined)')
        require(forged['recoveredSigner'] == relay and forged['recoveredSigner'] not in forged['witnesses'],
                'forged signature recovers to the non-witness relay')
        require(forged['decisionUnchanged'] is True and forged['signatureChanged'] is True, 'only the signature differs')
        require(forged['signedDigestEqual'] is True,
                'relay signed the exact digest/domain the honest witness signature recovers under (A1-0064)')
        require(success is False and rejection_code == '1' and receipt_events == [], 'mined BAD_SIGNATURE without events')
        require(_whole(after) == _whole(before), 'whole native state unchanged')
        return dict(ok=True, classification='REPAIR_SUPPORTED', error='BAD_SIGNATURE', delivery='unknown', grantWithoutPbcLog=False,
                    qualification='non-witness signature on an otherwise matching certificate; DecisionVerifier step 6 precedes any grant')
    require(forged is None, 'paper profile has no certificate')
    require(before['requests'][fabricated_ref]['status'] == '0' and after['requests'][fabricated_ref]['status'] == '0',
            'PBC never logged or forwarded the fabricated reference')
    require(success is True and rejection_code is None, 'paper tuple mined successfully; deny-all is not this observation')
    count = int(before['accessLogCount'])+1
    grant = _paper_grant(ref=fabricated_ref, grant_id=grant_id, gid=gid, data_id=data_id, relay=relay,
                         credential_digest=credential_digest, count=count, timestamp=timestamp, events=receipt_events)
    expected = _whole(before); expected['grants'][grant_id] = grant; expected['accessLogCount'] = str(count)
    expected['logs']['dbc'] = expected['logs']['dbc']+copy.deepcopy(receipt_events)
    require(_whole(after) == expected, 'only one grant/access delta; PBC history, nonces and other grants unchanged')
    return dict(ok=True, classification='SPEC_GAP', error=None, delivery='unknown', grantWithoutPbcLog=True,
                qualification='configured-relay stress outside A01: a DBC grant exists with no PBC request or log; '
                              'reconstruction specification gap, not an HMBC exploit')


def check_new_reference(*, profile, before, after, gid, data_id, relay, original_ref, original_grant, replay_ref, replay_grant,
                        credential_digest, identical_calldata, success, rejection_code, receipt_events, timestamp):
    """Paper: the same verified tuple under a fresh relay reference is granted again
    (SPEC_GAP). Repaired-e: re-consuming the signed request/certificate is REPLAY (8)."""
    require(profile in ('paper-strict', 'paper-minimal', 'repaired-e'), 'E reconstruction profile')
    _idle(before['worker']); _idle(after['worker']); require(before['worker'] == after['worker'], 'worker unchanged')
    first = before['grants'][original_grant]
    require(first['exists'] is True and first['requestDigest'] == original_ref and first['gid'] == gid, 'one prior original grant')
    require(before['requests'][original_ref]['status'] == '1', 'original PBC request forwarded')
    if profile == 'repaired-e':
        require(identical_calldata is True and replay_ref == original_ref and replay_grant == original_grant,
                'repaired reuses the original signed request and certificate')
        require(success is False and rejection_code == '8' and receipt_events == [], 'mined REPLAY without events')
        require(_whole(after) == _whole(before), 'whole native state unchanged')
        return dict(ok=True, classification='REPAIR_SUPPORTED', error='REPLAY', delivery='unknown', secondGrant=None,
                    qualification='grant uniqueness (KSSC.sol:180) rejects before the nonce check (:182); the nonce guard is '
                                  'reached only by the same-nonce distinct-digest row')
    require(identical_calldata is False and replay_ref != original_ref and replay_grant != original_grant, 'fresh relay reference')
    require(before['grants'][replay_grant]['exists'] is False, 'no prior grant for the fresh reference')
    require(before['requests'][replay_ref]['status'] == '0' and after['requests'][replay_ref]['status'] == '0',
            'fresh reference never logged at the PBC')
    require(success is True and rejection_code is None, 'paper second tuple mined successfully')
    count = int(before['accessLogCount'])+1
    grant = _paper_grant(ref=replay_ref, grant_id=replay_grant, gid=gid, data_id=data_id, relay=relay,
                         credential_digest=credential_digest, count=count, timestamp=timestamp, events=receipt_events)
    expected = _whole(before); expected['grants'][replay_grant] = grant; expected['accessLogCount'] = str(count)
    expected['logs']['dbc'] = expected['logs']['dbc']+copy.deepcopy(receipt_events)
    require(_whole(after) == expected, 'one second grant; original grant/request and PBC history unchanged')
    return dict(ok=True, classification='SPEC_GAP', error=None, delivery='unknown', secondGrant=replay_grant,
                qualification='configured-relay stress outside A01 (A25): a second grant without a second PBC request; '
                              'reconstruction specification gap, not an HMBC exploit')


def check_same_nonce(*, first, second, checkpoint, decisions, consume_first, before_second, after_second, before_block,
                     second_block, success, rejection_code, receipt_events, worker_before, worker_after):
    """Repaired-e only: two valid same-(gid, nonce) requests with distinct digests,
    both certified before consumption; the second pre-collected certificate is
    REPLAY (8) at the nonce guard (KSSC.sol:182) and leaves the first grant unchanged."""
    a, b = first['request'], second['request']
    require(a['gid'] == b['gid'] and a['nonce'] == b['nonce'] and a['expiresAt'] != b['expiresAt'],
            'same gid/nonce, distinct expiry')
    require(first['digest'] != second['digest'] and first['grantId'] != second['grantId'], 'distinct digests and derived grant ids')
    require(int(checkpoint['sourceBlockNumber']) >= max(int(first['block']), int(second['block'])), 'one checkpoint after both forwards')
    require(len(decisions) == 2, 'both certificates')
    for row, request in zip(decisions, (first, second)):
        d = row['decision']
        require(d['requestDigest'] == request['digest'] and d['result'] == '1' and d['stateSequence'] == checkpoint['sequence'],
                'honest ALLOW certificate for each request at the shared checkpoint')
        require(int(row['dbcBlock']) < int(consume_first['block']), 'certificate collected before any consumption')
    events = consume_first['events']
    require(consume_first['success'] is True and [e['name'] for e in events] == ['GrantIssued', 'AccessLog']
            and events[0]['fields']['grantId'] == first['grantId'] and events[0]['fields']['nonceConsumed'] is True
            and events[0]['fields']['nonce'] == a['nonce'], 'first consumption grants and consumes the nonce')
    require(before_second['grants'][first['grantId']]['exists'] is True
            and before_second['grants'][second['grantId']]['exists'] is False
            and [a['gid'], a['nonce'], True] in before_second['nonces'], 'first grant and consumed nonce precede the second')
    require(int(before_block) == int(second_block)-1, 'pinned pre-state is the block before the second consumption')
    require(success is False and rejection_code == '8' and receipt_events == [],
            'second pre-collected certificate mined REPLAY without events (EXPIRED or other codes mask the nonce guard)')
    require(_whole(after_second) == _whole(before_second), 'no second grant; first grant, nonce, count and histories unchanged')
    _idle(worker_before); require(worker_after == worker_before, 'worker unchanged')
    return dict(ok=True, classification='REPAIR_SUPPORTED', error='REPLAY', delivery='unknown', nonceGuardReached=True,
                qualification='distinct digests give distinct grant ids, so grant uniqueness cannot fire; the (gid, nonce) '
                              'guard at KSSC.sol:182 rejects the second consumption')
