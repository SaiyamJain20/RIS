"""E2 executor support (agent 2): catalog-driven case tracking, observation recording and flow helpers for the repaired-e cases.

TEST SUPPORT ONLY. Everything here uses the TEST-ONLY synthetic fixture keys. This module is not part of the protocol library: it
drives agent 2's honest components (user client, witness, worker, relay) and, where a catalog step is adversarial, plays the deviating
relay with raw transactions through the chain client.

Integrity rules this module enforces so a test cannot quietly tune its expectation:
  * the catalog file is pinned by SHA-256 and every expectation (`error`, `outcome`, `classification`) is READ FROM IT at run time;
  * each test must perform the catalog's directives in the catalog's order (a differing schedule fails with StepScheduleError,
    which is deliberately not an AssertionError so an xfail(raises=AssertionError) can never mask it);
  * each case is counted when it is concluded; a final test asserts every catalog id was concluded exactly once.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from eth_account import Account
from eth_utils import to_checksum_address

from hmbc_protocol import chain, eip712, messages
from hmbc_protocol.client import ClientError, UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness, WitnessError
from hmbc_protocol.worker import WorkerError
import ledger_setup as setup

CATALOG_PATH = pathlib.Path(__file__).resolve().parent / "fixtures" / "e0-cases-a3-3e0300a.json"       # candidate revision 5 (supersedes c982d04)
CATALOG_SHA256 = "66b5c4f0cb9bdd3ae8bb4795ac9e9771890572c6e238d29516be6668a4218a0f"
PROFILE = "repaired-e"

DIRECTIVES = frozenset({
    "REQUEST_ACCESS", "SUBSTITUTE_SUBJECT", "FORWARD_OR_CONSUME", "REPLAY_REQUEST", "ADVANCE_CLOCK", "REVOKE_ON_PBC", "INSTALL_NEW_LIST",
    "REPLAY_OLD_LIST", "WRONG_ISSUER_UPDATE", "ACCEPT_CHECKPOINT", "RELEASE", "REPORT_OUTCOME", "DROP_OUTCOME", "FABRICATE_OUTCOME",
    "DUPLICATE_OUTCOME", "CRASH_RESTART", "FABRICATE_TUPLE", "SUBSTITUTE_DESTINATION", "REPLAY_NEW_REFERENCE"})
STEP_KEYS = frozenset({"action", "offsetSeconds", "workerHook", "crashPoint"})                 # a new step field must be reviewed, not ignored
EXPECTED_KEYS = frozenset({"property", "outcome", "classification", "error", "qualification", "worker"})
CRASH_FAULTS = {"after-intent": "crash_after_intent", "after-send": "crash_after_send"}       # catalog crashPoint -> Worker fault hook

OBSERVED: dict[str, dict] = {}          # case id -> {classificationExpected, expectedError, observedError, observedOutcome, ...}
EXECUTED: Counter = Counter()           # case id -> number of times a test concluded it


# --- catalog -------------------------------------------------------------------------------------------------------------------

def _load_catalog() -> dict[str, dict]:
    raw = CATALOG_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CATALOG_SHA256, "the pinned case catalog changed"
    cases = {c["id"]: c for c in json.loads(raw)["cases"]}
    return cases


CATALOG: dict[str, dict] = _load_catalog()
REPAIRED_E_IDS = sorted(i for i, c in CATALOG.items() if c["profile"] == PROFILE)


class StepScheduleError(Exception):
    """A test did not perform the catalog's ordered directives. Not an AssertionError on purpose."""


class ClockPreconditionError(Exception):
    """The live chains were too slow/fast for an exact-second schedule (an environment fault, not a protocol result)."""


@dataclass
class Obs:
    """What one attempted action did: a ledger/component error name, or success with its value."""
    error: str | None
    value: Any = None


def observe(fn: Callable, *args, **kwargs) -> Obs:
    try:
        return Obs(None, fn(*args, **kwargs))
    except chain.Rejected as e:
        return Obs(e.code)
    except (WitnessError, WorkerError, ClientError) as e:
        return Obs(e.code)


def pbc_code(res) -> Obs:
    """A PBC request that the PSC denies is an AccessDenied event, not a revert: map it to the same error vocabulary."""
    return Obs(None if res.code == "NONE" else res.code, res)


