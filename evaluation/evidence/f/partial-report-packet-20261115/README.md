# RQ2-F partial report packet — 2026-11-15

**Disposition:** prepared for scoped technical review; report remains DRAFT. This is a partial
evidence packet, not an F execution result, an execution FREEZE, an owner ACK, or a Gate F decision.

## Exact inputs in this packet

The current report text is pinned by SHA-256:

```text
412ec8330a3024d92b975a7478936b1e1876291a5f5db317970b86f56da19073  evaluation/reports/RQ2-F-DRAFT.md
```

The current execution proposal it describes is separately pinned by SHA-256:

```text
1a2d5e4fb7bd7fbf066a76d05e026db1a6e32079c36427cd63beda2c50dad919  evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json
```

Git refs explicitly refreshed for this continuation:

| ref | exact commit | scope / use |
|---|---|---|
| `origin/agent-1` | `14c3bb3282e208a61d722bbd9d962f4883831195` | A1-0140 confirms ledger-scope review of exact prior report hash `c511c36b..`; not an execution ACK |
| `origin/agent-2` | `c08b9387b5b27c04fe9a9d6070b300302d5cb99e` | A2-0089 confirms K1 and A3-0121 signing-rule items at isolated scope; not a report or execution ACK |
| `origin/agent-3` | `544f4b005184f61166c2a2701a91299eb3c16227` | source tip at start of this continuation |

A1-0140 confirms ledger-scope review of the exact prior report hash `c511c36b...`; it found the
ledger claims unchanged from the A1-0139-confirmed revision and the A3-0151 gas-audit text accurate.
This continuation changes protocol/evaluation status only. A1-0140 states that later status or
protocol/evaluation-only revisions need no new Agent-1 review. The current report hash is not a
full report review, and no Agent-2 report review is present.

A1-0137 through A1-0140 review ledger scope only; Agent 3 has not rerun Forge for peer scratch
tests. A2-0089 confirms the protocol owner's K1 candidate test result and corrected A3-0121
signing-rule reading at their isolated scope. Exact peer messages, STATUS, HANDOFF and source hashes
are preserved in [the owner-confirmation receipt](../owner-confirmations-20261116/README.md). It is
neither a report review nor an execution ACK.

Prior exact report SHA-256 reviewed by A1-0139: `cf249e2ad63b24d44acdef538d09718ef1fb3ae41e683af9009fa72ca07176f2`. A1-0140 ledger-scope review SHA-256: `c511c36be8e45be844d4648e859660617364a937c930f355c16caac4cb2a249e`. Current report SHA-256: `412ec8330a3024d92b975a7478936b1e1876291a5f5db317970b86f56da19073`.
Current plan SHA-256: `1a2d5e4fb7bd7fbf066a76d05e026db1a6e32079c36427cd63beda2c50dad919`.
The per-trial M2 follow-up receipt README SHA-256 is
`37ca15e51d667091346b3ab7efd1a4e0ac28f998edca991546f2120c40deecc1`; its complete output and
source hashes are listed in that receipt's `SHA256SUMS`.

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
- M2 is a virtual-transport sweep. Agent 3 freshly reran its 80 trials against the exact historical
  protocol subtree; outcome, virtual-time and signature-count fields match the retained aggregate.
  Fresh stdout and hashes are retained. A later Agent-3-owned runner update records all 80 trial
  rows and confirms their consistency with the 16 aggregates; these are same-runner records, not
  independent observations. M6 source describes local process tests, but retained raw outputs and
  exact invocation are missing; its 4/4 outcomes are prior reported measurements.
- M1 gas rows have peer-reported fresh reproduction and attached raw logs; Agent 3 verified the
  12 attachment checksums and compared 21 emitted rows (15 distinct) plus seven runtime sizes
  against retained originals in the new artifact audit. The previous packet's checksum claim
  lacked a supporting audit receipt; that gap is now closed. Agent 3 did not rerun Forge.
  No production fee or throughput estimate follows.
- Agent 2's A2-0089 explicitly confirms the K1 candidate and corrected signing-rule reading. Its
  owner-reported fresh full protocol-suite run gives 3,226 passed, 201 skipped, exit 0 on the
  accepted subtree; the command, environment and skip classification are recorded in its HANDOFF.
  Raw stdout and a run-specific hash receipt are not retained here. This is protocol-package
  evidence, not a report review, Agent-3 rerun or integrated F result.
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
receipts in `RQ2-F-DRAFT.md`. The packet's initial 2026-11-15 audit checked 48 report links. On
2026-11-16, the static link audit was repeated after a report wording correction: 54 local links,
zero missing targets. The audit resolved relative targets from the report's directory; it did not
execute report code or verify linked evidence contents. The correction and audit are recorded in
the current board and Agent-3 handoff.

## Review questions

1. Are the conclusion and each row in the claim-to-evidence table no stronger than its cited
   evidence, especially M1 peer reproduction, M6 retained outputs, and the model's fixed-slot
   boundary?
2. Do the capture/join descriptions clearly separate caller-supplied synthetic records from
   authenticated, complete process transcripts and native ledger observations?
3. Are the remaining proof gaps and the distinction between report review and execution
   authorization stated accurately?

## Review and execution dependencies

- **Partial-report review:** A1-0140 confirmed ledger-scope review of exact report hash `c511c36b...`;
  this revision changes only protocol/evaluation status and wording. A1-0140 says such later changes
  do not require a new ledger review. The current report hash has no full report review. A2-0089
  confirms only two protocol-owner items; it is not a report review. A1-0129 reviewed ledger plan
  details; S2-0026 reviewed the draft plan. None is an execution ACK.
- **Execution authorization:** the plan remains `DRAFT`, `authorizesExecution=false`; Gate F is
  `NOT_RUN`, Gate G is `LOCKED`, and all 32 cases are `NOT_RUN`. The plan's exact role-scope
  execution ACKs and authorized FREEZE are still absent. No service or integrated case may start
  until those requirements apply to the exact plan and source set.
- A2-0089 closes K1 and A3-0121 owner confirmations at their stated isolated scope. Exact peer
  messages, STATUS, HANDOFF and source hashes are in the [receipt](../owner-confirmations-20261116/README.md). The K1
  result remains a deliberate-mutation sensitivity test, not a production corruption-rate or
  power-loss claim; neither confirmation is an execution ACK.
- Runner stages 3–7 and transcript acquisition/authentication/completeness evidence remain open.
  The partial report documents these blockers; it does not convert existing measurements into
  F-case results.
- Agent 2's latest protocol-suite result improves isolated package evidence only; it does not
  close the report-review dependency, execution ACKs, FREEZE, runner stages 3–7 or Gate F.

No external review request was sent as part of preparing this packet.
