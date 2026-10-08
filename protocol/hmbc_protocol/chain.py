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
from urllib.parse import urlsplit

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
        try:
            raw = bytes.fromhex(data[2:])
        except ValueError:
            return None
        if raw[:4] == REJECTED_SELECTOR and len(raw) >= 36:
            n = int.from_bytes(raw[4:36], "big")
            return Rejected(ERROR_NAMES[n] if n < len(ERROR_NAMES) else f"UNKNOWN_{n}")
    return None


def validate_url(u: object) -> str:
    """http(s) on the loopback host with an explicit port: a request must not be able to steer the adapter at another network target."""
    try:
        parts = urlsplit(u) if isinstance(u, str) else None
        port = parts.port if parts else None
    except ValueError:
        raise ChainError("rpcUrl is malformed") from None
    if not parts or parts.scheme not in ("http", "https") or parts.hostname not in ("127.0.0.1", "localhost", "::1") or not port:
        raise ChainError("rpcUrl must be an http(s) loopback URL with an explicit port")
    return u


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):          # a redirect would let a loopback node bounce the client to a host validate_url refused
        return None


# No proxies (environment proxy variables are ignored) and no redirects.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def _hex(v: Any) -> int:
    if not isinstance(v, str) or not v.startswith("0x"):
        raise ChainError("node returned a non-hex quantity")
    try:
        return int(v, 16)
    except ValueError:
        raise ChainError("node returned a malformed hex quantity") from None


class Chain:
    def __init__(self, url: str, chain_id: int, timeout: float = 30.0):
        self.url, self.chain_id, self.timeout = validate_url(url), chain_id, timeout
        self._verified = False

    def rpc(self, method: str, params: list | None = None):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
        req = urllib.request.Request(self.url, data=body, headers={"content-type": "application/json"})
        try:
            with _OPENER.open(req, timeout=self.timeout) as r:
                out = json.loads(r.read())
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ChainError(f"{method}: transport failure ({type(e).__name__})") from None
        if not isinstance(out, dict):
            raise ChainError(f"{method}: node reply is not a JSON object")
        if "error" in out:
            err = out["error"]
            rej = _revert(err.get("data")) if isinstance(err, dict) else None
            if rej:
                raise rej
            raise ChainError(f"{method}: {err.get('message') if isinstance(err, dict) else err}")
        if "result" not in out:
            raise ChainError(f"{method}: node reply has neither result nor error")
        return out["result"]

    def _check_chain(self) -> None:
        if not self._verified:
            got = _hex(self.rpc("eth_chainId"))
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
        return _hex(self.rpc("eth_blockNumber"))

    def now(self) -> int:
        """The chain's current time: the greater of the latest block's timestamp and the pending block's. The latest block's timestamp alone
        freezes while the chain is idle, which would let an expired grant look live and make fresh checkpoints look expired."""
        latest = self.get_block("latest")["timestamp"]
        try:
            b = self.rpc("eth_getBlockByNumber", ["pending", False])
            pending = _hex(b["timestamp"]) if isinstance(b, dict) and "timestamp" in b else latest
        except (ChainError, ValueError, TypeError):
            pending = latest
        return max(latest, pending)

    def get_block(self, block: int | str = "latest") -> dict:
        self._check_chain()
        b = self.rpc("eth_getBlockByNumber", [self._tag(block), False])
        if b is None:
            raise ChainError(f"block {block} does not exist")
        if not isinstance(b, dict) or not all(k in b for k in ("number", "hash", "timestamp")):
            raise ChainError("node returned a malformed block")
        return {"number": _hex(b["number"]), "hash": b["hash"], "timestamp": _hex(b["timestamp"])}

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
        if tag != "latest" and _hex(tag) > self.block_number():
            raise ChainError(f"block {block} does not exist")
        data = contract.calldata(fn, *args)
        out = self.rpc("eth_call", [{"to": contract.address, "data": "0x" + data.hex()}, tag])
        return contract.decode_output(fn, bytes.fromhex(out[2:]))

    def send(self, private_key: str, contract: Contract, fn: str, *args: Any) -> dict:
        self._check_chain()
        acct = Account.from_key(private_key)
        data = "0x" + contract.calldata(fn, *args).hex()
        tx = {"from": acct.address, "to": contract.address, "data": data}
        gas = _hex(self.rpc("eth_estimateGas", [tx]))          # a revert here raises Rejected before anything is sent
        signed = acct.sign_transaction({
            "chainId": self.chain_id, "nonce": _hex(self.rpc("eth_getTransactionCount", [acct.address, "pending"])),
            "gasPrice": _hex(self.rpc("eth_gasPrice")), "gas": gas + gas // 5, "to": to_checksum_address(contract.address), "value": 0, "data": data})
        h = self.rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
        for _ in range(100):
            rc = self.rpc("eth_getTransactionReceipt", [h])
            if rc is not None:
                if _hex(rc.get("status")) != 1:
                    raise ChainError(f"transaction {h} reverted on chain")
                return rc
            time.sleep(0.1)
        raise ChainError(f"transaction {h} not mined in time")
