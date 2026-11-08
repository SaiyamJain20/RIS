"""Pool decision core: recorded-value adoption, the effort-gate time functions and the assembly of the wire evidence (HMBC2020 successor, F task 3 slice 3a).

PAPER-DERIVED RECONSTRUCTION. This is the production port of the pinned specification reference `protocol/f0/vectors/pool_adoption.py` (SIGNING-RULES section 8; SUCCESSOR-WIRE "Recorded-value
reports and adoption") plus the assembly of the evidence members that rule produces on the wire. It is PURE: no clock, no network, no key, no file. The pool orchestration (a later slice) hands it
reports whose signatures it has ALREADY recovered over the digest it computed itself; this module only decides adoption, evaluates the effort gate from numbers it is given, and shapes evidence.
It never makes a witness sign anything, and nothing here is a measured property of a running pool.

Report (input):   {"witness": 0..3, "message": {str: str, with "sequence"}, "signature": str, "validSignature": bool}
  A report whose `validSignature` is False is IGNORED: only its witness index and the flag are read, so a Byzantine witness cannot make the pool raise by sending garbage (the reference never
  reads such a message either). A report with `validSignature` True must be well formed or the caller has a bug and PoolCoreError is raised.

Explicit choices the reference leaves open (they are choices, not discovered behaviour):
  * A message is a value by its canonical content `json.dumps(message, sort_keys=True)` (the order the wire checker uses for `inconsistentReports` and `lateReports`).
  * One signature is kept per (witness, value): the lexicographically smallest, so the evidence does not depend on arrival order. Signatures are evidence, never an input to adoption.
  * Only valid reports for the collection's sequence reach any evidence list; reports with an invalid signature or another sequence are dropped (the reference's `classify` drops them too).
  * Time inputs are non-negative integers (the reference accepts any integer).
  * `evidence` refuses late reports when the snapshot closed AT the original deadline: nothing arriving after it is collected, so a late report cannot exist there.
"""
from __future__ import annotations

import json
import re

REPLY_TIMEOUT_MS = 5000
COLLECTION_CAP_MS = 10000
RESERVE_S = 2
WITNESS_COUNT = 4
POOL_QUORUM = 3

_DEC = re.compile(r"(0|[1-9][0-9]*)")
_REPORT_KEYS = {"witness", "message", "signature", "validSignature"}


class PoolCoreError(ValueError):
    """A caller bug: a malformed report list, sequence or time input. Never raised for the content of an invalid-signature report."""


def canonical_message(message):
    return json.dumps(message, sort_keys=True)


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise PoolCoreError(f"{what} must be a non-negative integer")
    return v


def _sequence(sequence):
    return _int(sequence, "sequence")


def _reports(reports):
    if not isinstance(reports, list):
        raise PoolCoreError("reports must be a list")
    for r in reports:
        if not isinstance(r, dict) or set(r) != _REPORT_KEYS:
            raise PoolCoreError("report must be exactly {witness, message, signature, validSignature}")
        w = r["witness"]
        if isinstance(w, bool) or not isinstance(w, int) or not 0 <= w < WITNESS_COUNT:
            raise PoolCoreError(f"witness index must be an integer 0..{WITNESS_COUNT - 1}")
        if not isinstance(r["validSignature"], bool):
            raise PoolCoreError("validSignature must be a boolean")
        if not r["validSignature"]:
            continue
        m = r["message"]
        if not isinstance(m, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in m.items()):
            raise PoolCoreError("a valid report's message must be a dict of strings")
        if "sequence" not in m:
            raise PoolCoreError("a valid report's message must carry a sequence")
        if not isinstance(r["signature"], str):
            raise PoolCoreError("a valid report's signature must be a string")
    return reports


def _kept(reports, sequence):
    """{witness: {canonical value: (message, smallest signature)}} for the valid reports of this sequence."""
    seq = str(_sequence(sequence))
    kinds = {}
    for r in _reports(reports):
        if not r["validSignature"] or r["message"]["sequence"] != seq:
            continue
        slot = kinds.setdefault(r["witness"], {})
        c = canonical_message(r["message"])
        if c not in slot or r["signature"] < slot[c][1]:
            slot[c] = (r["message"], r["signature"])
    return kinds


def _report(entry):
    return {"message": dict(entry[0]), "signature": entry[1]}


def classify(reports, sequence):
    """-> (consistent, inconsistent). consistent = {w: {"message", "signature"}} for witnesses with ONE distinct value; inconsistent = {w: [{"message", "signature"}, ...]} for witnesses with two or
    more, in canonical order. Exactly the partition the wire carries as `recordedReports` and `inconsistentReports`."""
    kinds = _kept(reports, sequence)
    consistent = {w: _report(next(iter(d.values()))) for w, d in sorted(kinds.items()) if len(d) == 1}
    inconsistent = {w: [_report(d[c]) for c in sorted(d)] for w, d in sorted(kinds.items()) if len(d) >= 2}
    return consistent, inconsistent


