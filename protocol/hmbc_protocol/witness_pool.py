"""Pool collection state machine (HMBC2020 successor, F task 3 slice 3b).

PAPER-DERIVED RECONSTRUCTION of the collector procedure of SIGNING-RULES section 8 and SUCCESSOR-WIRE section 2, built on the pure decision core `pool_core` (slice 3a).

`Collection` is ONE pool collection as a SANS-IO state machine: the caller tells it what happened (a reply from witness w at host-monotonic millisecond t, or that time passed) and it answers with
the actions to perform (send the retained proposal, cancel an undelivered send). It holds no key, opens no socket, reads no clock and signs nothing; a real driver (a later slice) supplies the
transport and the clock, a test driver supplies virtual ones. The pool is untrusted: every reply is validated here by recomputing the digest and recovering the signer, and no witness is ever made to
sign anything it has not validated itself.

Procedure implemented: retain the proposal and send it verbatim to all four witnesses; per reply parse strictly, recover the signer, require it to equal the replying witness's configured address,
deduplicate by witness (the first valid signature wins; repeats only add to `replies`), and finish the moment three distinct valid signatures over ONE message exist (exactly three, sorted by signer
address). Otherwise close the decision snapshot (all four replied strictly before min(5 s, deadline), or the reply timeout, or the original deadline), adopt on the snapshot only (checkpoints only),
apply the effort gate, and, when it says `sent`, run one second round with the adopted message verbatim, inside the original deadline. Late reports are evidence, never an input. At the deadline
(or earlier when nothing can change) report a classified failure; a missing quorum is `QUORUM_UNAVAILABLE`, never a denial.

Explicit choices where F0 is silent (choices, not discoveries):
  * A timer due at millisecond t fires BEFORE a reply at t: a reply exactly at the reply timeout is late; a reply at or after the deadline is ignored (the collection ended at the deadline).
  * The collection ends early when nothing can change: all four witnesses replied in round 1 and no second round starts, or all four replied in round 2.
  * An early success (three signatures before the snapshot closes) takes no snapshot and serializes no evidence members; reports seen before it are not serialized.
  * A reply is judged against the message asked in ITS round (round 1: the retained proposal; round 2: the adopted message). A success reply over any other message is a `dissent`.
  * The status of a witness is judged against the final reference message M* (the certificate's message; else the adopted value; else the retained proposal): `signed` iff it returned a valid signature
    over M*; else `invalid` (any invalid reply, or inconsistent in the snapshot); else `refused` (its latest error reply); else `dissent` (a success reply that is not over M*); else `silent`.
  * `duplicate-only` is in the wire vocabulary but no reply sequence over per-witness channels reaches it (a signature that does not recover to the replying witness is `invalid`, rule 2), so it is
    never emitted. This is a limit to be listed, not a feature.
  * A recorded report is valid only for CONFLICT_PINNED (code STALE_STATE) on a checkpoint collection, for the proposal's sequence, with a signature that recovers to the replying witness.
"""
from __future__ import annotations

import copy
import json
import re

from . import pool_core as core

_ADDR = re.compile(r"0x[0-9a-f]{40}")
_DEC = re.compile(r"(0|[1-9][0-9]*)")
EQUIVOCATION_DETAIL = "returned two different recorded values; excluded from adoption"


class CollectionError(ValueError):
    """A caller bug (wrong index, time going backwards, wrong lifecycle). Never raised for the content of a witness's reply."""


class CollectionRefused(Exception):
    """The collection cannot exist (2 s or less of validity remain): refuse before any witness is contacted."""

    def __init__(self, code, reason, message):
        super().__init__(message)
        self.code, self.reason, self.message = code, reason, message


def make_recover(name, deployment):
    """The production signer recovery: recompute the EIP-712 digest of `message` under the deployment's domain for `name` and recover the signer. None when anything about the pair is malformed."""
    from . import eip712, messages        # lazy: the state machine itself needs no cryptography library

    def recover(message, signature):
        try:
            digest = messages.digest_of(name, message, messages.domain_for(name, message, deployment))
            return eip712.recover(digest, signature)
        except (ValueError, KeyError, TypeError):
            return None

    return recover


def _canon(message):
    return core.canonical_message(message)


def _flat_message(m):
    """A dict of strings: the shape of a checkpoint and the only shape the adoption core accepts (a recorded report that carried anything else would make the core raise on hostile input)."""
    return isinstance(m, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in m.items())