def check_error(obs: Obs, expected: str | None, what: str = "") -> None:
    """The comparison every case ends in. A wrong, missing or surplus error must raise AssertionError."""
    assert obs.error == expected, f"{what}expected error {expected!r}, observed {obs.error!r}"


class Case:
    def __init__(self, case_id: str, dry_run: bool = False):
        self.id, self.dry_run = case_id, dry_run
        self.case = CATALOG[case_id]
        assert self.case["profile"] == PROFILE, f"{case_id} is not a {PROFILE} case"
        self.expected = self.case["expected"]
        self.schedule = self.case["steps"]
        self.catalog_steps = [s["action"] for s in self.schedule]
        assert set(self.catalog_steps) <= DIRECTIVES, f"unknown directive in {case_id}"
        for s in self.schedule:
            if set(s) - STEP_KEYS or s["offsetSeconds"] != "0":
                raise StepScheduleError(f"{case_id}: step {s} has a field or delay this executor does not realise")
        if set(self.expected) - EXPECTED_KEYS:
            raise StepScheduleError(f"{case_id}: unreviewed expected fields {sorted(set(self.expected) - EXPECTED_KEYS)}")
        self.performed: list[str] = []

    def crash_fault(self) -> str:
        """The Worker fault hook the catalog's CRASH_RESTART names. Per scheduleSemantics it is armed BEFORE the immediately preceding RELEASE."""
        idx = [i for i, s in enumerate(self.schedule) if s["action"] == "CRASH_RESTART"]
        if len(idx) != 1 or idx[0] == 0 or idx[0] + 1 >= len(self.schedule):
            raise StepScheduleError(f"{self.id}: expected exactly one CRASH_RESTART between two steps")
        before, step, after = self.schedule[idx[0] - 1], self.schedule[idx[0]], self.schedule[idx[0] + 1]
        if (before["action"], after["action"], step.get("workerHook")) != ("RELEASE", "RELEASE", "release") or step.get("crashPoint") not in CRASH_FAULTS:
            raise StepScheduleError(f"{self.id}: CRASH_RESTART is not RELEASE / hook=release / known crashPoint / RELEASE: {step}")
        return CRASH_FAULTS[step["crashPoint"]]

    def step(self, action: str) -> None:
        assert action in DIRECTIVES, action
        self.performed.append(action)

    def finish(self, error: str | None, outcome: str, worker: dict | None = None, **detail) -> None:
        """Record the observation FIRST (so a disagreement is still on the record), then compare with the catalog's expectation."""
        if self.performed != self.catalog_steps:
            raise StepScheduleError(f"{self.id}: performed {self.performed}, catalog says {self.catalog_steps}")
        if not self.dry_run:
            assert self.id not in OBSERVED, f"{self.id} concluded twice"
            OBSERVED[self.id] = {
                "classificationExpected": self.expected["classification"], "expectedError": self.expected["error"],
                "observedError": error, "observedOutcome": outcome, "expectedOutcome": self.expected["outcome"],
                "workerExpected": self.expected.get("worker"), "workerObserved": worker,
                "stepsExecuted": list(self.performed), "detail": detail}
            EXECUTED[self.id] += 1
        check_error(Obs(error), self.expected["error"], f"{self.id}: catalog ")
        assert outcome == self.expected["outcome"], f"{self.id}: catalog expects outcome {self.expected['outcome']!r}, observed {outcome!r}"
        # a closed record: every catalog field is compared, and an observation without a catalog record (or the reverse) is itself a failure
        assert worker == self.expected.get("worker"), f"{self.id}: catalog worker record {self.expected.get('worker')}, observed {worker}"


# --- exact-timestamp raw transaction (controlled DBC clock) ---------------------------------------------------------------------

