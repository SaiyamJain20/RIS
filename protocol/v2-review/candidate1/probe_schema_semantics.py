"""Informational probe: which of BOUNDARY's mandatory semantic rules does the schema itself enforce? Each probe corrupts one candidate example in one way and
reports whether AdapterResponse still accepts it. ACCEPTS means the rule is carried by BOUNDARY/the runtime only (expected for rules that need recovery or recomputation).
Exit 0 always."""
import copy, json, sys
from common import *
from jsonschema import Draft202012Validator
root = proposal(sys.argv); D = load(root, "hmbc.schema.json")["$defs"]
ok = Draft202012Validator({"$ref": "#/$defs/AdapterResponse", "$defs": D})
w = load(root, "vectors/wire.json")["responses"]; su = load(root, "vectors/success.json")
col = lambda r: r["error"]["collection"]
fail = [x for x in w if x.get("error") and "collection" in x["error"]][0]
late = [x for x in w if x.get("error") and "collection" in x["error"] and "lateReports" in x["error"]["collection"]][0]
succ = su[0]["response"]
def p(name, base, fn):
    r = copy.deepcopy(base); fn(r); print("%-9s %s" % ("REJECTS" if not ok.is_valid(r) else "ACCEPTS", name))
def silent_replies(r):
    for o in col(r)["outcomes"]:
        if o["status"] == "silent": o["replies"] = "2"; return
def nonsilent_zero(r):
    for o in col(r)["outcomes"]:
        if o["status"] != "silent": o["replies"] = "0"; return
p("silent outcome with replies=2", fail, silent_replies)
p("non-silent outcome with replies=0", fail, nonsilent_zero)
p("outcomes in reverse index order", fail, lambda r: col(r)["outcomes"].reverse())
p("outcome address differs from the fixture mapping (runtime)", fail, lambda r: col(r)["outcomes"][0].__setitem__("witness", "0x" + "11" * 20))
p("success certificate with 2 signatures", succ, lambda r: r["result"]["signatures"].pop())
p("success certificate signatures reversed (needs recovery)", succ, lambda r: r["result"]["signatures"].reverse())
p("submittedSigners differs from recovered signers (needs recovery)", succ, lambda r: r["result"]["collection"]["submittedSigners"].__setitem__(0, "0x" + "22" * 20))
p("timing.collectionDeadlineMs wrong (recompute)", late, lambda r: col(r)["timing"].__setitem__("collectionDeadlineMs", "9000"))
p("adopted.reproposal wrong (recompute)", late, lambda r: col(r)["adopted"].__setitem__("reproposal", "skipped_validity"))
p("lateReports: [] with timing present (empty vs absent)", late, lambda r: col(r).__setitem__("lateReports", []))
p("adopted.reporters not ascending", late, lambda r: col(r)["adopted"].__setitem__("reporters", ["1", "0"]))
p("adopted.reporters duplicate", late, lambda r: col(r)["adopted"].__setitem__("reporters", ["0", "0"]))
p("recordedReports not ascending", late, lambda r: col(r)["recordedReports"].reverse())
