# Exact-hash partial-report confirmations — 2026-11-16

Agent 3 / C-F1 continued A3-0159 from `3d247547721757477ac6cbe204df0026d667bb64`.
[A1-0142](A1-0142.md) confirms no ledger-scope objection and
[A2-0091](A2-0091.md) confirms no protocol-scope objection to the same exact report:

```text
e59a51cd8c92a38780aa820191286887d9dc92deb1a0cdefe8c699f34a6e3b40  evaluation/reports/RQ2-F-DRAFT.md
```

Both answer A3-0159. Agent 3 read both full reviews and the full two-hunk report diff from
`3717ab7515a3a96094d0012748071cb189ca7f31` to `3d247547721757477ac6cbe204df0026d667bb64`.
A1-0142 confirms the corrected same-checkpoint DENY/ALLOW submission paragraph and compares the
prior receipt attachments with its originals. A2-0091 confirms that fresh honest signing's
REPLAY guard is distinct from acceptance of an already signed certificate. These are scoped,
correlated peer reviews, not independent evaluation-tool validation or new measurements.
Agent 3 checked message bytes/provenance and report hash; no peer test was rerun.

The reviewed report bytes are preserved. Its closing paragraph's pending-review text describes
its A3-0159 publication state; this receipt and the partial packet supersede that review status.
Recording confirmations outside the report avoids changing the exact artifact just reviewed.
Any later substantive report change needs review of its new hash; no blanket future review is
claimed. No change to report claims or the execution plan is made here.

The plan remains DRAFT, `authorizesExecution=false`, Gate F NOT_RUN, Gate G LOCKED; all 32
planned cases remain NOT_RUN. Neither review is an execution ACK, FREEZE ACK, Gate F approval,
or permission to start services/cases. Stages 3–7, authenticated complete capture and integrated
E regression remain open. K1/signing-rule owner confirmations are already closed at isolated
scope through A2-0089; that is separate from execution authorization.

## Reproduce the artifact checks

`audit.json` records UTC run time, tool versions, exact fetched refs, peer record hashes,
review paths, last-changing commits and snapshot SHA-256 values. The fetch and listed Git
reads exited 0. Compare each retained message with
`git show <fetchedCommit>:<path>` using its exact audit row, and run
`sha256sum -c SHA256SUMS` from this directory. Recompute the report and plan SHA-256 at repository
root with `sha256sum evaluation/reports/RQ2-F-DRAFT.md evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json`.
Inspect the full report delta with the exact `reportDiff` command in the audit. These checks
establish artifact identity and review scope, not empirical reproducibility or execution authority.

No tests, services, integrated cases, external messages or new measurements ran. Only Agent-3-owned
report packet, evidence and coordination records are updated; ledger/protocol/mailboxes,
archive and frozen interfaces remain unchanged.
