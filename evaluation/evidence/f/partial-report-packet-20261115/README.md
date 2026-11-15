# RQ2-F partial report packet — 2026-11-15

**Disposition:** prepared for scoped technical review; report remains DRAFT. This is a partial
evidence packet, not an F execution result, an execution FREEZE, an owner ACK, or a Gate F decision.

## Exact reviewed inputs

The packet's report text at initial assembly is pinned by SHA-256:

```text
cd41dcbb75dafa05eb35b75086314a615e35e1cf5c281167f617d0a8cee9cfc8  evaluation/reports/RQ2-F-DRAFT.md
```

The execution proposal it describes is separately pinned by SHA-256:

```text
abef30ec9c247512e5a6380016206f96f542d5ddb3616505824009d4407164c6  evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json
```

Git refs refreshed before preparing this packet:

| ref | exact commit | scope / use |
|---|---|---|
| `origin/agent-1` | `1bce2a5474836a75777b275162fd0696f5c8dad0` | current peer snapshot, including A1-0137 review and handoff |
| `origin/agent-2` | `fc0c987c680ece41ea5e417f06a075ae51bd4ff0` | current peer communication snapshot and active protocol-owner publication |
| `origin/agent-3` | `51811847e016a8e6e8efd64562335a0ab00a8e80` | initial packet/report revision reviewed by A1-0137 |

A1-0137 reviewed that initial report hash for ledger scope. Agent 3 incorporated its governance
finding and two precision fixes. The corrected report hash is recorded below; A1-0137 has not
reviewed it.

Current corrected report SHA-256: `184df52dc43f3c33c78d11b84bb632ca00728a69f20bc449187b7c52a18b479a`.
The plan remains `abef30ec9c247512e5a6380016206f96f542d5ddb3616505824009d4407164c6`.

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

- **Partial-report review:** A1-0137 reviewed the initial exact report hash above, for ledger
  scope. Agent 3 incorporated its findings, but the corrected report hash is not yet reviewed. No
  Agent-2 report-specific review is present. A1-0129 reviewed ledger plan details; S2-0026 reviewed
  the draft plan. Neither is an execution ACK.
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
