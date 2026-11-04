"""Consistency check of protocol/f0/SUCCESSOR-WIRE.md (agent 2, F0 revision 3): the JSON examples must obey the document's own tables.

Checks: every example parses; `code` is one of the 21 frozen v1 codes; every `reason` appears in the reason table with the SAME code; collection
invariants (one outcome per witness index in order; success has exactly `quorum` distinct, ascending submitted signers and as many signatures; failure
submits nothing and carries QUORUM_UNAVAILABLE). Documentation consistency only: it does not run the adapter.

    python3 -B -I check_wire_examples.py [path-to-SUCCESSOR-WIRE.md]
"""
import importlib.util
import json
import os
import re
import sys

_spec = importlib.util.spec_from_file_location("pool_adoption", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pool_adoption.py"))
pool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pool)
CHECKPOINT_KEYS = {"sequence", "authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash", "expiresAt"}
SIG = re.compile(r"0x[0-9a-f]{130}")
DEC = re.compile(r"(0|[1-9][0-9]*)")

V1_CODES = {"BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR", "STALE_STATE", "EXPIRED", "REPLAY", "POLICY_DENIED",
            "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER", "WRONG_EPOCH", "NOT_COMMITTED", "ADAPTER_UNAVAILABLE", "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER",
            "NOT_REGISTERED", "ALREADY_REGISTERED", "REVOKED", "MALFORMED", "WRONG_PROFILE"}
STATUSES = {"signed", "refused", "invalid", "silent", "dissent", "duplicate-only"}
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SUCCESSOR-WIRE.md")
text = open(path, encoding="utf-8").read()
fails = []


def check(name, cond):
    if not cond:
        fails.append(name)
    print(("ok   " if cond else "FAIL ") + name)


check("the frozen v1 enum has 21 codes", len(V1_CODES) == 21)
# reason table: rows of the form | `A`, `B` | `CODE` | ... |   (first table in section 1 that maps reasons to codes)
mapping = {}
for line in text.splitlines():
    m = re.match(r"\|\s*((?:`[A-Z_]+`(?:,\s*)?)+)\s*\|\s*`([A-Z_]+)`\s*\|", line)
    if m:
        for r in re.findall(r"`([A-Z_]+)`", m.group(1)):
            mapping[r] = m.group(2)
check("the reason table parsed and names the four internal reasons", {"CONFLICT_PINNED", "QUORUM_UNAVAILABLE", "WITNESS_FAULTED", "PROPOSAL_MISMATCH"} <= set(mapping))
prec = re.search(r"\*\*Precedence at open.*?\n\n", text, re.S).group(0)
named = {w for w in re.findall(r"`([A-Z_]+)`", prec) if w not in V1_CODES}
check("every reason named in the precedence list is in the table", named <= set(mapping) and len(named) >= 14)
check("every reason in the table is named in the precedence list or is an operation-time reason", set(mapping) - named <= {"CONFLICT_PINNED", "PROPOSAL_MISMATCH", "QUORUM_UNAVAILABLE"})
check("every mapped code is a frozen v1 code", all(c in V1_CODES for c in mapping.values()))
check("QUORUM_UNAVAILABLE maps to ADAPTER_UNAVAILABLE and not to INSUFFICIENT_QUORUM", mapping.get("QUORUM_UNAVAILABLE") == "ADAPTER_UNAVAILABLE")
check("no reason maps to POLICY_DENIED or INSUFFICIENT_QUORUM", "POLICY_DENIED" not in mapping.values() and "INSUFFICIENT_QUORUM" not in mapping.values())

examples = [json.loads(b) for b in re.findall(r"```json\n(.*?)\n```", text, re.S)]
check("examples found (>= 4)", len(examples) >= 4)


def report_ok(r):
    """One recorded-value report: closed shape {message, signature}; message is a StateCheckpoint of decimal strings and 0x hashes/addresses."""
    m = r.get("message") if isinstance(r, dict) else None
    return (isinstance(m, dict) and set(m) == CHECKPOINT_KEYS and all(isinstance(v, str) and (DEC.fullmatch(v) or v.startswith("0x")) for v in m.values())
            and isinstance(r.get("signature"), str) and SIG.fullmatch(r["signature"]) is not None)


