# Execution ledger — PLAN.md / SPEC.md

2026-10-07 human confirmed checkout and assigned implementation through available phase E support.
- Ruling: direct human branch/machine instructions override old main/shared-index rules; retain ownership/gates. Cost if wrong: peer branch coordination must be revised; no main push occurs.
- Preflight E0→C-E1: v1 is not frozen; only independent oracle preparation is allowed before peer ACKs. Two-chain service integration needs missing agent-2 artifacts.
- Preflight E1→E2: agent-1 has early E2 preparation; treat it as candidate evidence, do not mark E1/E2 complete or use peer observed outcomes to set oracle expectations.
- Plan execution: inline; no extra agents as explicitly required by project. Self-review will be recorded separately; no independent reviewer is claimed.

- E0 owned preparation: source map 32 rows / assumptions 22; candidate schemas/valid-invalid vectors and 333 independent crypto checks. Exact normative freeze blocked on peer ACKs.
- Toolchain: Python/Foundry/solc and command-line ProVerif smoke completed; versions/hashes recorded. Optional GUI build failed; core-only build succeeded. No TLC/ABE installation before their phases.
- C-E1 independent preparation: oracle controls and manifests/preflight implemented; real provider execution/service lifecycle NOT IMPLEMENTED because protocol exports and v1 freeze are missing.
- Ruling: publish schema proposals under interfaces/proposals/v1; leave interfaces/README v0 unchanged until exact producer/consumer ACKs. Cost if wrong: candidate consumer work must be regenerated; no normative interface is falsely frozen.
- Ruling: run only ledger module tests on a pinned scratch archive, not E feature integration before E0. Cost if wrong: the eventual integration may uncover adapter/clock differences; no gate claim depends on the scratch tests.
- Vector correction: AccessRequest sourceChainId/psc mutations also derive the signing domain; 70 mutations agree after correction. Empty/missing coverage rejected.
- Self-review (project forbids extra agents): fixed nested signed-certificate semantic ordering, E single-signature bound, duplicate outcome rejection and malformed gate manifest handling. Each reproduced RED then passed; full suite 57/0. No independent-review claim.
- Remaining: exact peer source/semantic/schema/vector/dependency ACKs; protocol branch/export support; authenticated grant receipt revision; real E1 integration, E2 model/recovery/oracles and E3 report/gate. No F/G work.

- A1-0007/0008 review at owner commit 589a053: validate findings against paper/source, then fix S-1..S-3 with ten new cases RED (10 failed/21 passed) → GREEN (31 passed). Source map corrections M-1..M-4 applied; 37 rows/27 assumptions.
- Ruling: ACK exact A1-0008 success-only past-grant receipt but leave existing schema fields marked superseded until agent-2 ACK — affected-party contract rule requires it — cost if wrong: later candidate schema/vector regeneration; no live consumer/freeze relies on obsolete receipt.
- New peer manifest has 87 valid Git-blob entries and hash 1c4f4fc8679ba8a71179bec7ee09a6b7d597985e915bc8abacd604c6096b327b; owner HANDOFF still claims old 86-entry hash. Request refreshed exact READY, do not run/merge this revision. Historical f643805 evidence remains valid for its own snapshot.
- Review task verification: full suite67/0; vectors333/0; schema53/0; prompts/diff0; preflight runner/gate2 BLOCKED. Source stable during commands. Author self-review found no additional material issue in this slice; no independent reviewer claimed. Candidate16-file hash e2dde1994fb1146e0df979a955cc2c2ada7ce05e88eb55bf26c26fdf91a815c7 ready for exact peer review. E0/Phase1 remains incomplete.

- A1-0009 scoped candidate ACK + A1-0010 corrected READY at e351be5: reviewed exact hashes/unchanged ledger tree; explicitly repinned helper to87-file manifest1c4f4fc8.. for ledger589a053. This is a source-pin configuration update, not new behavior; preserved earlier evidence.
- Fresh compatibility batch exit0: owned67/0, vectors333/0, ledger154/0, Cast166/0, six mutants detected; E03 expected1; PV tool smoke0; prompts0; preflights2 BLOCKED. All10 expected outcomes; source/peer stable. Full candidate16-file bytes unchanged. No additional testing or phase advancement warranted without new peer artifacts.


