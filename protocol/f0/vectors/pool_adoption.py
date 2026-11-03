"""Pool recorded-value adoption rule (agent 2, F0 revision 5): SPECIFICATION REFERENCE, not production code.

Context (SIGNING-RULES section 8, items 7-9). Within one StateCheckpoint collection, witnesses that already signed a value for sequence s refuse a different value with
CONFLICT_PINNED and, in revision 5, return the value they recorded together with the signature they already issued for it. The pool is untrusted and keyless; it may
converge on one value so that the collection can finish, but it can never make an honest witness sign anything: every witness still validates independently and the
conflict rule is unchanged.

A report is a dict {"witness": 0..3, "message": <hashable canonical value>, "validSignature": bool}. The caller (the pool) has ALREADY recovered the signer from the signature
over the digest it computed itself and set validSignature accordingly; this function only decides adoption.

adopt_recorded(reports, sequence) -> the adopted message, or None:
  1. keep reports whose signature verified and whose message is for `sequence` (message[0] is the sequence as a decimal string in this abstraction);
  2. count DISTINCT witnesses per message (a witness repeating a message counts once; a witness reporting two different messages counts once for each);
  3. a message is a candidate iff at least two distinct witnesses report it;
  4. adopt iff there is exactly one candidate; with none or with two or more candidates adopt nothing.
With at most one Byzantine witness (f <= 1) an adopted message was therefore recorded, and independently validated, by at least one honest witness.
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


def adopt_recorded(reports, sequence):
    seen_by = {}
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
        seen_by.setdefault(msg, set()).add(w)
    candidates = [m for m, ws in seen_by.items() if len(ws) >= 2]
    return candidates[0] if len(candidates) == 1 else None
