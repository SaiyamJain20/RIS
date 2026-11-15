# RQ2-F partial report packet — 2026-11-15

**Disposition:** prepared for scoped technical review; report remains DRAFT. This is a partial
evidence packet, not an F execution result, an execution FREEZE, an owner ACK, or a Gate F decision.

## Exact reviewed inputs

The current report text is pinned by SHA-256:

```text
8047d53e5e65020424db3469b0cc5589c7b91d793d991cec24c940a002a25b19  evaluation/reports/RQ2-F-DRAFT.md
```

The current execution proposal it describes is separately pinned by SHA-256:

```text
1a2d5e4fb7bd7fbf066a76d05e026db1a6e32079c36427cd63beda2c50dad919  evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json
```

Git refs explicitly refreshed for this continuation:

| ref | exact commit | scope / use |
|---|---|---|
| `origin/agent-1` | `208ed7d0415b8c1dd7d143c55e7271e71d310fcc` | includes A1-0139 confirmation of the `cf249e2a...` report hash |
| `origin/agent-2` | `81498f98aac497768b0dec35cea89ddf7466e697` | includes A2-0088 plan hook-coverage review |
| `origin/agent-3` | `445826a9140b49e2629f75da535e3e45b4706271` | report/packet revision reviewed by A1-0139 |

A1-0137 and A1-0138 reviewed earlier hashes for ledger scope, and their findings were
incorporated. A1-0139 then confirmed the exact `cf249e2a...` report hash, stating its correction
was applied exactly and the remaining report text was unchanged; it closed ledger-scope review
for that revision. This report-status and packet update is not an execution ACK or FREEZE ACK. Agent 3 has not
rerun Forge for the peer scratch tests.

Prior exact report SHA-256 reviewed by A1-0139: `cf249e2ad63b24d44acdef538d09718ef1fb3ae41e683af9009fa72ca07176f2`. Current report SHA-256: `8047d53e5e65020424db3469b0cc5589c7b91d793d991cec24c940a002a25b19`.
Current plan SHA-256: `1a2d5e4fb7bd7fbf066a76d05e026db1a6e32079c36427cd63beda2c50dad919`.

The plan's module pins are ledger commit `85c59f588de58a8ff5e87b9fe6f630c9d8c43642` and protocol
subtree `7566f63d693afe8fa88ab7cc69872082d58d88db` (active owner publication recorded in the plan
as `origin/agent-2` / `73fb2ce42d513ad3faf384500609e76d54aedbfb`). They are candidate source pins,
not execution authorization. A1-0137 is a report-specific review of the initial revision, for
ledger scope only; no Agent-2 report-specific review is present.

## Partial findings in scope

- The four-member, q=3 fixed-slot model satisfies Agreement under at most one Byzantine witness;
  the five-configuration rerun reproduces all recorded verdicts. This is a bounded model result,
  not implementation agreement, consensus, or liveness evidence.
- Synthetic oracle/store comparison is 180/180 on the cited grid. Seven deliberate oracle
  mutations are detected with their recorded counts. These are bounded reconstruction checks,
  not proof of oracle completeness.
- M5's exact-source pool sweep reproduces the prior result, including the out-of-bound f=2
  potential-hazard control. The honest signer behavior is modeled, and the hazards are not
  realized conflicting certificates.
- M2 is a virtual-transport sweep. M6 source describes local process tests, but retained raw
  outputs and exact invocation are missing; its 4/4 outcomes are prior reported measurements.
- M1 gas rows have peer-reported fresh reproduction and attached raw logs; Agent 3 verified the
  attachment checksums but did not rerun Forge. No production fee or throughput estimate follows.
- A1-0137's ledger-scope review found the reviewed draft accurate in its scope and identified the
  permanent DBC halt and fabricated-credential grant consequences of a compromised quorum. Agent
  3 added these with their f>=3 boundary and stated limitations.
- A1-0138's ledger-scope follow-up corrected the saturation claim: all three saturated checkpoint
  fields can permanently halt honest operation, with `authEpoch` stopping decisions immediately
  and `sourceBlockNumber`/`sequence` stopping them after expiry. Agent 3 verified the four published
  attachment hashes but did not rerun Forge.
- A2-0088 reviewed the execution-plan family `needs` strings, not the RQ2-F report. Agent 3 added
  the nine per-case G1/G2/G3 hook requirements and mutant IDs to the DRAFT plan; these are not new
  hook results or execution authorization.
- Signing-event join, sealing, duplicate-plan and fail-closed controls use synthetic inputs. The
  caller-supplied capture count/digest does not authenticate capture acquisition or completeness.
- F preflight covers stages 1–2 only. Stages 3–7, all 32 integrated cases and an E regression on
  the planned F system remain unrun.

The exact commands, exits, versions, source/output hashes and assumptions are in the linked
receipts in `RQ2-F-DRAFT.md`. The report's relative links were checked: 35 links, zero missing
before adding this packet link; all report links resolve after the edit. The review and response
are documented in [this receipt](../report-review-a1-0137-20261115/README.md).

## Review questions

1. Are the conclusion and each row in the claim-to-evidence table no stronger than its cited
   evidence, especially M1 peer reproduction, M6 retained outputs, and the model's fixed-slot
   boundary?
2. Do the capture/join descriptions clearly separate caller-supplied synthetic records from
   authenticated, complete process transcripts and native ledger observations?
3. Are the remaining proof gaps and the distinction between report review and execution
   authorization stated accurately?

## Review and execution dependencies

- **Partial-report review:** A1-0139 confirmed the exact prior report hash `cf249e2a...` and closed
  ledger-scope review for that revision. This packet's report-status wording update does not alter
  evidence or claim text, but the new report file hash has not itself been reviewed. No Agent-2
  report-specific review is present; A2-0088 is a plan-only review. A1-0129 reviewed ledger plan
  details; S2-0026 reviewed the draft plan. None is an execution ACK.
- **Execution authorization:** the plan remains `DRAFT`, `authorizesExecution=false`; Gate F is
  `NOT_RUN`, Gate G is `LOCKED`, and all 32 cases are `NOT_RUN`. The plan's exact role-scope
  execution ACKs and authorized FREEZE are still absent. No service or integrated case may start
  until those requirements apply to the exact plan and source set.
- Protocol source approval and signing-rule interpretation are accepted at the isolated source
  review scope under D57/S2-0024/25; this does not satisfy execution ACKs. K1 controls likewise
  do not satisfy them.
- Runner stages 3–7 and transcript acquisition/authentication/completeness evidence remain open.
  The partial report documents these blockers; it does not convert existing measurements into
  F-case results.

No external review request was sent as part of preparing this packet.
