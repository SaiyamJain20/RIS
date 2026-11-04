"""Corruption check of the successor wire document (agent 2, F0 revision 7). Standard library only.

Each corruption changes ONE thing in a copy of `SUCCESSOR-WIRE.md` (a JSON example parsed, modified and re-serialised, or a text replacement that must match exactly once; a
modification that changes nothing is refused as a no-op) and runs `check_wire_examples.py` on the copy. A corruption counts as DETECTED only when the checker exits non-zero; the
checker's `FAIL` lines are recorded so that the detecting example can be compared with the damaged one (the checker reports per example, not per invariant). The unmodified
document is run first as a control and must pass.

Usage (repository root):   python3 -B -I protocol/f0/vectors/run_wire_corruptions.py > protocol/f0/evidence/wire-mutants.txt
Exit 0 only when every corruption is detected.
"""
import copy
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
F0 = os.path.dirname(HERE)
CHECKER = os.path.join(HERE, "check_wire_examples.py")
S = tempfile.mkdtemp(prefix="wire-corruption-")
src = open(os.path.join(F0, "SUCCESSOR-WIRE.md")).read()
blocks=re.findall(r"```json\n(.*?)\n```",src,re.S)
assert len(blocks)==12, len(blocks)
def run(name, text):
    p=os.path.join(S,"w.md"); open(p,"w").write(text)
    r=subprocess.run([sys.executable,"-B","-I",CHECKER,p],capture_output=True,text=True)
    out=(r.stdout+r.stderr).strip().splitlines()
    first=" | ".join(l.strip() for l in out if l.startswith("FAIL ") )
    return ("DETECTED " if r.returncode!=0 else "SURVIVED ")+name+("\n    checker said: "+first[:240] if r.returncode!=0 else ""), r.returncode!=0
results=[]
_c=run("control: unmodified document", src)
assert not _c[1], "CONTROL FAILED: the unmodified document does not pass the checker"
print("control: unmodified document passes the checker")
def block_mut(name, idx, fn):
    d=json.loads(blocks[idx]); before=json.dumps(d,sort_keys=True); fn(d)
    assert json.dumps(d,sort_keys=True)!=before, ("no-op mutation", name)
    new=json.dumps(d,separators=(",",":"))
    assert src.count(blocks[idx])==1, ("anchor not unique", name)
    results.append(run(name, src.replace(blocks[idx], new)))
def text_mut(name, old, new):
    assert src.count(old)==1,(name,src.count(old)); results.append(run(name, src.replace(old,new)))
def coll(d): return d["error"]["collection"] if "error" in d else d["result"]["collection"]
text_mut("W1 timeout uses INSUFFICIENT_QUORUM", '"error":{"code":"ADAPTER_UNAVAILABLE","reason":"QUORUM_UNAVAILABLE","message":"2 of 3','"error":{"code":"INSUFFICIENT_QUORUM","reason":"QUORUM_UNAVAILABLE","message":"2 of 3')
block_mut("W2 failure submits a signer",1,lambda d:d["error"]["collection"].__setitem__("submittedSigners",["0x1000000000000000000000000000000000000001"]))
def swap_outcomes(d):
    o=d["result"]["collection"]["outcomes"]; o[0],o[1]=o[1],o[0]
block_mut("W3 outcome order swapped (first example)",0,swap_outcomes)
text_mut("W4 invalid code in table","| `WITNESS_FAULTED` | `ADAPTER_UNAVAILABLE` |","| `WITNESS_FAULTED` | `BAD_CODE_NAME` |")
block_mut("W5 success with 2 submitted signers",0,lambda d:d["result"]["collection"].__setitem__("submittedSigners",d["result"]["collection"]["submittedSigners"][:2]))
block_mut("W6 adopted.reporters names a witness whose report differs",4,lambda d:d["result"]["collection"]["adopted"].__setitem__("reporters",["0","1","2"]))
block_mut("W7 ambiguous split example claims an adoption",5,lambda d:d["error"]["collection"].__setitem__("adopted",{"message":d["error"]["collection"]["recordedReports"][0]["message"],"reporters":["0","1"],"reproposal":"sent"}))
block_mut("W8 single-witness recorded with the wrong reason",6,lambda d:d["error"].__setitem__("reason","PROPOSAL_MISMATCH"))
block_mut("W9 recorded signature has the wrong length",4,lambda d:d["result"]["collection"]["recordedReports"][1].__setitem__("signature","0xcdcd"))
def unsort(d):
    r=d["result"]["collection"]["recordedReports"]; r[0],r[1]=r[1],r[0]