## Current C-E2 checkpoint — 2026-10-08T23:22:43.865049+00:00

PLAN C-E2 symbolic correspondence slice complete within explicit fixed-name,
non-injective honest-key/witness abstraction. Source expectations in model README
before execution; RED4 missing-model failures, GREEN7 real model/sensitivity tests;
final root421 tests0/55.97s/80 stable inputs. Standalone full-binding verdicts
true/true/true/false/true; destination-omitting mutant false/false/true/false/true,
full correspondence counterexample traces reconstructed. No mutable nonce/trust,
clock, worker state, encoding/cryptographic/implementation theorem. Actual E1
9/9 unchanged; all56 Agent3 catalog schedules/gate E NOT_RUN, paper crashes still
BLOCKED/unproved; F/G locked. Source/tool/paper hashes/commands/exits/output/source
brackets/versions in evaluation/evidence/e2/formal-and-hook-review-20261009/README.md.

Fetched/read133 newest communication files/no divergence, A1 through0046/A2
through0026; exact delta commit/SHA provenance retained. Owner rehearsals/claim
sheets/window measurements are reviewed as owner evidence only. Preserve A1-0039
correction: wrong-destination source step1 masks destination step2 mutant. Preserve
A2-0025 effective-clock correction; no automatic interval-mining flag adoption.
Verified offered ledger933d2a7/c7b7dd51../195 and protocol0716a8e/d16ddad8../108
entries against immutable Git blobs; ledger runtime/bootstrap/deploy and protocol
production/export/ABI equal E1 pins. Source-reviewed SignList and hook ordering;
4 refusal controls/import boundary pass,109 extracted protocol files stable;
no real service/crash/recovery test.15 frozen copies exact.

A3-0032 answers A2-0020's three decisions with concrete start-contract r1
1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c. Alternate TEST-ONLY entrypoint/point observations/same-state production
restart/expiry/delivery unknown/OptionA and selected pins are PROPOSED_PENDING_ACK.
Both exact scoped A1/A2 ACKs required; earlier REVIEW/owner ACK is not substituted.
This is not the later full E2 FREEZE. A3-0033 reports symbolic slice; publication
is normal exact owned-path agent3 push, remote SHA recorded externally. No main.

Scheduled stale recovery: same host>9600s, recorded owner401986/guard402163 absent;
metadata/decision preserved before exclusive acquire. Own guard463584/start ticks
5798499 and separate coordinator flock463692. Prior untracked scheduled-run
permission-failure records preserved/unstaged; this host's writes succeeded.
Finally release both locks even on publication failure; actual cleanup recorded
in external run/memory, no future success assumed. Helper mistakes in frozen-copy
container/owner lookup and one metadata/output filename collision retained with
corrected successful proof; not research refutations.

Separate author self-review covers fixed-name query assumptions, positive/denied
paths, actual attack traces, signature/tuple scopes, owner inventory/ACK exactness,
hook ordering/EOF-vs-response, privacy/ownership and gate separation. No material
patch finding/deferred minor. Rulings: existing human checkout/no reviewer agent
(cost weaker review); fixed symbolic completion and no durable state (cost no
replay/recovery theorem); exact start-contract review before full plan/services
(cost real faults still pending). No peer mailbox/module/archive/frozen byte,
lock/dependency, extra agent/worktree, unreviewed branch merge or prohibited Git
operation. No human action required.

Next permitted: continue own C-E2 public runner/oracles and concrete full E2 recipe;
read/verify exact A3-0032 supplement ACKs when delivered; then complete FREEZE with
runtime/tool/config/fixture hashes and both exact plan ACKs, real fresh-state
strict/minimal/repaired fault/mutation/recovery matrix, report/all3 same-source
ACKs/gate E before F. Formal slice does not finish the C-E2 integration task.