def _canon(m):
    return json.dumps(m, sort_keys=True)


def reports_ok(c, result_checkpoint=None):
    """Revision 6 (A3-0062 R4/R5). The DECISION SNAPSHOT is `recordedReports` (consistent witnesses, one report each, ascending) plus `inconsistentReports` (witnesses that returned
    two or more different valid values, with every value and signature, ascending); the two lists are disjoint and are EXACTLY the partition pool_adoption.classify computes from the
    snapshot's reports. `lateReports` (reports after the snapshot closed, sorted by witness index then canonical message) are evidence only. `adopted` = {message, reporters} is present
    iff pool_adoption.adopt_recorded(snapshot) yields a value, equals it, `reporters` are the consistent witnesses reporting it, and on success the certificate is over it."""
    rr, inc, late, ad = c.get("recordedReports"), c.get("inconsistentReports"), c.get("lateReports"), c.get("adopted")
    tm = c.get("timing")
    if any(x == [] for x in (rr, inc, late)):              # revision 8 (A2-0054 P-4): a report array is present only when non-empty (one encoding of "none")
        return False
    if rr is None and inc is None and late is None and ad is None:
        return tm is None                                  # timing is present iff pool-retry evidence is present
    rr = [] if rr is None else rr
    inc = [] if inc is None else inc
    known = {o["witnessIndex"] for o in c["outcomes"]}
    if not (isinstance(rr, list) and isinstance(inc, list)):
        return False
    idx = [r.get("witnessIndex") for r in rr]
    iidx = [r.get("witnessIndex") for r in inc]
    if not (all(isinstance(x, str) and DEC.fullmatch(x) and x in known for x in idx + iidx) and idx == sorted(set(idx), key=int) and iidx == sorted(set(iidx), key=int) and not set(idx) & set(iidx)):
        return False
    if not all(set(r) == {"witnessIndex", "message", "signature"} and report_ok({"message": r["message"], "signature": r["signature"]}) for r in rr):
        return False
    for e in inc:
        subs = e.get("reports")
        if not (set(e) == {"witnessIndex", "reports"} and isinstance(subs, list) and len(subs) >= 2 and all(isinstance(x, dict) and set(x) == {"message", "signature"} and report_ok(x) for x in subs)):
            return False
        msgs = [_canon(x["message"]) for x in subs]
        if msgs != sorted(set(msgs)):
            return False                                   # at least two DISTINCT values, in canonical order
    if late is not None:
        if not (isinstance(late, list) and all(isinstance(x, dict) and set(x) == {"witnessIndex", "message", "signature"} and report_ok({"message": x["message"], "signature": x["signature"]}) and x["witnessIndex"] in known for x in late)):
            return False
        keys = [(int(x["witnessIndex"]), _canon(x["message"])) for x in late]
        if keys != sorted(set(keys)):
            return False
    # revision 7 (R6): the timing observations make the snapshot close and the re-proposal gate checkable against the reference's own time functions
    if not (isinstance(tm, dict) and set(tm) == {"ledgerNowAtStart", "proposalExpiresAt", "collectionDeadlineMs", "snapshotClosedAtMs", "snapshotClosedBy"}
            and all(isinstance(tm[k], str) and DEC.fullmatch(tm[k]) for k in ("ledgerNowAtStart", "proposalExpiresAt", "collectionDeadlineMs", "snapshotClosedAtMs"))
            and tm["snapshotClosedBy"] in ("all-replied", "reply-timeout", "deadline")):
        return False
    now0, prop, dl, close, by = int(tm["ledgerNowAtStart"]), int(tm["proposalExpiresAt"]), int(tm["collectionDeadlineMs"]), int(tm["snapshotClosedAtMs"]), tm["snapshotClosedBy"]
    if pool.collection_deadline_ms(now0, prop) != dl:
        return False                                       # the deadline is min(10 s, remaining - 2 s) and a collection exists only when more than 2 s remain
    replied_all = all(o["status"] != "silent" for o in c["outcomes"])
    if pool.snapshot_close(dl, close if by == "all-replied" else None) != (close, by) or (by == "all-replied" and not replied_all):
        return False
    if by == "deadline" and late:
        return False                                       # nothing arriving after the original deadline is collected
    snapshot = [{"witness": int(r["witnessIndex"]), "message": (r["message"]["sequence"], _canon(r["message"])), "validSignature": True} for r in rr]
    snapshot += [{"witness": int(e["witnessIndex"]), "message": (x["message"]["sequence"], _canon(x["message"])), "validSignature": True} for e in inc for x in e["reports"]]
    if not snapshot:
        return ad is None
    seqs = {m[0] for m in (r["message"] for r in snapshot)}
    if len(seqs) != 1:
        return False
    seq = seqs.pop()
    consistent, inconsistent = pool.classify(snapshot, seq)
    if consistent != {int(r["witnessIndex"]): (r["message"]["sequence"], _canon(r["message"])) for r in rr}:
        return False                                       # the wire lists must be exactly the reference's classification
    if inconsistent != {int(e["witnessIndex"]): sorted((x["message"]["sequence"], _canon(x["message"])) for x in e["reports"]) for e in inc}:
        return False
    picked = pool.adopt_recorded(snapshot, seq)
    if (picked is None) != (ad is None):
        return False                                       # adopted present iff the rule adopts, decided on the snapshot only
    if ad is None:
        return True
    if not (isinstance(ad, dict) and set(ad) == {"message", "reporters", "reproposal"} and isinstance(ad["message"], dict) and set(ad["message"]) == CHECKPOINT_KEYS and picked[1] == _canon(ad["message"])):
        return False
    if ad["reproposal"] != pool.reproposal_status(now0, int(ad["message"]["expiresAt"]), close, dl):
        return False                                       # `adopted` is the SELECTION; `reproposal` is the ACTION, gated by the deadline and the 2 s validity reserve
    rp = ad["reporters"]
    if not (isinstance(rp, list) and len(rp) >= 2 and rp == [r["witnessIndex"] for r in rr if r["message"] == ad["message"]]):
        return False
    return result_checkpoint is None or result_checkpoint == ad["message"]


