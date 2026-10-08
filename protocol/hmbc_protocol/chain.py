"""Minimal JSON-RPC chain client (stdlib urllib + eth_account), bound to an expected chain id.

Reads can name a block (never silently "latest"); reverts with the ledger's `Rejected(ErrorCode)` error decode to the
ledger error NAME so callers assert a reason class, not text. Private keys are used only to sign and never logged.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from eth_account import Account
from eth_utils import keccak, to_checksum_address

from .abi import Contract

ERROR_NAMES = ["NONE", "BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR", "STALE_STATE",
               "EXPIRED", "REPLAY", "POLICY_DENIED", "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER", "WRONG_EPOCH", "NOT_COMMITTED",
               "ADAPTER_UNAVAILABLE", "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER", "NOT_REGISTERED", "ALREADY_REGISTERED",
               "REVOKED", "MALFORMED", "WRONG_PROFILE"]
REJECTED_SELECTOR = keccak(text="Rejected(uint8)")[:4]


class ChainError(RuntimeError):
    pass


class Rejected(ChainError):
    """The ledger reverted with Rejected(code)."""

    def __init__(self, code: str):
        super().__init__(f"ledger rejected: {code}")
        self.code = code


def _revert(data: Any) -> Rejected | None:
    if isinstance(data, str) and data.startswith("0x"):
        raw = bytes.fromhex(data[2:]) if len(data) % 2 == 0 else b""
        if raw[:4] == REJECTED_SELECTOR and len(raw) >= 36:
            n = int.from_bytes(raw[4:36], "big")
            return Rejected(ERROR_NAMES[n] if n < len(ERROR_NAMES) else f"UNKNOWN_{n}")
    return None


class Chain:
    def __init__(self, url: str, chain_id: int, timeout: float = 30.0):
        self.url, self.chain_id, self.timeout = url, chain_id, timeout
        self._verified = False

    def rpc(self, method: str, params: list | None = None):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
        req = urllib.request.Request(self.url, data=body, headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                out = json.loads(r.read())
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ChainError(f"{method}: transport failure ({type(e).__name__})") from None
        if "error" in out:
            err = out["error"]
            rej = _revert(err.get("data")) if isinstance(err, dict) else None
            if rej:
                raise rej
            raise ChainError(f"{method}: {err.get('message') if isinstance(err, dict) else err}")
        return out["result"]

    def _check_chain(self) -> None:
        if not self._verified:
            got = int(self.rpc("eth_chainId"), 16)
            if got != self.chain_id:
                raise ChainError(f"chain id mismatch: node reports {got}, expected {self.chain_id}")
            self._verified = True

    @staticmethod
    def _tag(block: int | str) -> str:
        if block == "latest":
            return "latest"
        if isinstance(block, int) and not isinstance(block, bool) and block >= 0:
            return hex(block)
        raise ChainError("block must be 'latest' or a non-negative integer")

    def block_number(self) -> int:
        self._check_chain()
        return int(self.rpc("eth_blockNumber"), 16)

    def get_block(self, block: int | str = "latest") -> dict:
        self._check_chain()
        b = self.rpc("eth_getBlockByNumber", [self._tag(block), False])
        if b is None:
            raise ChainError(f"block {block} does not exist")
        return {"number": int(b["number"], 16), "hash": b["hash"], "timestamp": int(b["timestamp"], 16)}

    def get_logs(self, address: str, topics: list[str], from_block: int = 0, to_block: int | str = "latest") -> list[dict]:
        self._check_chain()
        flt = {"address": address, "topics": topics, "fromBlock": self._tag(from_block), "toBlock": self._tag(to_block)}
        return self.rpc("eth_getLogs", [flt])

    def get_transaction(self, tx_hash: str) -> dict:
        self._check_chain()
        tx = self.rpc("eth_getTransactionByHash", [tx_hash])
        if tx is None:
            raise ChainError(f"transaction {tx_hash} not found")
        return tx

    def call(self, contract: Contract, fn: str, *args: Any, block: int | str = "latest"):
        self._check_chain()
        tag = self._tag(block)
        if tag != "latest" and int(tag, 16) > self.block_number():
            raise ChainError(f"block {block} does not exist")
        data = contract.calldata(fn, *args)
        out = self.rpc("eth_call", [{"to": contract.address, "data": "0x" + data.hex()}, tag])
        return contract.decode_output(fn, bytes.fromhex(out[2:]))

    def send(self, private_key: str, contract: Contract, fn: str, *args: Any) -> dict:
        self._check_chain()
        acct = Account.from_key(private_key)
        data = "0x" + contract.calldata(fn, *args).hex()
        tx = {"from": acct.address, "to": contract.address, "data": data}
        gas = int(self.rpc("eth_estimateGas", [tx]), 16)          # a revert here raises Rejected before anything is sent
        signed = acct.sign_transaction({
            "chainId": self.chain_id, "nonce": int(self.rpc("eth_getTransactionCount", [acct.address, "pending"]), 16),
            "gasPrice": int(self.rpc("eth_gasPrice"), 16), "gas": gas + gas // 5, "to": to_checksum_address(contract.address), "value": 0, "data": data})
        h = self.rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
        for _ in range(100):
            rc = self.rpc("eth_getTransactionReceipt", [h])
            if rc is not None:
                if int(rc["status"], 16) != 1:
                    raise ChainError(f"transaction {h} reverted on chain")
                return rc
            time.sleep(0.1)
        raise ChainError(f"transaction {h} not mined in time")
