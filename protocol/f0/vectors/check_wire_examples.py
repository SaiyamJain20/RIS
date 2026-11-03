"""Consistency check of protocol/f0/SUCCESSOR-WIRE.md (agent 2, F0 revision 3): the JSON examples must obey the document's own tables.

Checks: every example parses; `code` is one of the 21 frozen v1 codes; every `reason` appears in the reason table with the SAME code; collection
invariants (one outcome per witness index in order; success has exactly `quorum` distinct, ascending submitted signers and as many signatures; failure
submits nothing and carries QUORUM_UNAVAILABLE). Documentation consistency only: it does not run the adapter.

    python3 -B -I check_wire_examples.py [path-to-SUCCESSOR-WIRE.md]
"""
import json
import os
import re
import sys

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


def collection_ok(c, success, sigs=None):
    q = int(c["quorum"])
    outs = c["outcomes"]
    ok = [o["witnessIndex"] for o in outs] == [str(i) for i in range(len(outs))] and len(outs) == 4
    ok &= all(o["status"] in STATUSES and re.fullmatch(r"(0|[1-9][0-9]*)", o["replies"]) for o in outs)
    for o in outs:
        if o["status"] == "refused":
            ok &= o.get("code") in V1_CODES and (("reason" not in o) or mapping.get(o["reason"]) == o["code"])
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
        if "collection" in e:
            check(tag + ": collection failure invariants", collection_ok(e["collection"], False) and e.get("reason") == "QUORUM_UNAVAILABLE")
    elif "collection" in ex["result"]:
        check(tag + ": collection success invariants", collection_ok(ex["result"]["collection"], True, ex["result"].get("signatures")))

print("\nFAILED: %d" % len(fails) if fails else "\nall wire-document checks hold")
sys.exit(1 if fails else 0)
