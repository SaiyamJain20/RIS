"""Public-ABI transaction/view executor for local C-E1 integration.

Uses only runner-owned TEST-ONLY relay/CA-admin keys. Native receipts must match
the signed call as well as their block/chain. This establishes consistency of
the supplied RPC evidence, not a light-client proof or Byzantine consensus.
"""
import copy
from contextlib import contextmanager
import json
import math
from pathlib import Path
import time

from eth_abi import decode, encode
from eth_account import Account
from eth_utils import keccak, to_checksum_address

from evaluation.evm import _hex
from evaluation.manifests import now, sha256
from evaluation.native import NativeReceipt, _quantity


def _owned_signer(role):
    if role not in ('relay', 'H1-ca-admin', 'H2-ca-admin', 'H3-ca-admin', 'H4-ca-admin'):
        raise ValueError('Runner may sign only as relay or TEST-ONLY CA-admin')
    return Account.from_key(keccak(text='hmbc-e0-synthetic-key:'+role))


class PublicChain:
    def __init__(self, rpc, *, chain_id, contracts, output, timeout=10.0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Transaction wait budget must be finite and positive')
        if not isinstance(chain_id, str) or not chain_id.isdecimal() or str(int(chain_id)) != chain_id:
            raise ValueError('Canonical chain ID required')
        self.rpc = rpc
        self.chain_id = chain_id
        self.contracts = dict(contracts)
        self.output = Path(output)
        self.timeout = timeout
        self.transactions = []
        self.views = []
        self._group_active = False
        self.output.mkdir(parents=True, exist_ok=False)
        self._save()

    def _save(self):
        for name, rows in (('transactions', self.transactions), ('views', self.views)):
            (self.output/(name+'.json')).write_text(json.dumps(rows, indent=2)+'\n')

    def _contract(self, role):
        if role not in self.contracts:
            raise ValueError('Contract is outside selected public ABI inventory')
        contract = self.contracts[role]
        if sha256(contract.path) != contract.abi_sha256:
            raise ValueError('Public ABI changed before execution')
        return contract

    def _check_chain(self):
        if str(_quantity(self.rpc.call('eth_chainId'))) != self.chain_id:
            raise ValueError('RPC chain differs from deployment')

    def latest_block(self):
        self._check_chain()
        return self.rpc.call('eth_getBlockByNumber', ['latest', False])

    def observe(self, role, method, *arguments, block=None):
        contract = self._contract(role)
        calldata = contract.calldata(method, *arguments)
        self._check_chain()
        block = self.latest_block() if block is None else block
        _hex(block['hash'], 32)
        number = hex(_quantity(block['number']))
        actual = self.rpc.call('eth_getBlockByNumber', [number, False])
        if actual['hash'] != block['hash'] or actual['number'] != number:
            raise ValueError('Historical block identity changed before view')
        raw = self.rpc.call('eth_call', [{'to': contract.address, 'data': calldata}, number])
        contract.decode_return(method, raw)
        after = self.rpc.call('eth_getBlockByNumber', [number, False])
        if after['hash'] != block['hash'] or after['number'] != number:
            raise ValueError('Historical block identity changed during view')
        self._contract(role)
        row = {'chainId': self.chain_id, 'blockHash': block['hash'],
               'blockNumber': str(_quantity(number)), 'address': contract.address,
               'calldata': calldata, 'returnData': raw, 'method': method, 'observedAt': now()}
        self.views.append(row)
        self._save()
        return copy.deepcopy(row)

    def read(self, role, method, *arguments, block=None):
        row = self.observe(role, method, *arguments, block=block)
        return self._contract(role).decode_return(method, row['returnData'])

    @contextmanager
    def read_group(self, roles):
        """At most 16 reads/log queries at one block, with identity bracketing.

        Individual ABI-bound views are published only if the whole group passes.
        This checks RPC consistency under the existing safe-ledger assumption;
        it cannot detect a transient reorg restored between boundary checks.
        """
        if self._group_active:
            raise ValueError('Public read groups cannot nest on one chain')
        roles = tuple(roles)
        if not roles or len(set(roles)) != len(roles):
            raise ValueError('Explicit distinct public ABI roles required')
        self._group_active = True
        group = None
        try:
            deadline = time.monotonic()+self.timeout
            contracts = {role: self._contract(role) for role in roles}
            self._check_chain()
            block = self.rpc.call('eth_getBlockByNumber', ['latest', False])
            group = _PublicReadGroup(self, contracts, block, deadline)
            group.check_block('before')
            yield group
            group.check_budget()
            group.check_block('during')
            self._check_chain()
            for role, contract in contracts.items():
                if self._contract(role) is not contract:
                    raise ValueError('Selected public ABI inventory changed during group')
            group.check_budget()
            self.views.extend(group.rows)
            self._save()
        finally:
            if group is not None:
                group.active = False
            self._group_active = False

    def submit(self, signer_role, role, method, *arguments, expect_success=True, gas_limit='3000000'):
        signer = _owned_signer(signer_role)
        contract = self._contract(role)
        calldata = contract.calldata(method, *arguments)
        if not isinstance(gas_limit, str) or not gas_limit.isdecimal() or str(int(gas_limit)) != gas_limit or not 21000 <= int(gas_limit) <= 30000000:
            raise ValueError('Explicit bounded canonical gas limit required')
        if type(expect_success) is not bool:
            raise ValueError('Expected native status must be explicit')
        self._check_chain()
        sender = signer.address.lower()
        nonce = _quantity(self.rpc.call('eth_getTransactionCount', [sender, 'pending']))
        price = _quantity(self.rpc.call('eth_gasPrice'))
        tx = {'chainId': int(self.chain_id), 'nonce': nonce, 'gasPrice': price,
              'gas': int(gas_limit), 'to': to_checksum_address(contract.address), 'value': 0, 'data': calldata}
        signed = signer.sign_transaction(tx)
        raw = '0x'+signed.raw_transaction.hex()
        expected_hash = '0x'+keccak(signed.raw_transaction).hex()
        row = {'startedAt': now(), 'endedAt': None, 'chainId': self.chain_id, 'signerRole': signer_role,
               'sender': sender, 'contractRole': role, 'method': method, 'address': contract.address,
               'calldata': calldata, 'nonce': str(nonce), 'gasLimit': gas_limit,
               'expectedSuccess': expect_success, 'transactionHash': expected_hash,
               'receipt': None, 'failure': None}
        self.transactions.append(row)
        self._save()
        try:
            reported_hash = self.rpc.call('eth_sendRawTransaction', [raw])
            if reported_hash != expected_hash:
                raise ValueError('Broadcast hash differs from locally signed transaction')
            deadline = time.monotonic()+self.timeout
            while True:
                receipt = self.rpc.call('eth_getTransactionReceipt', [expected_hash])
                if receipt is not None:
                    break
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Local transaction receipt wait timed out')
                time.sleep(min(0.05, remaining))
            row['receipt'] = receipt
            if receipt['transactionHash'] != expected_hash:
                raise ValueError('Receipt is for a different locally signed transaction')
            transaction = self.rpc.call('eth_getTransactionByHash', [expected_hash])
            block = self.rpc.call('eth_getBlockByNumber', [receipt['blockNumber'], False])
            self._check_chain()
            native = NativeReceipt(receipt=receipt, transaction=transaction, block=block, chain_id=self.chain_id)
            if (transaction['from'] != sender or transaction['to'] != contract.address
                    or transaction['input'] != calldata or _quantity(transaction['nonce']) != nonce
                    or _quantity(transaction['value']) != 0 or _quantity(transaction['gas']) != int(gas_limit)):
                raise ValueError('Native transaction differs from submitted sender/call')
            self._contract(role)
            row['transaction'] = transaction
            row['block'] = block
            if native.success != expect_success:
                raise ValueError('Native transaction status differs from expected control')
            return native
        except Exception as error:
            row['failure'] = type(error).__name__
            raise
        finally:
            row['endedAt'] = now()
            self._save()

    def rejection_code(self, native):
        """Decode the actual mined Rejected(uint8); OOG/generic failures refuse."""
        rows = [row for row in self.transactions if row['receipt'] == native.receipt and row['failure'] is None]
        if native.success or native.chain_id != self.chain_id or len(rows) != 1:
            raise ValueError('Owned mined rejection receipt required')
        trace = self.rpc.call('debug_traceTransaction', [native.receipt['transactionHash'],
                                                       {'disableStorage': True, 'disableMemory': True, 'disableStack': True}])
        rows[0]['rejectionTrace'] = trace
        self._save()
        raw = trace.get('returnValue')
        if trace.get('failed') is not True or not isinstance(raw, str):
            raise ValueError('Mined trace does not establish a contract rejection')
        raw = _hex(raw if raw.startswith('0x') else '0x'+raw)
        if len(raw) != 36 or raw[:4] != keccak(text='Rejected(uint8)')[:4]:
            raise ValueError('Mined failure is not the public Rejected(uint8) error')
        code = decode(['uint8'], raw[4:])[0]
        if not 1 <= code <= 21 or encode(['uint8'], [code]) != raw[4:]:
            raise ValueError('Unknown or malformed public rejection code')
        return str(code)


class _PublicReadGroup:
    """Short-lived public view reader; callers use PublicChain.read_group."""
    def __init__(self, chain, contracts, block, deadline):
        self.chain = chain
        self.contracts = contracts
        self.block = copy.deepcopy(block)
        _hex(self.block['hash'], 32)
        self.number = hex(_quantity(self.block['number']))
        self.deadline = deadline
        self.queries = 0
        self.rows = []
        self.active = True

    def check_budget(self):
        if not self.active:
            raise ValueError('Public read group is closed')
        if time.monotonic() >= self.deadline:
            raise TimeoutError('Public read group budget exhausted')

    def check_block(self, phase):
        self.check_budget()
        actual = self.chain.rpc.call('eth_getBlockByNumber', [self.number, False])
        if actual['hash'] != self.block['hash'] or actual['number'] != self.number:
            raise ValueError('Historical block identity changed '+phase+' group')
        self.check_budget()

    def _query(self, method, params):
        self.check_budget()
        if self.queries >= 16:
            raise ValueError('Public read group query bound exceeded')
        self.queries += 1
        result = self.chain.rpc.call(method, params)
        self.check_budget()
        return result

    def read(self, role, method, *arguments):
        if role not in self.contracts:
            raise ValueError('View is outside selected read group ABI scope')
        contract = self.contracts[role]
        calldata = contract.calldata(method, *arguments)
        raw = self._query('eth_call', [{'to': contract.address, 'data': calldata}, self.number])
        values = contract.decode_return(method, raw)
        self.rows.append(dict(chainId=self.chain.chain_id, blockHash=self.block['hash'],
                              blockNumber=str(_quantity(self.number)), address=contract.address,
                              calldata=calldata, returnData=raw, method=method, observedAt=now()))
        return copy.deepcopy(values)

    def logs(self):
        logs = self._query('eth_getLogs', [dict(fromBlock='0x0', toBlock=self.number,
                                              address=[c.address for c in self.contracts.values()])])
        if not isinstance(logs, list):
            raise ValueError('Public contract history array required')
        return copy.deepcopy(logs)
