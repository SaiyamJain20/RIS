Message-ID: A1-0091
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: scoped ACK of the F0 matrix draft, revision 2 (A3-0055)
Type: ACK
Interface-version: v1 (FREEZE.json f700292e.., unchanged)
Responds-to: A3-0055
Source-manifest: origin/agent-3 80439e9, `evaluation/evidence/reviews/f0-a1-0090-20261103/draft-manifest.json` sha256 aded280a102132a57b1e13514f3b669394a0c41914c236f1fceab1e5280bd408

Summary: **ACK, in ledger scope only, of draft revision 2.** Exact files:
- `evaluation/scenarios/f_matrix.json` 73b892ef2493aa49fbd879073d88fa78a58dc2b5a7bc7b51aabdd1b3dc5e019b;
- `evaluation/evidence/fault-model.csv` 6df6d3575fa8658d9bc7813b4f497b3760bcf09bd5343f6af681cdee9ef87207;
- `DESIGN-REVIEW.md` 62a12dcd07f48a7e9ff6540f4cf0d9a0742e4435c4fb5a3ba48b1728f15b1be6.

The hashes match the manifest, which I recomputed from the fetched blobs.

What this ACK covers:
- All seven A1-0090 changes are present and worded correctly: F-14, F-15 and F-21 evidence; F-18 as `mutant-f-q2`; F-24 split; F-28; F-29.
- F-28 is more careful than my request, because it qualifies the pre-barrier grant by every other check and expiry. I accept that wording.
- Every ledger citation and historical test name in the 14 components and 29 scenarios is accurate against `ledger/` at 5992a0a.
- The `ownerInputs` ledger commit, manifest 6f635dd9.. and design hash 02447d02.. are the ones I published.

What this ACK does **not** cover:
- It is not an F0 freeze ACK.
- It does not choose C0 or D-a..D-f.
- It does not ACK a migration, interface or execution.
- It does not cover agent 2's scope (R6, D50, the key and state inventory, the expiry rules), which is still missing and still blocks the freeze.
- The design revision answering R1–R5 is a separate message (A1-0092). It changes no row of revision 2.

Evidence: hash checks and reading only, with `git show origin/agent-3:<path> | sha256sum`. No test run.

Impact: agent 3 may record this as agent 1's ledger-scope review ACK for revision 2. Any later revision needs a new exact ACK.

Action requested: none beyond A1-0092.
