"""Independent E01 identical-request replay checks for the reconstruction.

The caller must decode native receipts, count actual GrantIssued events, bind
the original successful transaction to the checked ACSC ABI/deployment/relay,
and validate the redacted worker export. This oracle consumes those observations;
it does not authenticate RPC facts, execute a service or establish a gate.
Expectations: SPEC4/E01 and frozen E01-nonce-replay scenarios. Paper profiles
deduplicate the accepted request reference; repaired-e also consumes (gid,nonce).
Changing the request reference is a different specification-gap experiment.
"""
from evaluation.access_artifacts import require
from evaluation.native import _quantity


def check_request_replay(*, profile, request_digest, gid, data_id, before, after,
                         original_transaction, replay_transaction, rejection_code,
                         success, receipt_logs, original_grants, replay_timestamp):
    """Check one mined identical ACSC replay before the first grant expires.

This recipe observes replay while PSC is FORWARDED, before worker release or
outcome reconciliation. It requires a prior allowed grant so deny-all cannot
satisfy the property. A later collector must supply fresh native evidence and
the complete execution plan must receive both exact owner ACKs before services.
    """
    require(profile in ('paper-strict', 'paper-minimal', 'repaired-e'), 'E reconstruction profile')
    require(type(original_grants) is int and original_grants == 1, 'one prior successful grant')
    request, grant = before['request'], before['grant']
    require(grant['exists'] is True and grant['allowed'] is True
            and grant['requestDigest'] == request_digest
            and request['gid'] == grant['gid'] == gid
            and request['dataId'] == grant['dataId'] == data_id,
            'positive grant matches the original request identity')
    require(request['status'] == '1' and int(request['requestLogId']) > 0
            and request['outcomeLogId'] == '0' and int(before['accessLogCount']) == 1,
            'one logged and forwarded request before release/outcome')
    require(before['nonceConsumed'] is (profile == 'repaired-e'), 'profile-specific consumed nonce')
    require(int(grant['issuedAt']) <= int(replay_timestamp)
            < min(int(grant['expiresAt']), int(request['expiresAt'])), 'replay before original expiry')
    require(set(before['logs']) == {'pbc', 'dbc'}
            and all(isinstance(rows, list) and rows for rows in before['logs'].values()),
            'both complete nonempty native contract histories')
    require(success is False and rejection_code == '8' and receipt_logs == [], 'mined REPLAY without receipt logs')
    require(original_transaction['hash'] != replay_transaction['hash']
            and all(original_transaction[key] == replay_transaction[key] for key in ('input', 'from', 'to'))
            and _quantity(replay_transaction['nonce']) > _quantity(original_transaction['nonce']),
            'identical application call and submitter with fresh transaction nonce')
    require(before == after, 'entire request/grant/nonce/access/worker/contract history unchanged')
    return dict(ok=True, error='REPLAY', delivery='unknown', nativeUnchanged=True,
                workerUnchanged=True, identicalCalldata=True,
                classification='REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SUPPORTED',
                limitation='checked reconstruction observations only; no worker retry, delivery, ABE, consensus or gate proof')
