"""TEST-ONLY compromised key-worker variant H5 (HMBC2020 successor, F task 3; INVENTORY FM-08 and row F-19, PLAN B-F1 bullet 4). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys only.

WHAT IT IS. `CompromisedWorker` is the carried `Worker` with ONE thing taken away: for the request digests it was TOLD about (its CLAIMS) it releases the symbolic capability WITHOUT any ledger-committed grant,
exactly as a worker that has been taken over would simply stop asking the ledger. For every other grant id it behaves exactly like the honest worker (so it is not "allow everything", and legitimate flows
still work). A claim is {requestDigest, dataId, gid, recipientKeyRef}; the grant id is the hash of the request digest, so a compromised worker can only release for a digest it is given. Nothing else is skipped:
the record must still be in the worker's own registry (it legitimately holds it), the release is bound to the claimed recipient, intent and send are logged and the audit trail is the honest worker's.

WHAT IT SHOWS. The F certificate layer (q = 3 of 4 witness signatures checked by the real contracts) authorises a GRANT; it does not hold or guard a worker's secrets. With this variant the real ledger
still has no grant (and the PBC never forwarded the request) while the response is issued and completes. The honest worker refuses the same grant id with NOT_COMMITTED (the positive control).

WHAT IT DOES NOT SHOW. SYMBOLIC ONLY: the response token is a TEST-ONLY random handle, so there is no secrecy or ABE conclusion here, and no claim about witness-only resilience (that is the Byzantine
witness work, kept separate on purpose). It is a statement about WHERE authorisation is enforced: in the worker, by trust, which is the paper's isolation assumption and the plan's "trusted worker".

HOW, without editing any existing file: the honest `Worker.release` reads its grant through `self.led.dbc.call(self.led.KSSC, "grantDetails", id)`. For a claimed id this class swaps `self.led` for a thin facade whose
`grantDetails` answers with the claimed grant (and delegates everything else), calls the honest `release`, and restores the real ledger in a `finally`. `_recipient_for` is overridden only while forging.

Refuses (SystemExit `refusing:` before anything is created) unless the deployment declares TEST-ONLY synthetic keys; malformed or duplicate claims are a ValueError before anything is created. It is NOT part of
the production adapter or worker, not one of their operations, not imported by any production module and not in any export.
"""
from __future__ import annotations

from hmbc_protocol import eip712, keys, wire
from hmbc_protocol.worker import Worker

from testtools.bootstrap_fixture import require_test_only

CLAIM_FIELDS = {"requestDigest", "dataId", "gid", "recipientKeyRef"}
FORGED_TTL = 30


class _ForgedDbc:
    """The DBC client as the honest release code uses it, with ONE read replaced: `grantDetails` of a claimed grant id."""

    def __init__(self, real, grant_id, grant):
        self._real, self._grant_id, self._grant = real, grant_id, grant

    def call(self, contract, fn, *args, **kwargs):
        if fn == "grantDetails" and args and args[0] == self._grant_id:
            return dict(self._grant)
        return self._real.call(contract, fn, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _ForgedLedger:
    def __init__(self, real, grant_id, grant):
        self._real = real
        self.dbc = _ForgedDbc(real.dbc, grant_id, grant)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _validated(claims):
    if not isinstance(claims, list):
        raise ValueError("claims must be a list")
    out = []
    for c in claims:
        if not isinstance(c, dict) or set(c) != CLAIM_FIELDS:
            raise ValueError(f"a claim is exactly {sorted(CLAIM_FIELDS)}")
        wire.hash32(c["requestDigest"])
        wire.hash32(c["dataId"])
        wire.address(c["gid"])
        keys.recipient_key_hash(c["recipientKeyRef"])               # a `keyref:user:<label>` handle, else KeyRefError (a ValueError)
        out.append(dict(c))
    if len({c["requestDigest"] for c in out}) != len(out):
        raise ValueError("two claims for the same request digest")
    return out


class CompromisedWorker(Worker):
    """TEST-ONLY: releases for claimed request digests without a ledger-committed grant; honest for everything else. Symbolic mode only."""

    def __init__(self, led, state_dir, clock, claims):
        require_test_only(led.deployment)
        checked = _validated(claims)
        super().__init__(led, state_dir, clock=clock)
        self.claims = {"0x" + eip712.grant_id(bytes.fromhex(c["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex(): c for c in checked}
        self._forging = False

    def release(self, grant_id, transmit=None):
        c = self.claims.get(grant_id)
        if c is None:
            return super().release(grant_id, transmit)
        grant = {"exists": True, "allowed": True, "requestDigest": c["requestDigest"], "dataId": c["dataId"], "gid": c["gid"], "keyEpoch": "0",
                 "expiresAt": str(self.clock() + FORGED_TTL), "recipientKeyHash": keys.recipient_key_hash(c["recipientKeyRef"])}
        real, self.led, self._forging = self.led, _ForgedLedger(self.led, grant_id, grant), True
        try:
            return super().release(grant_id, transmit)
        finally:
            self.led, self._forging = real, False

    def _recipient_for(self, g):
        return g["recipientKeyHash"] if self._forging else super()._recipient_for(g)
