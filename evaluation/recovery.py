"""Independent C-E2 recovery joins, derived from the accepted start contract.

Redacted exports prove supplied-fact consistency only. Native grant provenance,
process exit observations, source stability and same-state restart are composed by
the runner. Attempted transmission is not recipient delivery or power-loss proof.
"""
import hashlib
import json

from evaluation.access_artifacts import require
from evaluation.worker_evidence import WorkerLog, IDENTITY

ZERO = '0x'+'00'*32
EXPECTED = {
    'after_intent': (['RELEASE_INTENT'], (0, 0), ['RELEASE_INTENT', 'RELEASE_SENT'], (1, 1)),
    'after_send': (['RELEASE_INTENT', 'RELEASE_SENT'], (1, 0), ['RELEASE_INTENT', 'RELEASE_SENT', 'RELEASE_SENT'], (2, 1)),
}


def _stage(before, payload, *, grant, grant_id, recipient, fingerprint, dbc_now, names, attempts):
    checked = WorkerLog(payload, fingerprint=fingerprint)
    events = checked.events_for(grant_id)
    require([event['type'] for event in events] == names, 'recovery stage event sequence')
    rows = [row for row in payload['releases'] if row['grantId'] == grant_id]
    require(len(rows) == 1, 'one recovery cache')
    row = rows[0]
    require(tuple(row[k] for k in ('sendAttempts', 'completedAttempts')) == attempts, 'recovery stage attempt counts')
    require(all(row[k] == grant[k] for k in ('requestDigest', 'gid', 'dataId', 'keyEpoch'))
            and row['grantExpiresAt'] == grant['expiresAt'] and row['recipientKeyHash'] == recipient, 'recovery native identity/expiry/recipient')
    require(int(grant['issuedAt']) <= int(row['createdAt']) < int(grant['expiresAt']), 'recovery intent within native permission')
    require(all(int(grant['issuedAt']) <= int(event['timestamp']) <= int(dbc_now)
                and int(event['timestamp']) < int(grant['expiresAt']) for event in events), 'recovery events before original expiry')
    require(payload['events'] == before['events']+events
            and len(payload['releases']) == len(before['releases'])+1
            and all(old in payload['releases'] for old in before['releases']), 'recovery exact worker delta')
    return checked, row


def check_recovery(*, before, crashed, after, response, crash_response, grant, grant_id,
                   recipient, point, fingerprint, dbc_now):
    """Join one new intent/cache with natural-crash and retry stage exports.

    Caller supplies a previously verified native grant and registered recipient.
    The frozen paper grant can have zero recipient; the access executor separately
    enforces the profile-specific grant and registration rule before calling here.
    Late evidence collection is allowed; each actual intent/send must predate expiry.
    """
    require(point in EXPECTED, 'named recovery point')
    require(grant['exists'] is True and grant['allowed'] is True
            and grant['recipientKeyHash'] in (ZERO, recipient), 'authorized native recovery grant')
    baseline = WorkerLog(before, fingerprint=fingerprint)
    require(not baseline.events_for(grant_id)
            and all(row['grantId'] != grant_id for row in before['releases']), 'fresh recovery intent/cache')
    names, counts, retry_names, retry_counts = EXPECTED[point]
    first, original = _stage(before, crashed, grant=grant, grant_id=grant_id, recipient=recipient,
                             fingerprint=fingerprint, dbc_now=dbc_now, names=names, attempts=counts)
    last, retried = _stage(before, after, grant=grant, grant_id=grant_id, recipient=recipient,
                           fingerprint=fingerprint, dbc_now=dbc_now, names=retry_names, attempts=retry_counts)
    immutable = set(original)-{'sendAttempts', 'completedAttempts'}
    require(all(original[key] == retried[key] for key in immutable), 'retry preserves original cache')
    require(after['events'][:len(crashed['events'])] == crashed['events'], 'retry preserves durable event prefix')
    require(last.check_response(response) == retried, 'retry response cache join')
    if point == 'after_send':
        require(crash_response is not None, 'after_send response required')
        require(first.check_response(crash_response) == original and crash_response == response, 'same full cached response after retry')
    else:
        require(crash_response is None, 'after_intent must have no response')
    return dict(ok=True, point=point, delivery='unknown', originalExpiry=grant['expiresAt'],
                sendAttempts=retry_counts[0], completedAttempts=retry_counts[1],
                responseSha256=hashlib.sha256(json.dumps(response, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                tokenDigest=retried['tokenDigest'], limitation='supplied-fact consistency; not power-loss durability or recipient delivery')