def send_at(ch: chain.Chain, private_key: str, contract, fn: str, *args, timestamp: int, gas: int = 4_000_000) -> dict:
    """Submit one transaction that is mined in a block whose timestamp is EXACTLY `timestamp` (Anvil test nodes only).

    chain.Chain.send estimates gas first, which executes at the node's wall clock and so cannot hit a chosen second. Here the gas is
    fixed, `evm_setNextBlockTimestamp` pins the block, the block's timestamp is checked afterwards, and an on-chain revert is
    decoded from the execution trace into the ledger's Rejected(code) so callers still assert a reason class.
    """
    head = ch.get_block()
    if timestamp <= head["timestamp"]:
        raise ClockPreconditionError(f"head block {head['timestamp']} is not before the requested {timestamp}: the live chains were too slow")
    acct = Account.from_key(private_key)
    data = "0x" + contract.calldata(fn, *args).hex()
    signed = acct.sign_transaction({
        "chainId": ch.chain_id, "nonce": int(ch.rpc("eth_getTransactionCount", [acct.address, "pending"]), 16),
        "gasPrice": int(ch.rpc("eth_gasPrice"), 16), "gas": gas, "to": to_checksum_address(contract.address), "value": 0, "data": data})
    ch.rpc("evm_setNextBlockTimestamp", [timestamp])
    h = ch.rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    for _ in range(100):
        rc = ch.rpc("eth_getTransactionReceipt", [h])
        if rc is not None:
            break
        time.sleep(0.1)
    else:
        raise chain.ChainError(f"transaction {h} not mined in time")
    mined = ch.get_block(int(rc["blockNumber"], 16))["timestamp"]
    if mined != timestamp:
        raise ClockPreconditionError(f"block timestamp {mined} is not the requested {timestamp}")
    if int(rc["status"], 16) != 1:
        trace = ch.rpc("debug_traceTransaction", [h, {}])
        rv = trace.get("returnValue", "")
        rej = chain._revert("0x" + rv.removeprefix("0x"))
        if rej is None:
            raise chain.ChainError(f"transaction {h} reverted without a decodable Rejected(code): {rv!r}")
        raise rej
    return rc


def snapshot(ch: chain.Chain):
    return ch.rpc("evm_snapshot")


def revert(ch: chain.Chain, snap_id) -> None:
    assert ch.rpc("evm_revert", [snap_id]) is True


def db_rows(state_dir, sql: str) -> list:
    con = sqlite3.connect(pathlib.Path(state_dir) / "worker.sqlite")
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def grant_id_of(led, digest: str) -> str:
    return "0x" + eip712.grant_id(bytes.fromhex(digest[2:]), led.KSSC.address, led.dbc.chain_id).hex()


def request_digest(led, request: dict) -> str:
    return "0x" + messages.digest_of("AccessRequest", request, messages.domain_for("AccessRequest", request, led.deployment)).hex()


# --- the flow ------------------------------------------------------------------------------------------------------------------