def collection_ok(c, success, sigs=None, checkpoint=None):
    q = int(c["quorum"])
    outs = c["outcomes"]
    ok = [o["witnessIndex"] for o in outs] == [str(i) for i in range(len(outs))] and len(outs) == 4
    ok &= all(o["status"] in STATUSES and re.fullmatch(r"(0|[1-9][0-9]*)", o["replies"]) for o in outs)
    for o in outs:
        if o["status"] == "refused":
            ok &= o.get("code") in V1_CODES and (("reason" not in o) or mapping.get(o["reason"]) == o["code"])
    ok &= reports_ok(c, checkpoint if success else None)
    sub = c["submittedSigners"]
    if success:
        signed = {o["witness"] for o in outs if o["status"] == "signed"}
        ok &= len(sub) == q and len(set(sub)) == q and sub == sorted(sub) and set(sub) <= signed
        ok &= sigs is not None and len(sigs) == q
    else:
        ok &= sub == [] and sum(o["status"] == "signed" for o in outs) < q
    return ok


for i, ex in enumerate(examples):
    tag = f"example {i + 1}"
    check(tag + ": envelope has schemaVersion v2 and ok/result/error", ex.get("schemaVersion") == "v2" and {"ok", "result", "error"} <= set(ex))
    check(tag + ": exactly one of result/error is non-null", (ex["result"] is None) != (ex["error"] is None))
    if ex["error"] is not None:
        e = ex["error"]
        check(tag + ": error code is a frozen v1 code", e["code"] in V1_CODES)
        check(tag + ": error reason (if any) is mapped to this code", "reason" not in e or mapping.get(e["reason"]) == e["code"])
        if "recorded" in e:
            check(tag + ": single-witness `recorded` only with CONFLICT_PINNED, closed shape {message, signature}", e.get("reason") == "CONFLICT_PINNED" and set(e["recorded"]) == {"message", "signature"} and report_ok(e["recorded"]))
        if "collection" in e:
            check(tag + ": collection failure invariants", collection_ok(e["collection"], False) and e.get("reason") == "QUORUM_UNAVAILABLE")
    elif "collection" in ex["result"]:
        check(tag + ": collection success invariants", collection_ok(ex["result"]["collection"], True, ex["result"].get("signatures"), ex["result"].get("checkpoint")))

