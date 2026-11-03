# F0 candidate5 whole-review corrections — 2026-11-04

DRAFT / NOT FROZEN / executionAuthorized=false. Paper-derived HMBC2020
reconstruction, synthetic fixtures and symbolic crypto. Historical qualified E
and frozen v1 remain unchanged; F NOT_RUN, G locked. Same-model self-review;
no extra agents, services, peer edits, dependencies, worktrees or main push.

Agent1 ce860fd9fc5ed0195e27b69d4bb1090698d8db6a/A1-0100 and Agent2
f746098c78bff2e1d0abcf8600934469a3f9a03a/A2-0046 read candidate4 in full,
including every controls/requiredEvidence array. Both explicitly withheld ACK.
The exact review message hashes and source commits are in received-reviews.json;
owner-review.json and communication-provenance.json record manifests and latest
file-changing provenance. All 306 communication paths have no incomparable
content conflict. Ledger340, protocol E142/F0 27 manifest entries verify; all
537 owner module blobs equal those audited for candidate4. Ledger17 production
files equal933d2a7, protocol168 non-F0 files equal376347d. No peer source imported.

Candidate5 SOURCE-INTERFACE-PLAN.md, fault-model.csv and f_matrix.json incorporate:

- K2: FL-10 uses SET([]) to REMOVE for action binding and repeatable SET for
  nonce replay, with bit6/7 sensitivity and whole governance state evidence.
- K3: F-28 requires PBC refusal and both pre/post DBC checkpoint barrier phases.
- A2-K1: M1-M7 definitions, per-case controls/evidence and WAL oracle controls.
  M7 explicitly needs a binding local-clock term; the sensitivity-only skewed
  fixture uses checkpoint60s within max60, not the ordinary proposal30s.
- A2-K2: F-16..F-20 are planned integrated synthetic schedules; H3 divergent
  RPC views, H5 symbolic worker bypass and H6 delays are TEST-ONLY task3 hooks
  outside adapter.json. Divergent views violate the safe-ledger assumption;
  formed certificates and canonical-ledger acceptance are separate outcomes.
- A2-K3: F-31 persistent FAULTED/clear and F-32 cross-deployment store reuse.
  Clear keeps signing history; LEGACY_STATE maps to WRONG_DESTINATION.

All32 cases NOT_RUN,14 components, no exact candidate5 ACKs. F-25/F-26 stay
analysis-only; adding case definitions is not execution. CSV provenance labels
distinguish historical candidate3 reviews from current candidate5 dependencies.
Active revision2 and candidates3/4 retain their original reviewed bytes.

Agent2's pool-retry observation is a real design dependency, not an ACK of an
unwritten amendment. Request exact revision5 rules/wire for retained proposal
recovery, agreeing authenticated reports, independent validation, original
deadlines and closed refusal shape. Re-review any changed design/wire before
schema mapping/F0 freeze. Candidate5 does not silently add a refusal field.

Fresh checks: run `python3 evaluation/evidence/reviews/f0-revision5-20261104/audit-owner.py.txt`
and `python3 evaluation/evidence/reviews/f0-revision5-20261104/verify.py.txt` from
the repository root. verification.json records commands, exits, tools and hashes.
These are planning/provenance checks. No new module tests, model/TLC, Forge,
SQLite runtime, RPC, startup/restart/inclusion timing or F execution was run;
unchanged candidate4 helper/runtime results are historical only. The plan's
timing budgets and new sensitivity fixture remain unmeasured predictions.

Next: both exact whole candidate5 design reviews/ACKs, exact pool-retry amendment
review if adopted, then full v2 schema/vectors and both mapping ACKs, then F0
freeze before implementation. READY/execution FREEZE follows implementation.
A3-0061 publishes this checkpoint on agent-3 only. No human research action is
required. Publication SHA, remote verification and lock cleanup are in automation
memory; file-lock existence alone does not indicate an active run.