class Flow:
    """Alice's client, the honest witness and honest relay over one live ledger; adversarial steps use raw transactions."""

    def __init__(self, led, ctx):
        self.led, self.ctx = led, ctx
        self.client = UserClient("alice", led.deployment)
        self.relay = Relay(led, "relay")
        self.witness = Witness(led)
        self.relay_key = setup.key("relay")
        # Anvil mines only on transactions, and evm_revert restores the OLD deployment head block while the node clock keeps running.
        # The witness now prices expiry from Chain.now() (pending block), which fixed the idle-chain fragility this block originally worked
        # around (independent review, A2-0009). The mined block is kept: it is harmless and keeps the head close to "now" for the boundary tests.
        led.dbc.rpc("evm_mine")

    # user + PBC leg
    def sign(self, nonce: str = "1", ttl: int = 30, **over) -> dict:
        return self.client.sign_request(setup.make_request(self.led, self.ctx, self.client, nonce=nonce, ttl=ttl, **over))

    def forward(self, signed: dict):
        return self.relay.forward(signed, self.ctx.bundle)

    def request(self, nonce: str = "1", ttl: int = 30) -> dict:
        """User signs; the honest relay forwards to the PBC; the PBC must allow."""
        signed = self.sign(nonce, ttl)
        res = self.forward(signed)
        assert res.code == "NONE", f"PBC denied the honest request: {res.code}"
        return signed

    # DBC leg
    def accept_checkpoint(self) -> dict:
        cp = self.witness.checkpoint()
        self.relay.accept_state(cp)
        return cp

    def decide(self, signed: dict) -> dict:
        return self.witness.decide(signed["requestDigest"])

    def certified(self, nonce: str = "1", ttl: int = 30) -> tuple[dict, dict]:
        """request + PBC forward + a fresh checkpoint accepted by the DBC + the witness decision (the 'certificate')."""
        signed = self.request(nonce, ttl)
        self.accept_checkpoint()
        return signed, self.decide(signed)

    @staticmethod
    def cert_of(decision_bundle: dict) -> dict:
        return {"decision": decision_bundle["decision"], "signatures": decision_bundle["signatures"]}

    def consume_raw(self, request: dict, decision_bundle: dict, *, cert: dict | None = None, records: list | None = None) -> dict:
        """The (possibly deviating) relay submits request + certificate + records to the ACSC with a raw transaction."""
        return self.led.dbc.send(self.relay_key, self.led.ACSC, "consumeDecision", request, cert or self.cert_of(decision_bundle),
                                 records if records is not None else decision_bundle["credentialRecords"])

    def consume_at(self, request: dict, decision_bundle: dict, timestamp: int, *, cert: dict | None = None) -> dict:
        return send_at(self.led.dbc, self.relay_key, self.led.ACSC, "consumeDecision", request, cert or self.cert_of(decision_bundle),
                       decision_bundle["credentialRecords"], timestamp=timestamp)

    def granted(self, nonce: str = "1", ttl: int = 30) -> tuple[dict, dict, str]:
        signed, d = self.certified(nonce, ttl)
        gid = self.relay.deliver(signed, d)
        assert gid is not None, "the honest flow did not produce a grant"
        return signed, d, gid

    def sign_until(self, nonce: str, expires_at: int) -> dict:
        """Alice signs a request with an EXPLICIT expiry: two requests with one nonce then differ in digest whatever second they are built in."""
        req = self.client.build_request(data_id=setup.DATA_P1, nonce=nonce, expires_at=str(expires_at),
                                        auth_epoch=self.led.pbc.call(self.led.TMSC, "authEpoch"))
        return self.client.sign_request(req)

    def decision_for(self, request: dict, records: list, signer: str, result: str = "1") -> dict:
        """A decision bundle for `request` built from the DBC's CURRENT checkpoint and signed by the key labelled `signer`.

        The honest witness never produces one for an unforwarded or foreign request; tests use this to play a deviating or compromised signer
        and to prove that a rejection is caused by the one thing under test (the control signs the same bytes with the real witness key).
        """
        led = self.led
        exists, cp = led.dbc.call(led.KSSC, "currentCheckpoint")
        assert exists, "no DBC checkpoint: accept one first"
        dec = {"requestDigest": request_digest(led, request), "result": result,
               "credentialDigest": "0x" + eip712.credential_digest(records).hex(), "stateSequence": cp["sequence"],
               "witnessSetVersion": cp["witnessSetVersion"], "sourceBlockNumber": cp["sourceBlockNumber"], "sourceBlockHash": cp["sourceBlockHash"],
               "expiresAt": str(min(int(request["expiresAt"]), int(cp["expiresAt"]), led.dbc.now() + 30))}
        digest = messages.digest_of("AccessDecision", dec, messages.domain_for("AccessDecision", dec, led.deployment))
        return {"decision": dec, "signatures": [eip712.sign_digest(setup.key(signer), digest)], "credentialRecords": records}

    # PBC trust-list leg
    def install_acl(self, acl: dict, admin: str = "H1-ca-admin", root: str = "H1-root") -> dict:
        return self.led.pbc.send(setup.key(admin), self.led.TMSC, "updateTemporalAcl", acl, setup.sign("TemporalAcl", acl, self.led.deployment, root))

    def install_crl(self, crl: dict, admin: str = "H1-ca-admin", root: str = "H1-root") -> dict:
        return self.led.pbc.send(setup.key(admin), self.led.TMSC, "updateRevocationList", crl, setup.sign("RevocationList", crl, self.led.deployment, root))

    def revoke_alice_on_duty(self) -> dict:
        """H1 publishes TempACL v2 without Alice (a new TempACL, so TMSC.authEpoch advances)."""
        return self.install_acl({**self.ctx.acl, "version": "2", "entries": []})

    # observation
    def probe(self, digest: str, nonce: str | None = None, gid: str | None = None) -> dict:
        led = self.led
        return {
            "accessLogCount": led.dbc.call(led.ACSC, "accessLogCount"),
            "grant": led.dbc.call(led.KSSC, "getGrant", grant_id_of(led, digest)),
            "nonceConsumed": None if nonce is None else led.dbc.call(led.KSSC, "nonceConsumed", gid or self.ctx.alice, nonce),
            "pscStatus": led.pbc.call(led.PSC, "getRequest", digest)["status"],
            "outcomeLogId": led.pbc.call(led.LSC, "outcomeLogId", digest),
            "authEpoch": led.pbc.call(led.TMSC, "authEpoch"),
            "checkpointSequence": led.dbc.call(led.KSSC, "currentCheckpoint")[1]["sequence"],
        }
