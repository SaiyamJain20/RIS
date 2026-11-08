"""Agent 2's verification of the F0 freeze request `communication/F0_FREEZE_CANDIDATE2.json` (A3-0072). Standard library only; reads blobs with `git show` from the local clone
(the commits named in the freeze must be present: `git fetch origin`). Usage (repository root or anywhere inside the clone):
    git show f1fe7e7:communication/F0_FREEZE_CANDIDATE2.json > "$DIR/freeze.json"; python3 -B check_freeze.py "$DIR/freeze.json"
Checks every pin the freeze lists against the real blobs, compares what the freeze says about my files with my working tree, and re-runs my own helper suites to compare the counts that
clarification A2-N5 quotes. Exit 0 only when every check passes."""
import hashlib, json, os, re, subprocess, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
FREEZE_SHA = "f9f0906faf8dbfb9ccd2d06a794c715bb6a3167b6f273a50347742db41196df5"
bad = 0
def rep(ok, text):
    global bad
    bad += (not ok); print(("PASS " if ok else "FAIL ") + text)
def blob(commit, path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{commit}:{path}"], capture_output=True)
    if r.returncode: raise SystemExit(f"cannot read {commit}:{path} (git fetch origin?)")
    return r.stdout
sha = lambda b: hashlib.sha256(b).hexdigest()
raw = open(sys.argv[1], "rb").read()
rep(sha(raw) == FREEZE_SHA, "the freeze JSON has sha256 %s" % FREEZE_SHA[:16])
j = json.loads(raw)
rep(j["freezeAcks"] == [] and j["implementationAuthorized"] is False and j["executionAuthorized"] is False and j["status"].startswith("REQUESTED"), "freezeAcks empty, implementation and execution NOT authorized, status REQUESTED")
oc = j["ownerInputs"]["ownerCommit"]
# protocol F0 files: equal my manifest at the owner commit, equal the blobs there, equal my working tree
mf = {}
for line in blob(oc, "protocol/f0/MANIFEST.sha256").decode().splitlines():
    h, p = line.split(None, 1); mf[p.strip()] = h
pf = j["protocolF0Files"]
rep(len(pf) == 52 and pf == mf, "protocolF0Files (%d) equals my protocol/f0/MANIFEST.sha256 at %s entry for entry" % (len(pf), oc[:7]))
rep(all(sha(blob(oc, p)) == h for p, h in pf.items()), "every protocolF0Files hash equals the blob at the owner commit")
rep(all(os.path.exists(os.path.join(REPO, p)) and sha(open(os.path.join(REPO, p), "rb").read()) == h for p, h in pf.items()), "every protocolF0Files hash equals my CURRENT working-tree file (nothing under protocol/f0 moved since)")
rep(sha(blob(oc, "protocol/f0/MANIFEST.sha256")) == j["ownerInputs"]["files"]["protocol/f0/MANIFEST.sha256"] == "8496c7f3266bdfd90dd0e10cc24b05c99b507a66aea3a49fefc7cee15d3d9d12", "the pinned F0 manifest hash is 8496c7f3.. at the owner commit")
rep(all(sha(blob(oc, p)) == h for p, h in j["ownerInputs"]["files"].items()), "ownerInputs.files (6 of my files) equal the blobs at the owner commit")
elp = j["explicitLayoutPins"]
rep(sorted(elp) == sorted(["protocol/f0/EXPORT-LAYOUTS.md", "protocol/f0/vectors/export_layouts_reference.py", "protocol/f0/vectors/export_layouts_vectors.json", "protocol/f0/vectors/run_export_layout_mutants.py", "protocol/f0/vectors/test_export_layouts.py"])
    and all(pf.get(p) == h for p, h in elp.items()), "explicitLayoutPins names the layout document, reference checker, vectors, mutant runner and tests, each equal to its protocolF0Files hash (my note N-4)")
rep(sha(blob(j["ownerInputs"]["ledgerCommit"], "ledger/f0/A-F1-DESIGN.md")) == j["ownerInputs"]["ledgerDesignSha256"] == "7eed1b29e79144d88d6b5bba33a414e4fcb6dc8fa8cb31262c0742e3baaebfd0", "ledgerDesignSha256 equals ledger/f0/A-F1-DESIGN.md at the ledger commit")
# candidate 2 and the historical base
cm = j["candidateManifest"]
man = blob(cm["commit"], cm["path"])
rep(sha(man) == cm["sha256"] == "0d1a2be44666164deccf19c8c7e942b91938d7577fd6caba569837888b4143e9", "candidateManifest hash is 0d1a2be4.. at its commit")
rep(j["candidateFiles"] == json.loads(man)["files"] and all(sha(blob(cm["commit"], p)) == h for p, h in j["candidateFiles"].items()), "candidateFiles (14) equal the candidate manifest's files and the blobs")
hb = j["historicalBase"]
rep(all(sha(blob(cm["commit"], p)) == h for p, h in hb.items()) and sorted(h[:8] for h in hb.values()) == sorted(["76069506", "2230daf3", "5bf01f05", "1388af02"]), "historicalBase (candidate-8 plan, matrix, CSV, review manifest) equals the blobs: the exact hashes I ACKed in A2-0053")
# ACK records
for a in j["mappingAcks"] + j["candidate8DesignAcks"]:
    ok = sha(blob(a["commit"], a["path"])) == a["sha256"] and sha(blob(a["fileChangingCommit"], a["path"])) == a["sha256"]
    rep(ok, "ACK record %s (%s) hashes correctly at its commit and fileChangingCommit" % (a["messageId"], a.get("scope")))
mine = [a for a in j["mappingAcks"] if a["messageId"] == "A2-0057"][0]
rep(mine["scope"] == "protocol producer/consumer mapping/layout only" and not any("freeze" in a["messageId"].lower() for a in j["mappingAcks"]), "A2-0057 is recorded with its exact scope (mapping/layout only) and not as a freeze ACK")
# cases and numeric plan against the candidate-8 matrix
mat = json.loads(blob(cm["commit"], "evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json"))
ids = [c["id"] for c in mat["cases"]]
rep(j["caseIds"] == ids and len(ids) == 32 and j["caseResults"] == "ALL_32_NOT_RUN" and all(c["executionStatus"] == "NOT_RUN" for c in mat["cases"]), "caseIds are the 32 candidate-8 matrix cases, in order, all NOT_RUN")
import csv, io
rows = list(csv.DictReader(io.StringIO(blob(cm["commit"], "evaluation/evidence/reviews/f0-revision8-20261104/fault-model.csv").decode())))
rep(j["componentCount"] == len(rows) == 14, "componentCount 14 equals the 14 rows of the candidate-8 fault model")
np_m = mat["numericPlan"]; np_f = j["numericPlan"]
rep(all(np_m[k] == v for k, v in np_f.items() if k != "plan"), "numericPlan equals the candidate-8 matrix numericPlan on every listed bound")
# the bounds against my own documents
sr = open(os.path.join(REPO, "protocol/f0/SIGNING-RULES.md")).read(); sw = open(os.path.join(REPO, "protocol/f0/SUCCESSOR-WIRE.md")).read()
wire_text = sw.replace("**", "")
rep(np_f["replyTimeoutSeconds"] == 5 and np_f["collectionTimeoutSeconds"] == 10 and np_f["inclusionReserveSeconds"] == 2
    and ("min(10 s, remaining - 2 s)" in wire_text or "min(10 s, remaining - 2 s)" in sr.replace("**", "")) and "5 s per-witness" in (wire_text + sr),
    "reply 5 s, collection 10 s and the 2 s reserve are the numbers my SUCCESSOR-WIRE and SIGNING-RULES state (min(10 s, remaining - 2 s), 5 s per-witness reply timeout)")
rep(np_f["checkpointWindowSeconds"] == 30 and np_f["checkpointMaxSeconds"] == 60 and np_f["governanceWindowSeconds"] == 60 and np_f["governanceMaxSeconds"] == 120 and np_f["confirmationDepth"] == 0 and np_f["blockCadenceSeconds"] == 1,
    "checkpoint 30/60 s, governance 60/120 s, depth 0 and 1 s cadence match SIGNING-RULES section 6 and the plan")
# clarifications about my notes
cl = j["clarifications"]
rep("065c46db8f3308e531b6b83db4bbf23cbe26f861a983a0af39ac3e86d505aa58" in cl["A2-N1"] and "3f1db2ca0ec2c9aa980121069ea2cc65d813df7c2d69f6109491c5f497247f47" in cl["A2-N1"], "A2-N1 names both wire hashes correctly (revision-7 provenance versus the active revision-8 pin)")
for n in ("A2-N1", "A2-N2", "A2-N3", "A2-N4", "A2-N5"): rep(n in cl, "clarification %s is present" % n)
# A2-N5: my current counts, by running my own suites on the current tree
def run(*args):
    return subprocess.run([sys.executable, "-B", "-I", *args], capture_output=True, text=True, cwd=REPO)
V = os.path.join(REPO, "protocol", "f0", "vectors")
counts = {}
for name, script in (("d50", "test_d50_reference.py"), ("layouts", "test_export_layouts.py"), ("pool", "test_pool_adoption.py")):
    r = run(os.path.join(V, script)); counts[name] = (r.returncode, sum(1 for l in r.stdout.splitlines() if l.startswith("ok ")))
for name, script in (("d50m", "run_d50_r5_mutants.py"), ("layoutsm", "run_export_layout_mutants.py"), ("poolm", "run_pool_adoption_mutants.py"), ("wire", "run_wire_corruptions.py")):
    r = run(os.path.join(V, script)); m = re.search(r"detected (\d+) of (\d+)", r.stdout); counts[name] = (r.returncode, int(m.group(1)) if m else -1, int(m.group(2)) if m else -1)
rep(counts["d50"] == (0, 126) and counts["d50m"] == (0, 15, 15), "D50 126 expectations and 15 of 15 mutants (A2-N5 says 126 / 15)")
rep(counts["wire"] == (0, 36, 36), "wire 36 of 36 corruptions (A2-N5 says 36)")
rep(counts["layouts"] == (0, 76) and counts["layoutsm"] == (0, 29, 29), "layouts 76 expectations and 29 of 29 mutants (A2-N5 says 76 / 29)")
rep(counts["pool"] == (0, 53) and counts["poolm"] == (0, 19, 19), "pool adoption 53 expectations and 19 of 19 mutants (A2-N5 says 53 / 19)")
# the freeze states the right limits
rep("same model family" in j["evidenceLimits"] and j["preservation"].find("G locked") >= 0, "the freeze states that the reviews are correlated and that G stays locked")
print("\nfailures: %d" % bad); sys.exit(1 if bad else 0)
