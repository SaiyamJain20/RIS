"""Independent E03 audit-correspondence oracles (SL3) for the paper-derived reconstruction.

Expectations: frozen rows E03-dropped-outcome and E03-fabricated-outcome, SPEC4/E03 and the
pinned ledger (933d2a7): the DBC grant, the worker release (intent then attempted send) and the
PBC outcome are distinct events; a dropped outcome leaves the PBC request PENDING (FORWARDED)
with no outcome record, and local worker logs never imply delivery. Paper PSC.reportOutcome
accepts a configured-relay outcome without any DBC grant (LSC OUTCOME(4) log with
abi.encode(digest, grantId, outcomeDigest, relay)); repaired-e disables it (WRONG_PROFILE 21)
and the honest witness refuses to attest a missing grant (NOT_COMMITTED). Configured-relay
stress is outside A01: paper results are reconstruction specification gaps, never exploits.
"""
import copy

from eth_abi import encode
from eth_utils import keccak

from evaluation.access_artifacts import require
from evaluation.evm import _hex
from evaluation.oracles.provenance import _idle
from evaluation.worker_evidence import WorkerLog

ZERO = '0x'+'00'*32
_NATIVE = ('grants', 'requests', 'accessLogCount', 'nonces', 'logs')
_OUTCOME_EVENTS = ('OutcomeRecorded', 'AttestedOutcomeRecorded')


def _native(snapshot):
    return {k: copy.deepcopy(snapshot[k]) for k in _NATIVE}


def _pending(request):
    require(request['status'] == '1' and request['outcomeLogId'] == '0', 'PBC request FORWARDED without an outcome (PENDING)')


def check_dropped_outcome(*, profile, before, after, request_digest, grant_id, gid, data_id, expected_recipient,
                          ciphertext_digest, response, dbc_now, fingerprint):
    """One production release on a live grant, then no outcome report: PBC stays PENDING."""
    require(profile in ('paper-strict', 'paper-minimal', 'repaired-e'), 'E reconstruction profile')
    repaired = profile == 'repaired-e'
    grant = before['grants'][grant_id]
    require(grant['exists'] is True and grant['allowed'] is True and grant['requestDigest'] == request_digest
            and grant['gid'] == gid and grant['dataId'] == data_id and grant['keyEpoch'] == '0', 'allowed DBC grant for the request')
    require(grant['recipientKeyHash'] == (expected_recipient if repaired else ZERO),
            'native grant recipient: signed key (repaired) or zero with off-chain registered key (paper, D35/A38)')
    _pending(before['requests'][request_digest]); _pending(after['requests'][request_digest])
    require(_native(after) == _native(before), 'release changes no native state; no outcome, grant or log delta')
    require(not any(row['name'] in _OUTCOME_EVENTS for row in after['logs']['pbc']), 'no outcome event in PBC history')
    expected = dict(requestDigest=request_digest, grantId=grant_id, dataId=data_id, ciphertextDigest=ciphertext_digest,
                    recipientKeyHash=expected_recipient, keyEpoch='0')
    require(all(response.get(k) == v for k, v in expected.items()), 'release response binds request/grant/record/recipient')
    require(before['worker'].get('instantiated') is True and after['worker'].get('instantiated') is True, 'instantiated worker exports')
    _idle(before['worker'])
    prior, log = before['worker']['log'], after['worker']['log']
    checked = WorkerLog(log, fingerprint=fingerprint)
    row = checked.check_response(response)
    events = checked.events_for(grant_id)
    issued, expires, observed = int(grant['issuedAt']), int(grant['expiresAt']), int(dbc_now)
    require(row['gid'] == gid and row['grantExpiresAt'] == grant['expiresAt'] and row['delivery'] == 'unknown'
            and row['sendAttempts'] == 1 and row['completedAttempts'] == 1 and issued <= int(row['createdAt']) <= observed < expires,
            'one release strictly inside the original grant lifetime; delivery unknown')
    require([e['type'] for e in events] == ['RELEASE_INTENT', 'RELEASE_SENT']
            and all(issued <= int(e['timestamp']) <= observed for e in events), 'durable intent then one attempted send')
    expected_log = copy.deepcopy(prior); expected_log.update(events=prior['events']+events, releases=[row],
                                                             counts=dict(releaseIntentCount='1', releaseSentCount='1'))
    require(log == expected_log, 'exactly one worker release delta')
    return dict(ok=True, outcome='PENDING', classification='REPAIR_SUPPORTED' if repaired else 'SUPPORTED', error=None,
                delivery='unknown', qualification='local durable intent/send log only; delivery unknown; eventual reconciliation needs '
                'eventual delivery and an honest reporter; tested reconstruction result')


def check_fabricated_outcome(*, profile, before, after, request_digest, grant_id, outcome_digest, relay,
                             success, rejection_code, receipt_events, attestation):
    """Paper: a relay outcome without any DBC grant is recorded (SPEC_GAP).
    Repaired-e: the unattested path is disabled (WRONG_PROFILE) and the witness will not attest."""
    require(profile in ('paper-strict', 'paper-minimal', 'repaired-e'), 'E reconstruction profile')
    _idle(before['worker']); require(after['worker'] == before['worker'], 'worker unchanged')
    require(before['grants'][grant_id]['exists'] is False and before['accessLogCount'] == '0'
            and not any(row['name'] == 'GrantIssued' for row in before['logs']['dbc']), 'no DBC grant or consumption at all')
    _pending(before['requests'][request_digest])
    if profile == 'repaired-e':
        require(success is False and rejection_code == '21' and receipt_events == [], 'mined WRONG_PROFILE without events')
        require(_native(after) == _native(before), 'whole native state unchanged')
        require(attestation == dict(ok=False, error='NOT_COMMITTED'), 'honest witness refuses to attest a missing grant')
        return dict(ok=True, classification='REPAIR_SUPPORTED', error='WRONG_PROFILE', delivery='unknown', outcomeWithoutGrant=False,
                    qualification='unattested outcome path disabled; receipt witness requires a matching DBC grant')
    require(attestation is None, 'paper profile has no receipt witness')
    require(success is True and rejection_code is None, 'paper relay outcome mined successfully')
    require([e['name'] for e in receipt_events] == ['LogRecorded', 'OutcomeRecorded'], 'outcome log then outcome event')
    log, event = receipt_events[0]['fields'], receipt_events[1]['fields']
    details = '0x'+encode(['bytes32', 'bytes32', 'bytes32', 'address'],
                          [_hex(request_digest, 32), _hex(grant_id, 32), _hex(outcome_digest, 32), relay]).hex()
    require(log['kind'] == '4' and log['subject'] == request_digest and log['details'] == details
            and log['detailsHash'] == '0x'+keccak(bytes.fromhex(details[2:])).hex(), 'LSC OUTCOME log with complete details')
    require(event == dict(requestDigest=request_digest, grantId=grant_id, outcomeDigest=outcome_digest, logId=log['logId']),
            'outcome event binds request, derived grant id, outcome and log')
    expected = _native(before)
    expected['requests'][request_digest] = dict(expected['requests'][request_digest], status='2', outcomeLogId=log['logId'])
    expected['logs']['pbc'] = expected['logs']['pbc']+copy.deepcopy(receipt_events)
    require(_native(after) == expected, 'only the PBC outcome delta; DBC grant/count/nonces/history unchanged')
    return dict(ok=True, classification='SPEC_GAP', error=None, delivery='unknown', outcomeWithoutGrant=True,
                qualification='configured-relay stress outside A01: the PBC records an outcome for which no DBC grant exists; '
                              'reconstruction specification gap, not an HMBC exploit')
