# A1-0087 F0 ledger-input review, 2026-10-13

Human requested checking further communication, managing untracked files and
switching to main for study. Read A1-0087 and owner STATUS/HANDOFF at
459464977e69e555e08b6719fabebb69e3eb5769. Agent2/main/Agent3 remain at common
baseline376347d. Slides changed independently; no slides work was merged.
278 newest communication paths, no divergent revisions; exact file-changing
provenance in communication-provenance.json. This is same-model source/mechanical
review, not independent F gate confirmation.

## Fresh checks

An exact git-archive ledger snapshot in .git/ris-study-20261013/a1-snapshot was
used. All297 tracked owner files hash-equal before/after. Production src/script/
foundry.toml match E pin933d2a7; all changes are new F0 input/tests/tools/evidence
and owner handoff updates. Owner manifest186e28fb.. verifies296 entries (exit0).
Pinned Forge1.8.5 / solc0.8.37 suite: **188 passed,0 failed,0 skipped**, exit0,
including22 F0 characterization cases. Compilation14.05s; EVM suites58.74ms.
AST/citation checker exit0, problems[]:29 state rows/70 variables,33 entry rows,
12 actors,18 cited tests. Compiler hash5de843c2.. matches frozen toolchain.

Commands/UTC/exits/output hashes are each in their .json sidecars; raw outputs
in .stdout.txt. No live Anvil services, two-chain integration, q3/f1 experiments,
new production semantics, F implementation, source-plan/interface ACK or gate
result. Owner7-control sensitivity and checker-negative tests were read, not
rerun in this focused review. The checker validates coverage/citations, not the
power claims; Forge reproduces the bounded characterization fixtures only.

## Coordination result

A3-0053 accepts this as ledger-side F0 input. Agent3 still owns fault-model.csv,
f_matrix.json and the coordinated exact plan. D-a..D-f remain open; FL1..FL11 are
proposals, not preregistered/ACKed outcomes. Agent2 has not yet published its F0
key-control enumeration/D50 successor RFC. Do not infer acceptance from silence.
Request a grouped owner RFC with separate choices/ABI/source migration impacts
for the six decisions so the shared plan can resolve them explicitly; this review
chooses no new governance, expiry, epoch or checkpoint semantics.

Old untracked files were **four automation stale-lock/run logs from October8**,
not implementation or research-gate output. They were copied and hash-verified
under .git/ris-local-evidence/scheduled-runs-preserved-20261013, then exact working-
tree originals removed. Preservation record stays there, not in the research
report. No blanket clean/reset/stash, raw private state publication or peer edits.
Main stays at376347d for studying completed E; this scoped review is published
only on Agent3 and is not merged/pushed to main by the prior one-time permission.
