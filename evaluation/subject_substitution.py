"""Public pre-release subject stress collector for the HMBC reconstruction.

The caller verifies historical credentials/policy/checkpoint and owns stable
public executors, fresh deployment/state, controls and full execution-plan ACKs.
This stage changes only gid and stops before release. Its result alone does not
complete the catalog case or establish an original-paper vulnerability.
"""
import copy
import json
from pathlib import Path

from evaluation.access_artifacts import require, verify_prepared, _witness
from evaluation.access_execution import _fingerprint
from evaluation.bootstrap import frozen_validate, strict_json
from evaluation.manifests import now
from evaluation.oracles.subject import check_subject_substitution
from evaluation.vectors import credential_digest
from evaluation.worker_evidence import WorkerLog


def execute_subject_substitution(pbc, dbc, *, deployment, request, prepared,
                                 original_native, original_bundle, forwarded, records, decision,
                                 target_gid, grant_id, worker_snapshot, output):
    """Collect authenticated calls and full block-anchored pre/post histories.

    No worker release, completion, outcome, clock mutation or retry occurs here.
    Raw receipts, view returns and RPC commands remain in the public executors.
    """
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    result = dict(startedAt=now(), endedAt=None, ok=False, failure=None,
                  scope='C-E2 subject pre-release stage; full case and gate incomplete', delivery='unknown')

    def save(name, data):
        (output/(name+'.json')).write_text(json.dumps(data, indent=2)+'\n')

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

    def decode(chain, logs):
        rows = []
        for log in logs:
            contract = next((c for c in chain.contracts.values() if c.address == log['address']), None)
            require(contract is not None, 'subject full history contract')
            row = contract.decode_log(log)
            require(row is not None, 'subject full history decoded event')
            rows.append(dict(name=row['name'], fields=row['fields']))
        return rows

    def snapshot(name):
        with dbc.read_group(tuple(dbc.contracts)) as domain:
            grant = domain.read('KSSC', 'grantDetails', grant_id)[0]
            nonce_alice = domain.read('KSSC', 'nonceConsumed', request['gid'], request['nonce'])[0]
            nonce_bob = domain.read('KSSC', 'nonceConsumed', target_gid, request['nonce'])[0]
            count = domain.read('ACSC', 'accessLogCount')[0]
            logs_dbc = decode(dbc, domain.logs())
        with pbc.read_group(tuple(pbc.contracts)) as proxy:
            state = proxy.read('PSC', 'getRequest', digest)[0]
            require(proxy.read('RSC', 'isRegistered', target_gid) == [True], 'registered substituted subject')
            logs_pbc = decode(pbc, proxy.logs())
        worker = strict_json(worker_snapshot()); WorkerLog(worker, fingerprint=_fingerprint(deployment))
        payload = dict(grant=grant, request=state, nonceAlice=nonce_alice, nonceBob=nonce_bob,
                       accessLogCount=count, logs=dict(pbc=logs_pbc, dbc=logs_dbc), worker=worker)
        save(name+'-blocks', dict(pbc=proxy.block, dbc=domain.block)); save(name, payload)
        return payload

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
        save('public-call', dict(originalTransaction=original_tx, originalRequest=request,
                                prepared=prepared, method=method, arguments=args, originalDecision=decision))
        before = snapshot('before')
        require(before['grant']['exists'] is False and before['accessLogCount'] == '0'
                and before['nonceAlice'] is False and before['nonceBob'] is False,
                'fresh stress grant/count/nonces before submission')
        native = dbc.submit('relay', 'ACSC', method, *args, expect_success=not repaired)
        tx = mined(dbc, native, 'ACSC', method, args); save('substituted-transaction', tx)
        code = dbc.rejection_code(native) if repaired else None
        events = decode(dbc, native.receipt['logs'])
        after = snapshot('after')
        proof = check_subject_substitution(profile=deployment['profile'], original_request=request,
            request_digest=digest, forwarded=forwarded, records=records, certificate=certificate,
            submitted_arguments=args, target_gid=target_gid, grant_id=grant_id,
            credential_digest=credential_digest(records), relay=deployment['fixture']['relay']['address'],
            before=before, after=after, success=native.success, rejection_code=code,
            receipt_events=events, timestamp=native.timestamp)
        result.update(proof, transactionHash=native.receipt['transactionHash'], rejectionCode=code)
        return result
    except BaseException as error:
        result['failure'] = type(error).__name__
        raise
    finally:
        result['endedAt'] = now(); save('result', result)
