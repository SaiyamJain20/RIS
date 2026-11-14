# F case coverage map (32 cases) — agent 3, 2026-11-14

Merges two owner inventories onto my own matrix (`reviews/f0-revision8-20261104/f_matrix.json`, 2230daf3..):
agent 1's ledger-scope A1-0127 (ledger 85c59f5: fresh `forge test` 316/316, mutant check exit 0, per agent 1)
and agent 2's protocol-scope A2-0081 (hook gaps at that time). `coverage.csv` has one row per case.
Both inventories are one author's reading each (correlated); neither is an F result.
ALL 32 CASES REMAIN NOT_RUN: no runner, no execution FREEZE, no ACKs; Gate F NOT_RUN; G locked.

Ledger scope (A1-0127): 22 cases have the ledger branch tested under REPAIRED_F by owner tests; FL-9 is accepted
by design (trust assumption, the oracle should expect a grant); F-17 and F-24 are outside the bound (scratch /
historical evidence); 7 have no ledger role (F-13, F-19, F-25, F-26, F-27, F-31, F-32). No new ledger code needed.
Protocol scope (A2-0081): 12 had a hook gap (G1 real-process Byzantine, G2 divergent view, G3 source mutants);
agent 2 has since delivered TEST-ONLY G1/G2/G3 (A2-0083) but I have not checked them case by case; 7 built at
real-process level; 11 ledger/relay/evaluator/fixture work with real components; 2 analysis only.
Not claimed: that any case's oracle accepts what the components produce.

Correction found while merging (agent 1's catch): my F matrix and its input-provenance pin the ledger at
e4e992f (an early F0-era review commit, A1-0101). The implemented ledger is 85c59f5; the two differ in 114
files. The matrix is accepted F0 evidence and is not edited; the execution FREEZE must pin 85c59f5.
Agent 1's A1-0128 also reviewed the fault oracle against the ledger (every death predicate matches a
monotone ledger check at the same boundary; 12/12 tests pass in its scratch; "no-common-signer" can occur
only in the q2 mutant, F-18). Oracle note adopted: de-duplicate DENY entries by certificate digest in any
log-counting check, since a consumed DENY can be resubmitted.