def _plain_message(m):
    """A dict of strings and lists of strings (a GovernanceAction has `admins`). Used for the retained proposal and for signature replies; adoption never sees such a message."""
    return isinstance(m, dict) and all(isinstance(k, str) and (isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))) for k, v in m.items())


class Collection:
    def __init__(self, *, witnesses, recover, proposal, ledger_now_at_start, proposal_expires_at, adoption, witness_set_version):
        if not (isinstance(witnesses, list) and len(witnesses) == core.WITNESS_COUNT and all(isinstance(a, str) and _ADDR.fullmatch(a) for a in witnesses) and len(set(witnesses)) == len(witnesses)):
            raise CollectionError("witnesses must be four distinct lowercase addresses in index order")
        if not callable(recover):
            raise CollectionError("recover must be callable")
        if not _plain_message(proposal):
            raise CollectionError("the proposal must be a dict of strings")
        if not isinstance(adoption, bool):
            raise CollectionError("adoption must be a boolean")
        if adoption and not _flat_message(proposal):
            raise CollectionError("an adopting collection needs a proposal that is a dict of strings")
        if not isinstance(witness_set_version, str) or _DEC.fullmatch(witness_set_version) is None:
            raise CollectionError("witness_set_version must be a decimal string")
        deadline = core.collection_deadline_ms(ledger_now_at_start, proposal_expires_at)
        if deadline is None:
            raise CollectionRefused("EXPIRED", None, "the proposal has 2 s or less of validity left; no witness was contacted")
        self._w, self._recover, self._P, self._adoption, self._version = list(witnesses), recover, dict(proposal), adoption, witness_set_version
        self._seq = None
        if adoption:
            if _DEC.fullmatch(self._P.get("sequence", "")) is None:
                raise CollectionError("an adopting collection needs a decimal sequence in the proposal")
            self._seq = int(self._P["sequence"])
        self._now0, self._prop, self._deadline = ledger_now_at_start, proposal_expires_at, deadline
        self._snap_limit = min(core.REPLY_TIMEOUT_MS, deadline)
        self._started = False
        self._done = False
        self._t = 0
        self.finished_at_ms = None
        self._result = None
        self._replies = [0] * core.WITNESS_COUNT
        self._events = [[] for _ in range(core.WITNESS_COUNT)]
        self._sigs = {}                  # canonical message -> {witness: signature}, first valid wins
        self._msgs = {}                  # canonical message -> message
        self._r1_replied = set()
        self._snap_closed = False
        self._close_ms = None
        self._all_at = None
        self._snapshot, self._late = [], []
        self._round2 = False
        self._r2_end = None
        self._r2_replied = set()
        self._asked2 = None
        self._adopted = None

    # ---- public surface ------------------------------------------------------------------------------------------------------------------------------------------------------------
    @property
    def done(self):
        return self._done

    @property
    def result(self):
        return self._result

    def start(self):
        if self._started:
            raise CollectionError("a collection starts once")
        self._started = True
        return [{"op": "send", "witness": w, "round": 1, "message": dict(self._P)} for w in range(core.WITNESS_COUNT)]

    def next_timer_ms(self):
        if not self._started or self._done:
            return None
        timers = [self._deadline]
        if not self._snap_closed:
            timers.append(self._snap_limit)
        if self._round2:
            timers.append(self._r2_end)
        return min(timers)

    def on_time(self, t_ms):
        self._tick(t_ms)
        return self._advance(t_ms)

    def on_reply(self, t_ms, witness, reply, round_no=1):
        if isinstance(witness, bool) or not isinstance(witness, int) or not 0 <= witness < core.WITNESS_COUNT:
            raise CollectionError("witness index must be an integer 0..3")
        if isinstance(round_no, bool) or not isinstance(round_no, int) or round_no not in (1, 2):
            raise CollectionError("round_no must be 1 or 2")
        self._tick(t_ms)
        actions = self._advance(t_ms)
        if self._done:
            return actions
        if round_no == 2 and not self._round2:
            raise CollectionError("no second round was started")
        self._replies[witness] += 1
        self._process(t_ms, witness, reply, round_no)
        if not self._done:
            actions += self._after_reply(t_ms, witness, round_no)
        return actions

    def current_evidence(self):
        """The evidence members (`recordedReports`, `inconsistentReports`, `lateReports`, `adopted`, `timing`) as they stand now; empty before the snapshot closes or without adoption."""
        if not self._adoption or not self._snap_closed:
            return {}
        return core.evidence(self._snapshot, self._late, self._seq, ledger_now_at_start=self._now0, proposal_expires_at=self._prop, all_replied_at_ms=self._all_at)

    # ---- time ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _tick(self, t_ms):
        if not self._started:
            raise CollectionError("the collection was not started")
        if isinstance(t_ms, bool) or not isinstance(t_ms, int) or t_ms < self._t:
            raise CollectionError("time must be a non-decreasing non-negative integer")
        self._t = t_ms

    def _advance(self, t_ms):
        actions = []
        while not self._done:
            due = []
            if not self._snap_closed and self._snap_limit <= t_ms:
                due.append((self._snap_limit, 0))
            if self._round2 and self._r2_end <= t_ms:
                due.append((self._r2_end, 1))
            if self._deadline <= t_ms:
                due.append((self._deadline, 2))
            if not due:
                break
            at, kind = min(due)
            if kind == 0:
                close, by = core.snapshot_close(self._deadline, None)
                actions += self._close_snapshot(close, None)
            else:
                self._finish(at)
        return actions

    # ---- replies ------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _asked(self, round_no):
        return self._P if round_no == 1 else self._asked2

    def _invalid(self, w, detail):
        self._events[w].append(("invalid", detail))

    def _process(self, t, w, reply, round_no):
        if not isinstance(reply, dict) or not isinstance(reply.get("type"), str):
            return self._invalid(w, "unparseable reply")
        kind = reply["type"]
        if kind == "malformed":
            return self._invalid(w, "malformed reply" if not isinstance(reply.get("detail"), str) or not reply["detail"] else "malformed reply: " + reply["detail"])
        if kind == "signature":
            return self._process_signature(w, reply, round_no)
        if kind == "error":
            return self._process_error(t, w, reply)
        return self._invalid(w, "unknown reply type")

    def _process_signature(self, w, reply, round_no):
        if set(reply) != {"type", "message", "signature"} or not _plain_message(reply["message"]) or not isinstance(reply["signature"], str):
            return self._invalid(w, "malformed signature reply")
        m, sig = reply["message"], reply["signature"]
        if _canon(m) != _canon(self._asked(round_no)):
            self._events[w].append(("dissent", "replied with a message that differs from the one asked"))
            return None
        who = self._recover(m, sig)
        if who is None:
            return self._invalid(w, "signature does not verify over the recomputed digest")
        if who != self._w[w]:
            return self._invalid(w, "signature does not recover to the replying witness")
        c = _canon(m)
        self._events[w].append(("signed", c))
        self._msgs.setdefault(c, dict(m))
        self._sigs.setdefault(c, {}).setdefault(w, sig)
        return None

    def _process_error(self, t, w, reply):
        if not set(reply) <= {"type", "code", "reason", "recorded"} or not isinstance(reply.get("code"), str) or not reply["code"] \
                or not (reply.get("reason") is None or (isinstance(reply["reason"], str) and reply["reason"])):
            return self._invalid(w, "malformed error reply")
        code, reason, recorded = reply["code"], reply.get("reason"), reply.get("recorded")
        if recorded is not None:
            if not (self._adoption and code == "STALE_STATE" and reason == "CONFLICT_PINNED"):
                return self._invalid(w, "a recorded value is only valid with a CONFLICT_PINNED refusal of a checkpoint")
            if not (isinstance(recorded, dict) and set(recorded) == {"message", "signature"} and _flat_message(recorded["message"]) and isinstance(recorded["signature"], str)):
                return self._invalid(w, "malformed recorded value")
            if recorded["message"].get("sequence") != self._P["sequence"]:
                return self._invalid(w, "the recorded value is for another sequence")
            who = self._recover(recorded["message"], recorded["signature"])
            if who is None or who != self._w[w]:
                return self._invalid(w, "the recorded signature does not recover to the replying witness")
            report = {"witness": w, "message": dict(recorded["message"]), "signature": recorded["signature"], "validSignature": True}
            (self._late if self._snap_closed else self._snapshot).append(report)
        self._events[w].append(("refused", (code, reason)))
        return None

    # ---- after a reply: success, snapshot, rounds ----------------------------------------------------------------------------------------------------------------------------------
    def _after_reply(self, t, w, round_no):
        for c, sigs in self._sigs.items():
            if len(sigs) >= core.POOL_QUORUM:
                self._finish(t, certificate=c)
                return []
        actions = []
        if round_no == 1:
            self._r1_replied.add(w)
            if not self._snap_closed and len(self._r1_replied) == core.WITNESS_COUNT and t < self._snap_limit:
                actions += self._close_snapshot(t, t)
        else:
            self._r2_replied.add(w)
            if len(self._r2_replied) == core.WITNESS_COUNT:
                self._finish(t)
        return actions

    def _close_snapshot(self, close, all_at):
        self._snap_closed, self._close_ms, self._all_at = True, close, all_at
        actions = []
        if self._adoption:
            picked = core.adopt_recorded(self._snapshot, self._seq)
            if picked is not None:
                self._adopted = picked
                if core.reproposal_status(self._now0, int(picked["expiresAt"]), close, self._deadline) == "sent":
                    self._round2, self._asked2, self._r2_end = True, picked, min(close + core.REPLY_TIMEOUT_MS, self._deadline)
                    actions += [{"op": "cancel", "witness": w, "round": 1} for w in range(core.WITNESS_COUNT) if w not in self._r1_replied]
                    actions += [{"op": "send", "witness": w, "round": 2, "message": dict(picked)} for w in range(core.WITNESS_COUNT)]
                    return actions
        if len(self._r1_replied) == core.WITNESS_COUNT:
            self._finish(close)
        return actions

    # ---- the result ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _finish(self, t, certificate=None):
        self._done = True
        self.finished_at_ms = t
        evidence = self.current_evidence()
        reference = certificate if certificate is not None else (_canon(self._adopted) if self._adopted is not None else _canon(self._P))
        inconsistent = {int(e["witnessIndex"]) for e in evidence.get("inconsistentReports", [])}
        outcomes = [self._outcome(w, reference, w in inconsistent) for w in range(core.WITNESS_COUNT)]
        coll = {"quorum": str(core.POOL_QUORUM), "witnessSetVersion": self._version, "outcomes": outcomes}
        coll.update(evidence)
        if certificate is not None:
            addrs = sorted(self._w[w] for w in self._sigs[certificate])
            by_addr = {self._w[w]: s for w, s in self._sigs[certificate].items()}
            coll["submittedSigners"] = addrs
            self._result = {"ok": True, "message": dict(self._msgs[certificate]), "signatures": [by_addr[a] for a in addrs], "collection": coll}
            return
        coll["submittedSigners"] = []
        self._result = {"ok": False, "failure": self._failure_text(evidence), "collection": coll}

    def _outcome(self, w, reference, inconsistent):
        ev = self._events[w]
        o = {"witnessIndex": str(w), "witness": self._w[w], "replies": str(self._replies[w])}
        invalid = [d for k, d in ev if k == "invalid"]
        if any(k == "signed" and d == reference for k, d in ev):
            o["status"] = "signed"
        elif inconsistent or invalid:
            o["status"], o["detail"] = "invalid", EQUIVOCATION_DETAIL if inconsistent else invalid[0]
        elif any(k == "refused" for k, _ in ev):
            code, reason = [d for k, d in ev if k == "refused"][-1]
            o["status"], o["code"] = "refused", code
            if reason is not None:
                o["reason"] = reason
        elif not ev:
            o["status"] = "silent"
        elif any(k == "dissent" for k, _ in ev):
            o["status"], o["detail"] = "dissent", "replied with a message that differs from the one asked"
        else:
            o["status"], o["detail"] = "dissent", "signed a value other than the final reference message"
        out = {"witnessIndex": o["witnessIndex"], "witness": o["witness"], "status": o["status"], "replies": o["replies"]}
        for k in ("code", "reason", "detail"):
            if k in o:
                out[k] = o[k]
        return out

    def _failure_text(self, evidence):
        signed = max((len(s) for s in self._sigs.values()), default=0)
        ad = evidence.get("adopted")
        if ad is not None and ad["reproposal"] == "skipped_deadline":
            return f"the original collection deadline ({self._deadline / 1000:g} s) was reached at the snapshot close; no second round runs and nothing is extended"
        if ad is not None and ad["reproposal"] == "skipped_validity":
            left = (int(ad["message"]["expiresAt"]) * 1000 - (self._now0 * 1000 + self._close_ms)) / 1000
            return f"the adopted value had {max(left, 0):g} s of validity left at the snapshot close (below the 2 s reserve); no re-proposal was sent"
        if ad is not None:
            return f"the adopted value was re-proposed; {signed} of {core.POOL_QUORUM} required distinct valid signatures before the deadline"
        return f"{signed} of {core.POOL_QUORUM} required distinct valid signatures before the deadline"
