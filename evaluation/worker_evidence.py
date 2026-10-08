"""Independent consistency checks for the public redacted worker-log export.

The caller collects raw output with the pinned owner command, retains its hash,
and supplies the independently bound deployment fingerprint. Checked cache/log
agreement is not proof of a native grant, delivery, durable storage or secrecy.
The runner must also join native grant, registered recipient and record facts.
"""
import copy
import re

from eth_utils import keccak
from jsonschema.exceptions import ValidationError

from evaluation.evm import _hex
from evaluation.schema import validate

IDENTITY = ('requestDigest', 'grantId', 'gid', 'dataId')
RELEASE_FIELDS = set(IDENTITY) | {'ciphertextDigest', 'recipientKeyHash', 'keyEpoch',
                                'tokenDigest', 'grantExpiresAt', 'createdAt', 'delivery',
                                'sendAttempts', 'completedAttempts'}
EVENT_FIELDS = set(IDENTITY) | {'type', 'timestamp'}


def _fields(value, expected):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('Worker evidence fields differ from the redacted export')


def _uint64(value):
    if (not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]{0,19}', value)
            or int(value) >= 2**64):
        raise ValueError('Noncanonical worker timestamp/count')
    return int(value)


def _identity(value):
    for key in IDENTITY:
        _hex(value[key], 20 if key == 'gid' else 32)


class WorkerLog:
    def __init__(self, payload, *, fingerprint):
        _fields(payload, {'schemaVersion', 'adapterMode', 'deploymentFingerprint',
                          'events', 'releases', 'counts', 'note'})
        if (not isinstance(fingerprint, str) or not re.fullmatch(r'[0-9a-f]{64}', fingerprint)
                or payload['deploymentFingerprint'] != fingerprint):
            raise ValueError('Worker deployment fingerprint differs')
        if payload['schemaVersion'] != 'hmbc-worker-log/v0' or payload['adapterMode'] != 'symbolic':
            raise ValueError('Worker evidence version/mode differs')
        if not isinstance(payload['note'], str) or not payload['note']:
            raise ValueError('Worker evidence note is absent')
        if not isinstance(payload['events'], list) or not isinstance(payload['releases'], list):
            raise ValueError('Worker events/releases must be arrays')
        _fields(payload['counts'], {'releaseIntentCount', 'releaseSentCount'})
        self._events = copy.deepcopy(payload['events'])
        self._releases = {}
        for offered in payload['releases']:
            _fields(offered, RELEASE_FIELDS)
            row = copy.deepcopy(offered)
            _identity(row)
            for key in ('ciphertextDigest', 'recipientKeyHash', 'tokenDigest'):
                _hex(row[key], 32)
            created, expires = _uint64(row['createdAt']), _uint64(row['grantExpiresAt'])
            if row['keyEpoch'] != '0' or row['delivery'] != 'unknown' or created >= expires:
                raise ValueError('Worker phase, delivery or original expiry differs')
            for key in ('sendAttempts', 'completedAttempts'):
                if type(row[key]) is not int or row[key] < 0:
                    raise ValueError('Worker attempt count must be a nonnegative integer')
            if row['completedAttempts'] > row['sendAttempts']:
                raise ValueError('Worker completed attempts exceed sends')
            if row['grantId'] in self._releases:
                raise ValueError('Duplicate worker grant cache')
            self._releases[row['grantId']] = row
        intents, sends, last = {}, {}, {}
        for event in self._events:
            _fields(event, EVENT_FIELDS)
            _identity(event)
            timestamp = _uint64(event['timestamp'])
            row = self._releases.get(event['grantId'])
            if row is None or any(event[key] != row[key] for key in IDENTITY):
                raise ValueError('Worker event/cache identity differs')
            grant = event['grantId']
            if timestamp < last.get(grant, int(row['createdAt'])):
                raise ValueError('Worker event precedes cache creation or prior attempt')
            last[grant] = timestamp
            if event['type'] == 'RELEASE_INTENT':
                if grant in intents or event['timestamp'] != row['createdAt']:
                    raise ValueError('Worker must have exactly one original intent per grant')
                intents[grant] = 1
            elif event['type'] == 'RELEASE_SENT':
                if grant not in intents:
                    raise ValueError('Worker send precedes intent')
                sends[grant] = sends.get(grant, 0)+1
            else:
                raise ValueError('Unknown worker event')
        for grant, row in self._releases.items():
            if grant not in intents or row['sendAttempts'] != sends.get(grant, 0):
                raise ValueError('Worker cache/event attempt counts differ')
        if (_uint64(payload['counts']['releaseIntentCount']) != len(intents)
                or _uint64(payload['counts']['releaseSentCount']) != sum(sends.values())):
            raise ValueError('Worker aggregate counts differ from events')

    def events_for(self, grant_id):
        _hex(grant_id, 32)
        return copy.deepcopy([e for e in self._events if e['grantId'] == grant_id])

    def check_response(self, response):
        try:
            validate('ReleaseResult', response)
        except ValidationError as error:
            raise ValueError('Malformed release response') from error
        row = self._releases.get(response['grantId'])
        if row is None:
            raise ValueError('Response has no worker cache evidence')
        keys = ('requestDigest', 'grantId', 'dataId', 'ciphertextDigest', 'recipientKeyHash', 'keyEpoch')
        digest = '0x'+keccak(_hex(response['responseEnvelope']['token'], 32)).hex()
        if any(response[key] != row[key] for key in keys) or digest != row['tokenDigest']:
            raise ValueError('Response differs from redacted worker cache commitments')
        return copy.deepcopy(row)
