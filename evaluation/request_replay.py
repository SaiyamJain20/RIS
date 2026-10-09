"""Public ACSC identical-request replay collector; live plan ACKs are mandatory.

The coordinator owns source stability, native executors, services and controls.
No worker operation, clock change, crash or new request reference occurs here.
"""
import copy
import json
from pathlib import Path

from evaluation.access_artifacts import require
from evaluation.access_execution import _fingerprint
from evaluation.bootstrap import frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.oracles.replay import check_request_replay
from evaluation.worker_evidence import WorkerLog


def execute_request_replay(pbc, dbc, *, deployment, request, grant_id, method,
                           arguments, original_grant, worker_snapshot, output):
    """Replay the accepted ACSC call before release and preserve all observations."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None,
                  scope='C-E2 identical accepted request; not an RQ gate', delivery='unknown')

    def save(name, payload):
        (output/(name+'.json')).write_text(json.dumps(payload, indent=2)+'\n')

    def snapshot(name):
        # All roles preserve complete history coverage. Views and logs on each
        # chain share an explicit historical block; anchors are evidence sidecars
        # because before/after block numbers differ across the mined replay.
        with dbc.read_group(tuple(dbc.contracts)) as domain:
            grant = domain.read('KSSC', 'grantDetails', grant_id)[0]
            nonce = domain.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'])[0]
            count = domain.read('ACSC', 'accessLogCount')[0]
            domain_logs = domain.logs()
        with pbc.read_group(tuple(pbc.contracts)) as proxy:
            request_state = proxy.read('PSC', 'getRequest', grant['requestDigest'])[0]
            proxy_logs = proxy.logs()
        worker = strict_json(worker_snapshot()); WorkerLog(worker, fingerprint=_fingerprint(deployment))
        payload = dict(grant=grant, request=request_state, worker=worker,
                       nonceConsumed=nonce, accessLogCount=count,
                       logs=dict(pbc=proxy_logs, dbc=domain_logs))
        save(name+'-blocks', dict(pbc=proxy.block, dbc=domain.block))
        save(name, payload); return payload

    try:
        frozen_validate('LedgerDeployment', deployment)
        require(method == ('consumeDecision' if deployment['profile'] == 'repaired-e' else 'policyEnf')
                and original_grant.success is True, 'matching successful ACSC grant call')
        grant_rows = [e['fields'] for e in original_grant.decoded(dbc.contracts['KSSC']) if e['name'] == 'GrantIssued']
        require(len(grant_rows) == 1 and grant_rows[0]['grantId'] == grant_id
                and grant_rows[0]['gid'] == request['gid'] and grant_rows[0]['dataId'] == request['dataId'],
                'original successful grant identity')
        args = copy.deepcopy(arguments)
        original_hash = original_grant.receipt['transactionHash']
        original = dbc.rpc.call('eth_getTransactionByHash', [original_hash])
        require(original is not None and original['hash'] == original_hash
                and original['input'] == dbc.contracts['ACSC'].calldata(method, *args)
                and original['to'] == dbc.contracts['ACSC'].address
                and original['from'] == deployment['fixture']['relay']['address'], 'original mined ACSC call binding')
        save('public-call', dict(method=method, arguments=args, originalTransaction=original))
        before = snapshot('before')
        rows = [dbc.contracts['KSSC'].decode_log(log) for log in before['logs']['dbc']
                if log['address'] == dbc.contracts['KSSC'].address]
        grants = sum(row is not None and row['name'] == 'GrantIssued' for row in rows)
        require(grants == 1 and before['grant']['requestDigest'] == grant_rows[0]['requestDigest']
                and before['grant']['exists'] is True and before['grant']['allowed'] is True,
                'one positive grant before replay')
        rejected = dbc.submit('relay', 'ACSC', method, *args, expect_success=False)
        code = dbc.rejection_code(rejected)
        replay_hash = rejected.receipt['transactionHash']
        replay = dbc.rpc.call('eth_getTransactionByHash', [replay_hash]); save('replay-transaction', replay)
        require(replay is not None and replay['hash'] == replay_hash, 'mined replay transaction identity')
        after = snapshot('after')
        proof = check_request_replay(profile=deployment['profile'], request_digest=grant_rows[0]['requestDigest'],
                                     gid=request['gid'], data_id=request['dataId'], before=before, after=after,
                                     original_transaction=original, replay_transaction=replay, rejection_code=code,
                                     success=rejected.success, receipt_logs=rejected.receipt['logs'],
                                     original_grants=grants, replay_timestamp=rejected.timestamp)
        result.update(proof, rejectionCode=code, replayTransactionHash=replay_hash)
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); save('result', result)
