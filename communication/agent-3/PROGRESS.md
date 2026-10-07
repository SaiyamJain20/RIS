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
