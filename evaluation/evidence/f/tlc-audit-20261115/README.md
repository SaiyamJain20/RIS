# DecisionQuorum TLC audit — 2026-11-15

Fresh offline rerun of the five finite-model configurations already described in
evaluation/evidence/f/decision-quorum-tlc-20261113/README.md. This is a tested
reconstruction result, not a proof of production consensus, a runtime signing
result, an integrated F case, or Gate F.

Tool/source identity is recorded in source-sha256.txt (full SHA-256),
java-version.txt, and jar-sha256.txt. TLC is the same pinned jar (SHA-256
936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88) and OpenJDK
21.0.11. Commands and each exit status are in commands-and-exits.txt; complete
stdout/stderr is retained under logs/, with hashes in log-sha256.txt.

| Config | Expected check | Exit | States generated / distinct | Queue | Result |
|---|---|---:|---:|---:|---|
| f=1, q=3, persistent | positive control | 0 | 433 / 108 | 0 | Agreement holds; complete |
| f=0, q=3, persistent | positive control | 0 | 217 / 81 | 0 | Agreement holds; complete |
| f=1, q=2, persistent | weak-threshold mutant | 12 | 202 / 78 | 40 | Agreement violation found; search stopped at violation |
| f=2, q=3, persistent | out-of-bound control | 12 | 679 / 142 | 18 | Agreement violation found; conditional on f=2, outside f=1 bound |
| f=0, q=3, no persistence | no-single-signing mutant | 12 | 1,344 / 226 | 57 | Agreement violation found; search stopped at violation |

All five verdicts and counts match the retained 2026-11-13 results. Queue counts
for violation runs are remaining states when TLC stops at its first counterexample;
they are not completed graph sizes. The positive runs exhaust the reachable graph.
The original model-hashes.txt records only 16 hexadecimal characters per digest;
this recheck adds full SHA-256 values and log hashes. That provenance improvement
found no model/result mismatch.

The model covers one decision slot and assumes the declared witness set, threshold,
Byzantine subset and persistence rule. It does not model expiry, checkpoint changes,
superseded pin generations, delivery/liveness, key custody, real signatures, adapter
behavior, or consensus. In particular, f=2 is outside the stated fault bound and
is not a measured chain break. No services were started.
