"""Bind native receipt bytes and normalize only checked public ledger facts.

The caller must collect/hash raw RPC replies from the pinned local deployment.
These consistency checks are not a light-client proof or integration evidence by
themselves. Receipt order is the executor's causal order, never cross-chain
block-number sorting. Worker observations and denial-state checks are separate.
"""
import copy
import re

from evaluation.evm import _hex


def _quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x(?:0|[1-9a-f][0-9a-f]{0,63})', value):
        raise ValueError('Noncanonical RPC quantity')
    return int(value, 16)


def _required(value, names):
    if not isinstance(value, dict) or not set(names).issubset(value):
        raise ValueError('Required native evidence fields are absent')


class NativeReceipt:
    def __init__(self, *, receipt, transaction, block, chain_id):
        if not isinstance(chain_id, str) or not re.fullmatch(r'0|[1-9][0-9]*', chain_id):
            raise ValueError('Canonical deployment chain ID required')
        _required(receipt, ('status', 'transactionHash', 'blockHash', 'blockNumber', 'transactionIndex', 'gasUsed', 'logs'))
        _required(transaction, ('hash', 'chainId', 'blockHash', 'blockNumber', 'transactionIndex'))
        _required(block, ('hash', 'number', 'timestamp', 'transactions'))
        self.receipt = copy.deepcopy(receipt)
        self.chain_id = chain_id
        self.block_hash = block['hash']
        self.block_number = str(_quantity(block['number']))
        self.timestamp = str(_quantity(block['timestamp']))
        self.gas_used = str(_quantity(receipt['gasUsed']))
        _hex(self.block_hash, 32)
        _hex(receipt['transactionHash'], 32)
        status = _quantity(receipt['status'])
        if status not in (0, 1):
            raise ValueError('Invalid native receipt status')
        self.success = status == 1
        if transaction['hash'] != receipt['transactionHash'] or str(_quantity(transaction['chainId'])) != chain_id:
            raise ValueError('Native transaction/chain binding differs')
        for item in (receipt, transaction):
            if item['blockHash'] != self.block_hash or str(_quantity(item['blockNumber'])) != self.block_number:
                raise ValueError('Native block binding differs')
        if not isinstance(block['transactions'], list):
            raise ValueError('Block transaction identities are absent')
        index = _quantity(receipt['transactionIndex'])
        if index >= len(block['transactions']) or block['transactions'][index] != receipt['transactionHash']:
            raise ValueError('Native transaction is absent at its block index')
        if _quantity(transaction['transactionIndex']) != index:
            raise ValueError('Native transaction index differs')
        if not isinstance(receipt['logs'], list) or not self.success and receipt['logs']:
            raise ValueError('Reverted or malformed receipt cannot have success logs')
        previous = -1
        for log in receipt['logs']:
            _required(log, ('blockHash', 'blockNumber', 'transactionHash', 'transactionIndex', 'logIndex', 'removed', 'address'))
            if any(log[name] != receipt[name] for name in ('blockHash', 'blockNumber', 'transactionHash', 'transactionIndex')):
                raise ValueError('Native log identity differs from its receipt')
            if log['removed'] is not False:
                raise ValueError('Removed native log cannot be evidence')
            _hex(log['address'], 20)
            current = _quantity(log['logIndex'])
            if current <= previous:
                raise ValueError('Duplicate or unordered native log index')
            previous = current

    def decoded(self, contract):
        result = []
        for log in self.receipt['logs']:
            if log['address'] == contract.address:
                event = contract.decode_log(log)
                if event is not None:
                    result.append({**event, 'logIndex': str(_quantity(log['logIndex']))})
        return result

    def read_view(self, contract, method, arguments, reader):
        if reader is None:
            raise ValueError('Bound native view evidence is required')
        view = reader(contract, method, *arguments)
        _required(view, ('chainId', 'blockHash', 'blockNumber', 'address', 'calldata', 'returnData'))
        if (view['chainId'] != self.chain_id or view['blockHash'] != self.block_hash
                or view['blockNumber'] != self.block_number or view['address'] != contract.address
                or view['calldata'] != contract.calldata(method, *arguments)):
            raise ValueError('Native view identity/call differs from recorded block')
        return contract.decode_return(method, view['returnData'])

    def normalized(self, contract, role, *, view_reader=None):
        result = []
        for event in self.decoded(contract):
            name, fields = event['name'], event['fields']
            if role == 'KSSC' and name == 'GrantIssued':
                result.append({'type': 'DBC_AUTHORIZED', 'requestDigest': fields['requestDigest'],
                               'timestamp': self.timestamp, 'grantId': fields['grantId'], 'gid': fields['gid'],
                               'dataId': fields['dataId'], 'kssc': contract.address,
                               'destinationChainId': self.chain_id, 'recipientKeyHash': fields['recipientKeyHash'],
                               'keyEpoch': fields['keyEpoch']})
            elif role == 'PSC' and name in ('AccessForwarded', 'AccessDenied'):
                result.append({'type': 'PBC_DECIDED', 'requestDigest': fields['requestDigest'], 'timestamp': self.timestamp})
            elif role == 'PSC' and name in ('OutcomeRecorded', 'AttestedOutcomeRecorded'):
                record = self.read_view(contract, 'getRequest', [fields['requestDigest']], view_reader)[0]
                if record['status'] != '2' or record['outcomeLogId'] != fields['logId']:
                    raise ValueError('Native outcome/request state join differs')
                result.append({'type': 'OUTCOME_RECORDED', 'requestDigest': fields['requestDigest'],
                               'timestamp': self.timestamp, 'grantId': fields['grantId'],
                               'gid': record['gid'], 'dataId': record['dataId']})
            elif role == 'LSC' and name == 'LogRecorded' and fields['kind'] == '3':
                entry, details = self.read_view(contract, 'getLog', [fields['logId']], view_reader)
                if (any(entry[key] != fields[key] for key in ('kind', 'subject', 'detailsHash'))
                        or entry['timestamp'] != self.timestamp or entry['blockNumber'] != self.block_number
                        or details != fields['details']):
                    raise ValueError('Native request log/entry join differs')
                result.append({'type': 'REQUEST_LOGGED', 'requestDigest': fields['subject'], 'timestamp': entry['timestamp']})
        return result