def _coll(ex):
    return (ex.get("result") or {}).get("collection") or (ex.get("error") or {}).get("collection") or {}


n_rec = sum(1 for ex in examples if _coll(ex).get("recordedReports"))
n_adopted = sum(1 for ex in examples if "adopted" in _coll(ex))
n_single = sum(1 for ex in examples if "recorded" in (ex.get("error") or {}))
check("revision 5: the document carries a collection example with recordedReports (>= 1)", n_rec >= 1)
check("revision 5: the document carries an adoption example (>= 1)", n_adopted >= 1)
check("revision 5: the document carries a single-witness refusal with a recorded value (>= 1)", n_single >= 1)
n_inc = sum(1 for ex in examples if _coll(ex).get("inconsistentReports"))
n_late_adopt = sum(1 for ex in examples if _coll(ex).get("lateReports") and "adopted" in _coll(ex))
unions = {}
for ex in examples:
    c = _coll(ex)
    if c.get("lateReports") and "adopted" in c:
        u = frozenset(_canon(r["message"]) + r["witnessIndex"] for r in (c.get("recordedReports") or []) + (c["lateReports"] or []))
        unions.setdefault(u, set()).add(_canon(c["adopted"]["message"]))
n_reversed = sum(1 for v in unions.values() if len(v) >= 2)
check("revision 6: the document carries an equivocator example with inconsistentReports (>= 1)", n_inc >= 1)
check("revision 6: the document carries a prefix-adoption-then-late-split example (>= 1)", n_late_adopt >= 1)
check("revision 6: the document carries a reversed-arrival-order example: same reports, a different adopted value (>= 1 pair)", n_reversed >= 1)
reps = [(_coll(ex).get("adopted") or {}).get("reproposal") for ex in examples]
n_by_deadline = sum(1 for ex in examples if (_coll(ex).get("timing") or {}).get("snapshotClosedBy") == "deadline")
check("revision 7: the document carries examples of each re-proposal status (sent, skipped_validity, skipped_deadline)", {"sent", "skipped_validity", "skipped_deadline"} <= set(reps))
check("revision 7: the document carries an earlier-hard-stop example (snapshot closed by the deadline) (>= 1)", n_by_deadline >= 1)
check("revision 7: the document defines selection versus action, the effort gate and the hard stop", all(w in text for w in ("selection", "effort gate", "hard stop", "skipped_validity", "skipped_deadline")))
check("revision 6: the document defines the decision snapshot, late reports and inconsistent reporters", all(w in text for w in ("decision snapshot", "late reports", "inconsistent")))
check("revision 5: the document states the adoption rule (exactly one value with two distinct reporters)", "exactly one value" in text and "two distinct" in text)
check("revision 8: the document states that a report array is present only when non-empty", "is present only when non-empty** (revision 8" in text)
check("revision 8: the document states both refusals (an unconfigured witnessIndex is MALFORMED; a declared witnessSetVersion mismatch is STALE_STATE with reason WITNESS_SET_MISMATCH)",
      "not configured in this deployment" in text and "`MALFORMED`" in text and "declared `witnessSetVersion`" in text and text.count("WITNESS_SET_MISMATCH") >= 3)
check("revision 8: the document states that the pool quorum is the constant 3 and when an F deployment is refused", "pool quorum is the constant 3" in text and "threshold is not 2 or 3" in text)
check("revision 8: the document points to EXPORT-LAYOUTS.md for the --binding and --evidence layouts", "are in `EXPORT-LAYOUTS.md` (revision 8).**" in text)
print("\nFAILED: %d" % len(fails) if fails else "\nall wire-document checks hold")
sys.exit(1 if fails else 0)
