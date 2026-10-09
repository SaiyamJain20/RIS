"""Independent, hash-bound public ABI codec for the C-E1 collector/runner.

This decodes supplied native bytes; it does not prove they came from a chain.
Receipt/block/transaction binding and native-evidence joins are separate duties.
No ledger or protocol implementation is imported.
"""
import hashlib
import json
import re
from pathlib import Path

from eth_abi import decode, encode
from eth_abi.exceptions import DecodingError, EncodingError
from eth_utils import keccak



def _type(spec):
    value = spec['type']
    if value.startswith('tuple'):
        return '('+','.join(_type(x) for x in spec['components'])+')'+value[5:]
    return value


def _array(spec):
    found = re.fullmatch(r'(.*)\[([0-9]*)\]', spec['type'])
    return ({**spec, 'type': found[1]}, int(found[2]) if found[2] else None) if found else None


def _hex(value, size=None):
    if not isinstance(value, str) or not re.fullmatch(r'0x(?:[0-9a-f]{2})*', value):
        raise ValueError('Noncanonical ABI hex bytes')
    raw = bytes.fromhex(value[2:])
    if size is not None and len(raw) != size:
        raise ValueError('Wrong ABI byte width')
    return raw


def _internal(spec, value):
    array = _array(spec)
    if array:
        item, count = array
        if not isinstance(value, list) or count is not None and len(value) != count:
            raise ValueError('Wrong ABI array shape')
        return [_internal(item, child) for child in value]
    kind = spec['type']
    if kind == 'tuple':
        names = [x['name'] for x in spec['components']]
        if not isinstance(value, dict) or set(value) != set(names):
            raise ValueError('Wrong ABI tuple fields')
        return tuple(_internal(x, value[x['name']]) for x in spec['components'])
    if kind.startswith('uint'):
        if not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]*', value):
            raise ValueError('Noncanonical ABI unsigned integer')
        result = int(value)
        if result >= 2**int(kind[4:] or '256'):
            raise ValueError('ABI unsigned integer out of range')
        return result
    if kind == 'address':
        _hex(value, 20)
        return value
    if kind.startswith('bytes'):
        return _hex(value, int(kind[5:]) if kind[5:] else None)
    if kind == 'bool':
        if type(value) is not bool:
            raise ValueError('ABI boolean required')
        return value
    raise ValueError('Unsupported E1 ABI input type: '+kind)


def _external(spec, value):
    array = _array(spec)
    if array:
        return [_external(array[0], child) for child in value]
    if spec['type'] == 'tuple':
        return {x['name']: _external(x, child) for x, child in zip(spec['components'], value, strict=True)}
    if spec['type'].startswith('uint'):
        return str(value)
    if spec['type'].startswith('bytes'):
        return '0x'+value.hex()
    return value


def _decode(specs, raw):
    types = [_type(x) for x in specs]
    try:
        values = decode(types, raw, strict=True)
        if encode(types, values) != raw:
            raise ValueError('Noncanonical or trailing ABI data')
    except (DecodingError, EncodingError) as error:
        raise ValueError('Invalid ABI data') from error
    return [_external(x, value) for x, value in zip(specs, values, strict=True)]


class AbiContract:
    def __init__(self, path, address, expected_sha256):
        self.path = Path(path)
        raw = self.path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError('ABI hash differs from reviewed pin')
        _hex(address, 20)
        self.address = address
        self.abi_sha256 = expected_sha256
        self.abi = json.loads(raw)
        self._events = {}
        for item in self.abi:
            if item['type'] == 'event':
                if item.get('anonymous'):
                    raise ValueError('Anonymous events are unsupported in E1')
                topic = '0x'+keccak(text=self._signature(item)).hex()
                if topic in self._events:
                    raise ValueError('Ambiguous ABI event')
                self._events[topic] = item

    @staticmethod
    def _signature(item):
        return item['name']+'('+','.join(_type(x) for x in item['inputs'])+')'

    def _function(self, name):
        matches = [x for x in self.abi if x['type'] == 'function' and x['name'] == name]
        if len(matches) != 1:
            raise ValueError('Unknown or ambiguous ABI method')
        return matches[0]

    def calldata(self, name, *values):
        function = self._function(name)
        specs = function['inputs']
        if len(specs) != len(values):
            raise ValueError('Wrong ABI argument count')
        arguments = [_internal(x, value) for x, value in zip(specs, values, strict=True)]
        selector = keccak(text=self._signature(function))[:4]
        try:
            return '0x'+(selector+encode([_type(x) for x in specs], arguments)).hex()
        except EncodingError as error:
            raise ValueError('Invalid ABI arguments') from error

    def decode_return(self, name, data):
        return _decode(self._function(name)['outputs'], _hex(data))

    def decode_log(self, log):
        if log.get('address') != self.address or log.get('removed') is not False:
            raise ValueError('Native event emitter/removed flag does not match')
        topics = log.get('topics')
        if not isinstance(topics, list) or not topics:
            raise ValueError('Native event topics are absent')
        for topic in topics:
            _hex(topic, 32)
        event = self._events.get(topics[0])
        if event is None:
            return None
        indexed = [x for x in event['inputs'] if x['indexed']]
        ordinary = [x for x in event['inputs'] if not x['indexed']]
        if len(topics) != 1+len(indexed):
            raise ValueError('Wrong native event topic count')
        values = {}
        for spec, topic in zip(indexed, topics[1:], strict=True):
            if spec['type'] in ('tuple', 'bytes', 'string') or _array(spec):
                raise ValueError('Indexed dynamic values cannot be decoded')
            values[spec['name']] = _decode([spec], _hex(topic, 32))[0]
        data = _decode(ordinary, _hex(log.get('data')))
        values.update({spec['name']: value for spec, value in zip(ordinary, data, strict=True)})
        return {'name': event['name'], 'fields': values}