def _adopt(consistent):
    seen_by = {}
    for w, rep in consistent.items():
        seen_by.setdefault(canonical_message(rep["message"]), set()).add(w)
    candidates = [c for c, ws in seen_by.items() if len(ws) >= 2]
    if len(candidates) != 1:
        return None
    for rep in consistent.values():
        if canonical_message(rep["message"]) == candidates[0]:
            return dict(rep["message"])
    return None


def adopt_recorded(reports, sequence):
    """The adopted message (a copy), or None: among the CONSISTENT witnesses exactly one value with at least two distinct reporters."""
    return _adopt(classify(reports, sequence)[0])


def decide(snapshot, late, sequence):
    """The decision is a function of the SNAPSHOT only; late reports are shape-checked and are never an input."""
    classify(late, sequence)
    return adopt_recorded(snapshot, sequence)


# ---- the time functions (integers; seconds are target-ledger seconds, durations are host-monotonic milliseconds) ---------------------------------------------------------------------------
def collection_deadline_ms(ledger_now_at_start, proposal_expires_at):
    remaining = _int(proposal_expires_at, "proposal_expires_at") - _int(ledger_now_at_start, "ledger_now_at_start")
    if remaining <= RESERVE_S:
        return None
    return min(COLLECTION_CAP_MS, (remaining - RESERVE_S) * 1000)


def snapshot_close(deadline_ms, all_replied_at_ms):
    d = _int(deadline_ms, "deadline_ms")
    limit = min(REPLY_TIMEOUT_MS, d)
    if all_replied_at_ms is not None and _int(all_replied_at_ms, "all_replied_at_ms") < limit:
        return all_replied_at_ms, "all-replied"
    if d <= REPLY_TIMEOUT_MS:
        return d, "deadline"
    return REPLY_TIMEOUT_MS, "reply-timeout"


def reproposal_status(ledger_now_at_start, adopted_expires_at, snapshot_closed_at_ms, deadline_ms):
    now0, exp = _int(ledger_now_at_start, "ledger_now_at_start"), _int(adopted_expires_at, "adopted_expires_at")
    close, d = _int(snapshot_closed_at_ms, "snapshot_closed_at_ms"), _int(deadline_ms, "deadline_ms")
    if close >= d:
        return "skipped_deadline"
    remaining_ms = exp * 1000 - (now0 * 1000 + close)
    return "skipped_validity" if remaining_ms <= RESERVE_S * 1000 else "sent"


# ---- evidence assembly ------------------------------------------------------------------------------------------------------------------------------------------------------------------
def evidence(snapshot, late, sequence, *, ledger_now_at_start, proposal_expires_at, all_replied_at_ms=None):
    """The collection members the adoption rule produces, as wire values: any of `recordedReports`, `inconsistentReports`, `lateReports`, `adopted` and `timing`. An array is present only when
    non-empty; `timing` is present iff at least one of the four others is. `adopted` is the SELECTION (a function of the snapshot alone); `adopted.reproposal` is the ACTION gated by the effort gate.
    `all_replied_at_ms` is the host-monotonic time at which the last of the four witnesses had replied, or None when not all did before the snapshot closed."""
    seq = _sequence(sequence)
    now0 = _int(ledger_now_at_start, "ledger_now_at_start")
    prop = _int(proposal_expires_at, "proposal_expires_at")
    all_at = None if all_replied_at_ms is None else _int(all_replied_at_ms, "all_replied_at_ms")
    deadline = collection_deadline_ms(now0, prop)
    if deadline is None:
        raise PoolCoreError("no collection exists: 2 s or less of validity remain")
    close, by = snapshot_close(deadline, all_at)
    if by == "deadline" and late:
        raise PoolCoreError("the snapshot closed at the original deadline: nothing after it is collected, so there can be no late report")
    consistent, inconsistent = classify(snapshot, seq)
    late_kept = _kept(late, seq)
    out = {}
    if consistent:
        out["recordedReports"] = [{"witnessIndex": str(w), "message": r["message"], "signature": r["signature"]} for w, r in consistent.items()]
    if inconsistent:
        out["inconsistentReports"] = [{"witnessIndex": str(w), "reports": rs} for w, rs in inconsistent.items()]
    late_list = [{"witnessIndex": str(w), "message": dict(d[c][0]), "signature": d[c][1]} for w, d in sorted(late_kept.items()) for c in sorted(d)]
    if late_list:
        out["lateReports"] = late_list
    picked = _adopt(consistent)
    if picked is not None:
        expires = picked.get("expiresAt")
        if not isinstance(expires, str) or _DEC.fullmatch(expires) is None:
            raise PoolCoreError("the adopted message needs a decimal expiresAt")
        c = canonical_message(picked)
        out["adopted"] = {"message": picked, "reporters": [str(w) for w, r in consistent.items() if canonical_message(r["message"]) == c],
                          "reproposal": reproposal_status(now0, int(expires), close, deadline)}
    if out:
        out["timing"] = {"ledgerNowAtStart": str(now0), "proposalExpiresAt": str(prop), "collectionDeadlineMs": str(deadline), "snapshotClosedAtMs": str(close), "snapshotClosedBy": by}
    return out
