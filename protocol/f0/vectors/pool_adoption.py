"""Pool recorded-value adoption rule (agent 2, F0 revision 6): SPECIFICATION REFERENCE, not production code.

Context (SIGNING-RULES section 8, items 7-12). Within one StateCheckpoint collection, witnesses that already signed a value for sequence s refuse a different value with
CONFLICT_PINNED and return the value they recorded together with the signature they already issued for it. The pool is untrusted and keyless; it may converge on one value
so that the collection can finish, but it can never make an honest witness sign anything: every witness still validates independently and the conflict rule is unchanged.

A report is a dict {"witness": 0..3, "message": <hashable canonical value>, "validSignature": bool}. The caller (the pool) has ALREADY recovered the signer from the signature
over the digest it computed itself and set validSignature accordingly; this module only decides adoption.

classify(reports, sequence) -> (consistent, inconsistent)           [revision 6, R4]
  keep reports whose signature verified and whose message is for `sequence` (message[0] is the sequence as a decimal string in this abstraction);
  a witness whose kept reports contain ONE distinct message is CONSISTENT (repeats of the same message are one report); a witness whose kept reports contain TWO OR MORE
  distinct messages is INCONSISTENT. consistent = {witness: message}; inconsistent = {witness: sorted list of its distinct messages}.
  This is exactly the partition the wire carries: `recordedReports` (consistent, one per witness) and `inconsistentReports` (evidence).

adopt_recorded(reports, sequence) -> the adopted message, or None:
  inconsistent witnesses are EXCLUDED (an order-independent policy; a first-report projection would depend on arrival order). Among the consistent witnesses, a message is a
  candidate iff at least two distinct witnesses report it; adopt iff there is exactly one candidate; with none or with two or more adopt nothing.
  With at most one Byzantine witness (f <= 1) an adopted message was recorded, and independently validated, by at least one honest witness.

decide(snapshot, late, sequence) -> the adopted message, or None                [revision 6, R5]
  The decision is a function of the SNAPSHOT only. `late` holds the reports that arrived after the snapshot closed: they are evidence, never an input. They cannot cancel an
  adoption and cannot create one. Two different arrival orders may therefore adopt different values; each was recorded by an honest witness, so either is safe.

Revision 7 (R6): SELECTION VERSUS ACTION. `adopted` records the SELECTION: a pure function of the snapshot, with no clock input. Whether the pool then RE-PROPOSES the selected value is a
separate ACTION with its own recorded status, `reproposal`, decided by the time functions below. The gate is an EFFORT gate on a host-time estimate (one target-ledger read at the start
plus the host-monotonic time elapsed); it never declares a signature dead. Witnesses stay the authority: they validate against ledger time and refuse an expired value themselves, so an
estimate that errs either way costs availability, never safety.

collection_deadline_ms(now0, proposal_expires_at)      -> ms, or None when 2 s or less remain (refused with EXPIRED before any witness is contacted)
snapshot_close(deadline_ms, all_replied_at_ms)          -> (ms, by) with by in {"all-replied", "reply-timeout", "deadline"}; the close never exceeds min(5000, deadline_ms)
reproposal_status(now0, adopted_expires_at, close_ms, deadline_ms) -> "skipped_deadline" | "skipped_validity" | "sent"
  A snapshot that closes AT the original deadline is still a snapshot: the rule applies to the reports received so far, the value (if any) is selected, and no second round runs; the
  deadline is never extended and nothing arriving after it is collected.
"""
from __future__ import annotations


class AdoptionError(ValueError):
    pass


def refuses(fn) -> bool:
    try:
        fn()
    except AdoptionError:
        return True
    except Exception:  # noqa: BLE001 - another exception class is not the documented refusal
        return False
    return False


def classify(reports, sequence):
    kinds = {}
    for r in reports:
        if not isinstance(r, dict) or set(r) != {"witness", "message", "validSignature"}:
            raise AdoptionError("report must be exactly {witness, message, validSignature}")
        w = r["witness"]
        if isinstance(w, bool) or not isinstance(w, int) or not 0 <= w <= 3:
            raise AdoptionError("witness index must be an integer 0..3")
        if not isinstance(r["validSignature"], bool):
            raise AdoptionError("validSignature must be a boolean")
        if not r["validSignature"]:
            continue
        msg = r["message"]
        if msg[0] != str(sequence):
            continue
        kinds.setdefault(w, set()).add(msg)
    consistent = {w: next(iter(ms)) for w, ms in kinds.items() if len(ms) == 1}
    inconsistent = {w: sorted(ms) for w, ms in kinds.items() if len(ms) >= 2}
    return consistent, inconsistent


def adopt_recorded(reports, sequence):
    consistent, _ = classify(reports, sequence)
    seen_by = {}
    for w, msg in consistent.items():
        seen_by.setdefault(msg, set()).add(w)
    candidates = [m for m, ws in seen_by.items() if len(ws) >= 2]
    return candidates[0] if len(candidates) == 1 else None


def decide(snapshot, late, sequence):
    classify(late, sequence)                      # late reports are validated for shape but are never an input to the decision
    return adopt_recorded(snapshot, sequence)


# ---- revision 7: time functions (all integers; seconds are target-ledger seconds, durations are host-monotonic milliseconds) --------------------------------------------------
REPLY_TIMEOUT_MS = 5000
COLLECTION_CAP_MS = 10000
RESERVE_S = 2


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int):
        raise AdoptionError(f"{what} must be an integer")
    return v


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
