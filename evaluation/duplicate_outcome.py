"""Public ABI duplicate-outcome probe for the paper-derived reconstruction.

Exact-plan ACKs, live services and source stability belong to the caller. This
collector never establishes delivery, paper durability or an RQ gate by itself.
"""
import copy
import json
from pathlib import Path

from evaluation.access_artifacts import require
from evaluation.access_execution import _fingerprint
from evaluation.bootstrap import frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.native import _quantity
from evaluation.worker_evidence import WorkerLog


def check_duplicate_outcome(*, before, after, request_digest, rejection_code,
                            success, receipt_logs, original_outcomes, original_grants):
    require(original_outcomes == 1 and original_grants == 1, 'one positive outcome and grant before replay')
    request, grant = before['request'], before['grant']
    require(request['status'] == '2' and int(request['outcomeLogId']) > 0
            and int(request['requestLogId']) > 0 and grant['exists'] is True and grant['allowed'] is True
            and grant['requestDigest'] == request_digest
            and all(request[key] == grant[key] for key in ('gid', 'dataId')), 'prior native outcome/grant/request join')
    require(success is False and rejection_code == '8' and receipt_logs == [], 'mined REPLAY rejection without logs')
    require(set(before['logs']) == {'pbc', 'dbc'} and before == after,
            'replay preserves entire request/grant/worker and both contract histories')
    return dict(ok=True, error='REPLAY', delivery='unknown', workerUnchanged=True, nativeUnchanged=True,
                limitation='tested reconstruction duplicate reconciliation; not delivery, paper durability or an RQ gate')


def execute_duplicate_outcome(pbc, dbc, *, deployment, grant_id, method, arguments,
                              original_outcome, worker_snapshot, output):
    """Resubmit the exact successful public outcome call with a fresh tx nonce."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None,
                  scope='C-E2 duplicate outcome; not an RQ gate', delivery='unknown')

    def save(name, payload):
        (output/(name+'.json')).write_text(json.dumps(payload, indent=2)+'\n')

    def snapshot(name):
        grant = dbc.read('KSSC', 'grantDetails', grant_id)[0]
        worker = strict_json(worker_snapshot()); WorkerLog(worker, fingerprint=_fingerprint(deployment))
        payload = dict(grant=grant, request=pbc.read('PSC', 'getRequest', grant['requestDigest'])[0], worker=worker, logs={})
        for chain, label in ((pbc, 'pbc'), (dbc, 'dbc')):
            logs = chain.rpc.call('eth_getLogs', [dict(fromBlock='0x0', toBlock='latest',
                                                    address=[c.address for c in chain.contracts.values()])])
            require(isinstance(logs, list), 'public contract history array')
            payload['logs'][label] = copy.deepcopy(logs)
        save(name, payload)
        return payload

    def count(logs, contract, names):
        rows = [contract.decode_log(log) for log in logs if log['address'] == contract.address]
        return sum(row is not None and row['name'] in names for row in rows)

    try:
        frozen_validate('LedgerDeployment', deployment)
        expected_method = 'reportAttestedOutcome' if deployment['profile'] == 'repaired-e' else 'reportOutcome'
        require(method == expected_method and original_outcome.success is True, 'successful matching profile outcome')
        event_name = 'AttestedOutcomeRecorded' if method == 'reportAttestedOutcome' else 'OutcomeRecorded'
        outcome_rows = [e['fields'] for e in original_outcome.decoded(pbc.contracts['PSC']) if e['name'] == event_name]
        require(len(outcome_rows) == 1 and outcome_rows[0]['grantId'] == grant_id
                and outcome_rows[0]['requestDigest'] == arguments[0], 'original successful outcome identity')
        args = copy.deepcopy(arguments)
        original_calldata = pbc.contracts['PSC'].calldata(method, *args)
        original_hash = original_outcome.receipt['transactionHash']
        original_transaction = pbc.rpc.call('eth_getTransactionByHash', [original_hash])
        require(original_transaction is not None and original_transaction['hash'] == original_hash
                and original_transaction['input'] == original_calldata
                and original_transaction['to'] == pbc.contracts['PSC'].address
                and original_transaction['from'] == deployment['fixture']['relay']['address'], 'original mined public call binding')
        save('public-call', dict(method=method, calldata=original_calldata, originalTransaction=original_transaction))
        before = snapshot('before')
        outcomes = count(before['logs']['pbc'], pbc.contracts['PSC'], {'OutcomeRecorded', 'AttestedOutcomeRecorded'})
        grants = count(before['logs']['dbc'], dbc.contracts['KSSC'], {'GrantIssued'})
        require(before['request']['outcomeLogId'] == outcome_rows[0]['logId'], 'original outcome log join')
        # Check positive controls before submitting a deliberately failing call.
        require(outcomes == grants == 1 and before['request']['status'] == '2', 'completed positive control before replay')
        rejected = pbc.submit('relay', 'PSC', method, *args, expect_success=False)
        code = pbc.rejection_code(rejected)
        duplicate_hash = rejected.receipt['transactionHash']
        duplicate_transaction = pbc.rpc.call('eth_getTransactionByHash', [duplicate_hash])
        save('duplicate-transaction', duplicate_transaction)
        require(duplicate_hash != original_hash and duplicate_transaction is not None
                and duplicate_transaction['hash'] == duplicate_hash
                and all(duplicate_transaction[key] == original_transaction[key] for key in ('input', 'from', 'to'))
                and _quantity(duplicate_transaction['nonce']) > _quantity(original_transaction['nonce']),
                'same application call and relay with fresh transaction nonce')
        after = snapshot('after')
        proof = check_duplicate_outcome(before=before, after=after, request_digest=args[0], rejection_code=code,
                                        success=rejected.success, receipt_logs=rejected.receipt['logs'],
                                        original_outcomes=outcomes, original_grants=grants)
        result.update(proof, identicalCalldata=True, rejectionCode=code,
                      duplicateTransactionHash=rejected.receipt['transactionHash'],
                      classification='REPAIR_SUPPORTED' if deployment['profile'] == 'repaired-e' else 'SUPPORTED')
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); save('result', result)