block_mut("W10 recordedReports not in ascending order",4,unsort)
block_mut("W11 success certificate over a different checkpoint than adopted.message",4,lambda d:d["result"]["checkpoint"].__setitem__("sourceBlockNumber","249"))
def late_inside(d):
    c=d["error"]["collection"]; c["recordedReports"]+=c.pop("lateReports")
block_mut("W12 late split kept INSIDE recordedReports while adopted is retained (the R5 failure)",7,late_inside)
block_mut("W13 a witness listed both as consistent and inconsistent",9,lambda d:d["error"]["collection"]["inconsistentReports"][0].__setitem__("witnessIndex","0"))
def ident(d):
    e=d["error"]["collection"]["inconsistentReports"][0]; e["reports"][1]["message"]=e["reports"][0]["message"]
block_mut("W14 inconsistent entry with two IDENTICAL messages",9,ident)
def unsort_late(d):
    l=d["error"]["collection"]["lateReports"]; l[0],l[1]=l[1],l[0]
block_mut("W15 lateReports out of canonical order",7,unsort_late)
block_mut("W16 adoption omitted although the snapshot adopts (prefix example)",7,lambda d:d["error"]["collection"].pop("adopted"))
block_mut("W17 adoption claimed on the equivocator snapshot (rule yields none)",9,lambda d:d["error"]["collection"].__setitem__("adopted",{"message":d["error"]["collection"]["recordedReports"][0]["message"],"reporters":["0","3"],"reproposal":"sent"}))
def wrong_adopted(d):
    c=d["error"]["collection"]; c["adopted"]["message"]=copy.deepcopy(c["lateReports"][0]["message"])
block_mut("W18 reversed example names the LATE value as adopted",8,wrong_adopted)
# revision 7 (R6)
block_mut("W19 reproposal says sent although only 1 s of validity was left (the R6 case)",10,lambda d:d["error"]["collection"]["adopted"].__setitem__("reproposal","sent"))
block_mut("W20 reproposal says skipped_validity although 25 s of validity were left",4,lambda d:d["result"]["collection"]["adopted"].__setitem__("reproposal","skipped_validity"))
block_mut("W21 reproposal says sent on the earlier hard stop",11,lambda d:d["error"]["collection"]["adopted"].__setitem__("reproposal","sent"))
block_mut("W22 timing missing on a pool-retry example",7,lambda d:d["error"]["collection"].pop("timing"))
block_mut("W23 timing present on an example without pool-retry evidence",0,lambda d:d["result"]["collection"].__setitem__("timing",{"ledgerNowAtStart":"1791521470","proposalExpiresAt":"1791521500","collectionDeadlineMs":"10000","snapshotClosedAtMs":"5000","snapshotClosedBy":"reply-timeout"}))
block_mut("W24 collectionDeadlineMs is not min(10 s, remaining - 2 s)",4,lambda d:d["result"]["collection"]["timing"].__setitem__("collectionDeadlineMs","9000"))
block_mut("W25 hard stop claims it closed by the reply-timeout",11,lambda d:d["error"]["collection"]["timing"].__setitem__("snapshotClosedBy","reply-timeout"))
def late_on_hard_stop(d):
    c=d["error"]["collection"]; m=c["recordedReports"][0]["message"]
    new={}
    for k,v in c.items():
        if k=="timing": new["lateReports"]=[{"witnessIndex":"2","message":m,"signature":"0x"+"ef"*65}]
        new[k]=v
    d["error"]["collection"]=new
block_mut("W26 a late report on the hard-stop example (nothing after the deadline is collected)",11,late_on_hard_stop)
block_mut("W27 adopted omitted on the skipped_validity example (the OTHER reading of R6)",10,lambda d:d["error"]["collection"].pop("adopted"))
def claim_all_replied(d):
    t=d["result"]["collection"]["timing"]; t["snapshotClosedBy"]="all-replied"; t["snapshotClosedAtMs"]="1200"
block_mut("W28 all-replied claimed while a witness was silent",4,claim_all_replied)
block_mut("W29 snapshot closed after the original deadline",11,lambda d:d["error"]["collection"]["timing"].__setitem__("snapshotClosedAtMs","3000"))
block_mut("W30 adopted.reproposal missing",7,lambda d:d["error"]["collection"]["adopted"].pop("reproposal"))
det=sum(ok for _,ok in results)
for line,_ in results: print(line)
print(f"detected {det} of {len(results)} (skipped 0)")
import shutil
shutil.rmtree(S, ignore_errors=True)
sys.exit(0 if det == len(results) else 1)
