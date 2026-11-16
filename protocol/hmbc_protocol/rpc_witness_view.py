"""Witness-side ledger view over JSON-RPC (HMBC2020 successor, F task 2 slice 9a): the REAL implementation of the view `witness_service` reads (derive_* and the signing rules).

PAPER-DERIVED RECONSTRUCTION. `RpcWitnessView` answers the fifteen reads of the witness service from the two chains through the carried `chain.Chain` client (loopback-only URL, no redirects, chain id checked on first use) and the carried `abi.Contract` codec, with the F ledger's ABI files pinned by the manifest's `abiSha256` (`from_manifest`). Each method mirrors what the carried E witness read (`witness.py`) for the same quantity:
  observe(chain)            {"chainId","blockNumber","blockHash","timestamp"} of the LATEST block (all strings);
  pbc_block(n)              {"number","hash","timestamp"} of PBC block n, or None when the node has no such block;
  reads_at(n)               {"authEpoch","policyVersion","witnessSetVersion"} at PBC block n (TMSC.authEpoch, PSC.policyVersion, PSC.witnessSetVersion);
  dbc_current_checkpoint()  None, or the KSSC.currentCheckpoint tuple as a dict;
  governance_nonce(), is_authority(root), removed_authority(root)   Governance.governanceNonce, TMSC.isAuthority, TMSC.removedAuthority;
  psc_request(digest)       PSC.getRequest as a dict; forwarded_logs(digest) [{"txHash","block"}] of AccessForwarded; forwarding_call(txHash) the decoded direct call or None;
  now(chain)                the carried Chain.now (the greater of the latest and the pending block timestamp);
  nonce_consumed(gid, nonce), credentials(gid, bundle, at, block) (TMSC.checkCredentials at the PBC block), policy_satisfied(dataId, records) (ACSC.evaluate);
  grant(grantId)            KSSC.getGrant as a dict; grant_issued_logs(grantId) [{"block","hash"}] of GrantIssued.
FAULT MODEL. Any transport, node, revert or decoding failure is `witness_service.LedgerUnreachable` (the service turns it into ADAPTER_UNAVAILABLE / LEDGER_UNREACHABLE and writes nothing); a caller bug is a
ValueError. LIMITS stated plainly: reads of the latest state (`grant`, `nonce_consumed`, `policy_satisfied`, `dbc_current_checkpoint`) are NOT pinned to the block `observe` returned (two reads can straddle a
block); there is no reorg bracketing. The decision and receipt paths have been run once, honest path only, against a real forwarded request on a real F ledger (test_rpc_binding_view_live.py, slice 9b); no
denial, stale, expired or adversarial case has. DECODING IS THE CARRIED CODECS' AND IS PERMISSIVE: `chain.Chain` parses hex quantities with `int(v, 16)` (separators, leading zeros and upper case are accepted) and
`abi.Contract.decode_output` is the lenient `eth_abi` decoder (trailing bytes and non-minimal offsets decode). Unlike `RpcBindingView`, which enforces minimal quantities and exact canonical ABI replies, this view
makes NO canonical-bytes claim: it classifies a reply that cannot be read as LedgerUnreachable and otherwise trusts the carried decoding of it. No clock, thread or environment access; the injected clients own the transport.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

from eth_utils import keccak

from . import startup_config as sc
from .abi import AbiError, Contract
from .chain import Chain, ChainError
from .witness_service import LedgerUnreachable

SIDES = ("pbc", "dbc")
CONTRACT_SIDE = {"PSC": "pbc", "TMSC": "pbc", "Governance": "pbc", "KSSC": "dbc", "ACSC": "dbc"}
REQUIRED = ("PSC", "TMSC", "KSSC", "ACSC")
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_HASH = re.compile(r"0x[0-9a-f]{64}")
_DEC = re.compile(r"(0|[1-9][0-9]*)")


def _unreachable(what):
    return LedgerUnreachable(what)


class RpcWitnessView:
    def __init__(self, *, chains, contracts):
        if not isinstance(chains, dict) or set(chains) != set(SIDES):
            raise ValueError("chains must be exactly {'pbc': client, 'dbc': client}")
        if not isinstance(contracts, dict) or not set(REQUIRED) <= set(contracts) <= set(CONTRACT_SIDE):
            raise ValueError("contracts must hold PSC, TMSC, KSSC and ACSC, and may hold Governance")
        for name, c in contracts.items():
            if not isinstance(c, Contract) or not isinstance(c.address, str) or _ADDR.fullmatch(c.address) is None:
                raise ValueError(f"{name} must be a Contract with a lowercase address")
        self._chains, self._c = dict(chains), dict(contracts)

    @classmethod
    def from_manifest(cls, manifest, chains, abi_dir):
        """The view for a pinned deployment manifest: chain clients for the manifest's chain ids; each ABI file must hash to the manifest's `abiSha256`."""
        if not isinstance(manifest, dict) or not isinstance(chains, dict) or set(chains) != set(SIDES):
            raise ValueError("a manifest and chain clients for pbc and dbc are required")
        contracts = {}
        try:
            for side in SIDES:
                if sc.uint_text(manifest["chains"][side]["chainId"], 256, f"{side} chainId") != chains[side].chain_id:
                    raise ValueError(f"the {side} client is for another chain id than the manifest's")
            for name, side in CONTRACT_SIDE.items():
                address = manifest["chains"][side]["contracts"].get(name)
                if address is None:
                    continue
                pinned = manifest["abi"][name]["abiSha256"]
                with open(os.path.join(abi_dir, name + ".json"), "rb") as f:
                    raw = f.read()
                if hashlib.sha256(raw).hexdigest() != pinned:
                    raise ValueError(f"the ABI file for {name} does not hash to the manifest's abiSha256")
                contracts[name] = Contract(sc.loads(raw, f"ABI file for {name}"), address)
        except (KeyError, TypeError, AttributeError, OSError, AbiError, json.JSONDecodeError) as e:
            raise ValueError(f"the manifest, the clients or the ABI files are unusable: {type(e).__name__}") from None
        return cls(chains=chains, contracts=contracts)

    # ---- plumbing ----------------------------------------------------------------------------------------------------------------------------------------------
    def _chain(self, side):
        if side not in SIDES:
            raise ValueError("chain must be 'pbc' or 'dbc'")
        return self._chains[side]

    def _contract(self, name):
        try:
            return self._c[name]
        except KeyError:
            raise ValueError(f"this view has no {name} contract") from None

    def _guard(self, fn):
        try:
            return fn()
        except (ChainError, AbiError) as e:
            raise _unreachable(f"{type(e).__name__}: {e}") from None
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as e:
            raise _unreachable(f"the node answered something unusable ({type(e).__name__})") from None

    @staticmethod
    def _exactly(out, n):
        """A decoded multi-value output must be exactly `n` values: anything else is the node (or the ABI) answering something unusable."""
        if not isinstance(out, (list, tuple)) or len(out) != n:
            raise _unreachable(f"the node answered {type(out).__name__} where {n} values were expected")
        return tuple(out)

    def _call(self, side, name, fn, *args, block="latest"):
        chain, contract = self._chain(side), self._contract(name)
        return self._guard(lambda: chain.call(contract, fn, *args, block=block))

    @staticmethod
    def _number(n):
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("a block number must be a non-negative integer")
        return n

    @staticmethod
    def _hash32(v, what):
        if not isinstance(v, str) or _HASH.fullmatch(v) is None:
            raise ValueError(f"{what} must be a lowercase 32-byte hash")
        return v

    # ---- blocks and clocks -------------------------------------------------------------------------------------------------------------------------------------
    def observe(self, chain):
        c = self._chain(chain)
        b = self._guard(lambda: c.get_block("latest"))
        return {"chainId": str(c.chain_id), "blockNumber": str(b["number"]), "blockHash": b["hash"], "timestamp": str(b["timestamp"])}

    def pbc_block(self, number):
        n, c = self._number(number), self._chain("pbc")

        def read():
            c._check_chain()
            b = c.rpc("eth_getBlockByNumber", [hex(n), False])
            if b is None:
                return None
            return {"number": str(n), "hash": b["hash"], "timestamp": str(int(b["timestamp"], 16))}
        return self._guard(read)

    def now(self, chain):
        c = self._chain(chain)
        return self._guard(c.now)

    # ---- PBC state ---------------------------------------------------------------------------------------------------------------------------------------------
    def reads_at(self, number):
        n = self._number(number)
        return {"authEpoch": self._call("pbc", "TMSC", "authEpoch", block=n), "policyVersion": self._call("pbc", "PSC", "policyVersion", block=n),
                "witnessSetVersion": self._call("pbc", "PSC", "witnessSetVersion", block=n)}

    def governance_nonce(self):
        return self._call("pbc", "Governance", "governanceNonce")

    def is_authority(self, root):
        return self._call("pbc", "TMSC", "isAuthority", root)

    def removed_authority(self, root):
        return self._call("pbc", "TMSC", "removedAuthority", root)

    def psc_request(self, digest):
        return self._call("pbc", "PSC", "getRequest", self._hash32(digest, "digest"))

    def credentials(self, gid, bundle, at_timestamp, block):
        out = self._call("pbc", "TMSC", "checkCredentials", gid, bundle, str(at_timestamp), block=self._number(block))
        code, records = self._exactly(out, 2)
        return code, records

    # ---- logs and transactions ---------------------------------------------------------------------------------------------------------------------------------
    def _logs(self, side, name, event, topic_value):
        c, contract = self._chain(side), self._contract(name)
        topic0 = "0x" + keccak(text=contract.event_signature(event)).hex()
        topic = self._hash32(topic_value, "topic")                       # validated BEFORE the guard: a caller bug must not look like a ledger fault
        return self._guard(lambda: c.get_logs(contract.address, [topic0, topic]))

    def forwarded_logs(self, digest):
        logs = self._logs("pbc", "PSC", "AccessForwarded", digest)
        return self._guard(lambda: [{"txHash": lg["transactionHash"], "block": int(lg["blockNumber"], 16)} for lg in logs])

    def forwarding_call(self, tx_hash):
        """The transaction's target and decoded call, or None when the transaction object carries no input that decodes as a call of the PSC ABI (the service refuses a None as WRONG_SUBJECT). A transaction the
        node does not have, a transport failure and a reply that is not even a JSON object are LedgerUnreachable, not None (the carried client raises ChainError for a missing transaction)."""
        c, psc = self._chain("pbc"), self._contract("PSC")
        tx_hash = self._hash32(tx_hash, "tx hash")
        tx = self._guard(lambda: c.get_transaction(tx_hash))
        if not isinstance(tx, dict):                                         # the carried client returns any non-null node reply: a non-object is the node answering something unusable
            raise _unreachable(f"the node answered {type(tx).__name__} where a transaction object was expected")
        try:
            to = str(tx.get("to") or "").lower()
            name, args = psc.decode_input(bytes.fromhex(tx["input"][2:]))
        except (AbiError, KeyError, TypeError, ValueError):
            return None
        if name != "requestAccess":
            return {"to": to, "method": name, "request": None, "signature": None, "bundle": None}
        request, signature, bundle = args
        return {"to": to, "method": name, "request": request, "signature": signature, "bundle": bundle}

    def grant_issued_logs(self, grant_id):
        logs = self._logs("dbc", "KSSC", "GrantIssued", grant_id)
        return self._guard(lambda: [{"block": int(lg["blockNumber"], 16), "hash": lg["blockHash"]} for lg in logs])

    # ---- DBC state ---------------------------------------------------------------------------------------------------------------------------------------------
    def dbc_current_checkpoint(self):
        out = self._call("dbc", "KSSC", "currentCheckpoint")
        exists, cur = self._exactly(out, 2)
        return self._guard(lambda: dict(cur)) if exists else None

    def nonce_consumed(self, gid, nonce):
        return self._call("dbc", "KSSC", "nonceConsumed", gid, str(nonce))

    def policy_satisfied(self, data_id, records):
        return self._call("dbc", "ACSC", "evaluate", self._hash32(data_id, "data id"), records)

    def grant(self, grant_id):
        out = self._call("dbc", "KSSC", "getGrant", self._hash32(grant_id, "grant id"))
        digest, data_id, gid, key_epoch, expires, allowed = self._exactly(out, 6)
        return {"digest": digest, "dataId": data_id, "gid": gid, "keyEpoch": key_epoch, "expiresAt": expires, "allowed": allowed}
