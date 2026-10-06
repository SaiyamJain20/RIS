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
