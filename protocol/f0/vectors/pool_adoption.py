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
