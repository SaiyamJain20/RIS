"""Compose the accepted crash transport with public ABI and redacted recovery.

The caller owns exact ACKed snapshots/services, restart command, same state and
source brackets. This adapter wrapper neither starts chains nor closes an RQ gate.
"""
import json
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak

from evaluation.access_artifacts import require
from evaluation.access_execution import _clock, _fingerprint
from evaluation.bootstrap import frozen_validate, strict_json
from evaluation.evm import _hex
from evaluation.manifests import now
from evaluation.recovery import EXPECTED, _stage, check_recovery
from evaluation.worker_evidence import WorkerLog


class RecoveryAdapter:
    def __init__(self, process, *, restart, point, pbc, dbc, deployment, worker_snapshot, output):
        require(point in EXPECTED and callable(restart), 'named recovery point/restart')
        self.process = process; self.restart = restart; self.point = point
        self.pbc = pbc; self.dbc = dbc; self.deployment = deployment
        self.worker_snapshot = worker_snapshot; self.fingerprint = _fingerprint(deployment)
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=False)
        self.record = dict(startedAt=now(), endedAt=None, ok=False, failure=None, point=point,
                           delivery='unknown', scope='logical process crash/retry; not an RQ gate')
        self.used = False

    def _worker(self, name):
        raw = self.worker_snapshot(); payload = strict_json(raw)
        WorkerLog(payload, fingerprint=self.fingerprint)  # Refuse raw secrets before writing.
        (self.output/(name+'.json')).write_bytes(raw)
        return payload

    def exchange(self, request):
        if request.get('operation') != 'release' or self.used:
            return self.process.exchange(request)
        frozen_validate('AdapterRequest', request)
        require(request['deploymentManifest'] == self.deployment, 'recovery instance deployment')
        self.used = True
        try:
            gid = request['input']['grantId']
            grant = self.dbc.read('KSSC', 'grantDetails', gid)[0]
            require(grant['exists'] is True and grant['allowed'] is True, 'recovery native grant')
            expected_id = '0x'+keccak(encode(['bytes32', 'address', 'uint256'],
                               [_hex(grant['requestDigest'], 32), self.dbc.contracts['KSSC'].address, int(self.dbc.chain_id)])).hex()
            require(expected_id == gid, 'recovery grant identity')
            require(self.pbc.read('RSC', 'isRegistered', grant['gid']) == [True], 'registered recovery subject')
            recipient = self.pbc.read('RSC', 'recipientKeyHash', grant['gid'])[0]
            pending = self.pbc.read('PSC', 'getRequest', grant['requestDigest'])[0]
            require(pending['status'] == '1' and int(_clock(self.dbc)) < int(grant['expiresAt']), 'recovery pending/unexpired permission')
            before = self._worker('worker-before-crash')

            def validate_reply(reply):
                frozen_validate('ReleaseResponse', reply)
                require(reply['ok'] is True, 'crash/retry response success')
                result = reply['result']
                require(all(result[k] == grant[k] for k in ('requestDigest', 'dataId', 'keyEpoch'))
                        and result['grantId'] == gid and result['recipientKeyHash'] == recipient, 'crash/retry native response')

            crash_reply = self.process.exchange_crash(request, point=self.point, validate_response=validate_reply)
            require(self.process.returncode == 86, 'natural crash exit86')
            crashed = self._worker('worker-after-crash')
            names, attempts, _, _ = EXPECTED[self.point]
            _stage(before, crashed, grant=grant, grant_id=gid, recipient=recipient, fingerprint=self.fingerprint,
                   dbc_now=_clock(self.dbc), names=names, attempts=attempts)
            # Native permission and expiry cannot change through a worker retry.
            require(self.dbc.read('KSSC', 'grantDetails', gid) == [grant], 'crash preserves native permission')
            self.process = self.restart()
            self.record['restartedAt'] = now()
            require(int(_clock(self.dbc)) < int(grant['expiresAt']), 'retry before original expiry')
            reply = self.process.exchange(request); validate_reply(reply)
            after = self._worker('worker-after-retry')
            proof = check_recovery(before=before, crashed=crashed, after=after, response=reply['result'],
                                   crash_response=None if crash_reply is None else crash_reply['result'], grant=grant,
                                   grant_id=gid, recipient=recipient, point=self.point, fingerprint=self.fingerprint, dbc_now=_clock(self.dbc))
            require(self.dbc.read('KSSC', 'grantDetails', gid) == [grant]
                    and self.pbc.read('PSC', 'getRequest', grant['requestDigest']) == [pending], 'recovery does not issue grant or outcome')
            self.record.update(proof)
            return reply
        except BaseException as error:
            self.record['failure'] = type(error).__name__
            raise
        finally:
            self.record['endedAt'] = now()
            (self.output/'result.json').write_text(json.dumps(self.record, indent=2)+'\n')
