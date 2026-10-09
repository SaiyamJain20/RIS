"""Independent original-expiry refusal checks for the C-E2 recovery slice.

Synthetic-only unless composed with exact ACKed live services. No paper
durability, delivery, ABE, power-loss or provider-integrity claim follows.
"""
import hashlib
import json
from pathlib import Path

from evaluation.access_artifacts import require
from evaluation.access_execution import _clock, _fingerprint
from evaluation.bootstrap import frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.worker_evidence import WorkerLog


def check_expired_retry(*, before, after, response, grant_before, grant_after,
                        pending_before, pending_after, grant_id, fingerprint,
                        dbc_now, logs_before, logs_after):
    frozen_validate('ReleaseResponse', response)
    require(response['ok'] is False and response['error']['code'] == 'EXPIRED', 'original-expiry refusal')
    require(grant_before['exists'] is True and grant_before['allowed'] is True
            and int(dbc_now) >= int(grant_before['expiresAt']), 'probe at or after original expiry')
    checked = WorkerLog(before, fingerprint=fingerprint)
    WorkerLog(after, fingerprint=fingerprint)
    rows = [row for row in before['releases'] if row['grantId'] == grant_id]
    require(len(rows) == 1 and rows[0]['grantExpiresAt'] == grant_before['expiresAt']
            and all(rows[0][key] == grant_before[key] for key in ('requestDigest', 'gid', 'dataId', 'keyEpoch'))
            and rows[0]['completedAttempts'] == 1 and bool(checked.events_for(grant_id)), 'previously recovered original cache')
    require(after == before, 'expired refusal preserves entire worker log/cache/attempts')
    require(grant_after == grant_before and pending_after == pending_before, 'expired refusal preserves native permission/outcome')
    require(set(logs_before) == set(logs_after) == {'pbc', 'dbc'}
            and logs_after == logs_before, 'expired refusal creates no native event')
    return dict(ok=True, error='EXPIRED', originalExpiry=grant_before['expiresAt'],
                observedDbcTime=dbc_now, delivery='unknown', workerUnchanged=True, nativeUnchanged=True,
                limitation='tested reconstruction refusal only; not paper durability, recipient delivery or an RQ gate')


def execute_expired_retry(pbc, dbc, adapter, *, deployment, grant_id, worker_snapshot, output):
    """Reuse the recovered grant on the production adapter after DBC time advances.

    Caller owns exact-plan ACKs, live chains, source brackets and the adapter.
    Empty block mining is an explicit synthetic schedule, not an expiry extension.
    Probe follows successful recovery/outcome, before the fresh Bob denial control.
    """
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None, delivery='unknown',
                  scope='C-E2 expired cached retry; not an RQ gate')
    fingerprint = _fingerprint(deployment)

    def save(name, payload):
        (output/(name+'.json')).write_text(json.dumps(payload, indent=2)+'\n')

    def worker(name):
        payload = strict_json(worker_snapshot())
        WorkerLog(payload, fingerprint=fingerprint)
        save(name, payload)
        return payload

    def native(name):
        payload = dict(grant=dbc.read('KSSC', 'grantDetails', grant_id)[0])
        payload['pending'] = pbc.read('PSC', 'getRequest', payload['grant']['requestDigest'])[0]
        payload['logs'] = {}
        for chain, label in ((pbc, 'pbc'), (dbc, 'dbc')):
            payload['logs'][label] = chain.rpc.call('eth_getLogs', [dict(fromBlock='0x0', toBlock='latest',
                                                        address=[c.address for c in chain.contracts.values()])])
            require(isinstance(payload['logs'][label], list), 'native log array')
        save(name, payload)
        return payload

    try:
        frozen_validate('LedgerDeployment', deployment)
        request = dict(schemaVersion='v1', operation='release', input=dict(grantId=grant_id), deploymentManifest=deployment)
        frozen_validate('AdapterRequest', request)
        original = native('native-before'); before = worker('worker-before')
        expiry = int(original['grant']['expiresAt'])
        latest = dbc.latest_block()
        target = max(int(latest['timestamp'], 16)+1, expiry)
        result.update(grantId=grant_id, originalExpiry=str(expiry), targetDbcTime=str(target))
        dbc.rpc.call('evm_setNextBlockTimestamp', [target]); dbc.rpc.call('evm_mine')
        require(int(dbc.latest_block()['timestamp'], 16) >= expiry and int(_clock(dbc)) >= expiry,
                'mined and pending DBC clock expired')
        result['beforeProbeDbcTime'] = _clock(dbc)
        reply = adapter.exchange(request)
        result['responseSha256'] = hashlib.sha256(json.dumps(reply, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        frozen_validate('ReleaseResponse', reply)
        after = worker('worker-after'); final = native('native-after')
        proof = check_expired_retry(before=before, after=after, response=reply, grant_before=original['grant'],
                                   grant_after=final['grant'], pending_before=original['pending'], pending_after=final['pending'],
                                   logs_before=original['logs'], logs_after=final['logs'], grant_id=grant_id,
                                   fingerprint=fingerprint, dbc_now=_clock(dbc))
        # Refusal messages/capabilities are not public evidence. Record code and digest.
        result.update(proof)
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); save('result', result)
