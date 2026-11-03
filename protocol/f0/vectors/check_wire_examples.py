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


def reports_ok(c, result_checkpoint=None):
    """`collection.recordedReports` = [{witnessIndex, message, signature}] with strictly ascending indices that exist in `outcomes`; `collection.adopted` = {message, reporters}
    where reporters are the indices whose report equals `message`, the rule of pool_adoption.py picks exactly this message from the reports, and (on success) the certificate is
    over this very message. `adopted` requires `recordedReports`."""
    rr, ad = c.get("recordedReports"), c.get("adopted")
    if rr is None and ad is None:
        return True
    if rr is None or not isinstance(rr, list):
        return False
    idx = [r.get("witnessIndex") for r in rr]
    known = {o["witnessIndex"] for o in c["outcomes"]}
    if not (all(isinstance(x, str) and DEC.fullmatch(x) and x in known for x in idx) and idx == sorted(set(idx), key=int)):
        return False
    if not all(set(r) == {"witnessIndex", "message", "signature"} and report_ok({"message": r["message"], "signature": r["signature"]}) for r in rr):
        return False
    if ad is None:
        return True
    if not (isinstance(ad, dict) and set(ad) == {"message", "reporters"} and isinstance(ad["message"], dict) and set(ad["message"]) == CHECKPOINT_KEYS):
        return False
    rp = ad["reporters"]
    if not (isinstance(rp, list) and len(rp) >= 2 and rp == sorted(set(rp), key=int) and rp == [r["witnessIndex"] for r in rr if r["message"] == ad["message"]]):
        return False
    reports = [{"witness": int(r["witnessIndex"]), "message": (r["message"]["sequence"], json.dumps(r["message"], sort_keys=True)), "validSignature": True} for r in rr]
    picked = pool.adopt_recorded(reports, ad["message"]["sequence"])
    if picked is None or picked[1] != json.dumps(ad["message"], sort_keys=True):
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
check("revision 5: the document states the adoption rule (exactly one value with two distinct reporters)", "exactly one value" in text and "two distinct" in text)
print("\nFAILED: %d" % len(fails) if fails else "\nall wire-document checks hold")
sys.exit(1 if fails else 0)
