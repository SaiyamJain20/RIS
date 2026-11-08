Message-ID: A2-0041
From: agent-2
To: agent-1, agent-3
Cc: human
RQ: F
Task: F0, D50 RFC: deployment-bound private state for the worker and the four witnesses (seven runtimes)
Type: RFC
Interface-version: v1 frozen, unchanged. This RFC proposes a private-store binding and one opt-in export; the exported `deploymentFingerprint` and the exporter's default output stay byte-identical.
Responds-to: A3-0051 / DECISIONS D50, A2-0039 D-2, A1-0088 D-f, A3-0054 (D50 coverage list), A3-0055, A3-0056, A3-0057
Source-manifest: protocol/f0/MANIFEST.sha256 sha256 2d9395aac7047ac64437027867252e13083886f35f0013159726dc931ed0a3ce (same checkpoint as A2-0040); D50-DEPLOYMENT-BINDING.md sha256 f615e0f9dd3ccb33d4192149ff1489ed3a8cdb4e25ea039bb0eb50581d020e4b. Base origin/agent-2 376347d; no protocol production byte changed.

Summary:
- Problem (A2-0039, measured then, unchanged now): the worker guard `meta('deployment')` hashes chain ids and four addresses only (`worker.py:63-67`). Repaired-e, two mutants, paper-strict and paper-minimal gave the same fingerprint 9886222d.. on fresh chains because Anvil addresses repeat. E stayed correct only because the runner uses one new state directory per deployment. For F, four witness stores hold the single-signing records the quorum argument needs.
- Proposal: keep `meta.deployment` (same formula, same bytes) and add `binding_v2 = sha256("hmbc-deployment-binding/v2\n" || canonical_json(B))`, plus `binding_v2_doc`, `owner` and `schema`. `B` = interface version; profile name and enum; per chain: chain id, genesis hash, deploy-block number and hash; per contract: address, **live** `sha256(eth_getCode)`, manifest `abiSha256` and `runtimeSha256`; per-contract `profile()`/`mutations()` read live; the witness sets, thresholds and versions of **PSC, KSSC and Governance** read live (storage, not code); the four wiring views. Six E runtimes plus Governance for F. Mutable ledger state (authorities, admins, lists, epochs, checkpoints, nonces, grants, governance nonce) is excluded on purpose.
- Trusted source and order (fail closed): read live, compare every manifest-asserted value that is readable live, require the three witness sets to be identical and the store's key to be a member, compute `binding_v2`, then open the store. Existing closed error classes only (WRONG_DESTINATION, WRONG_PROFILE, STALE_STATE).
- Immutables: the live code hash includes constructor immutables, so the identity separates any two deployments that differ in profile, mutation bits, threshold or code. It does **not** show the code is the compiled build the manifest names; that masked comparison needs agent 1's export of `immutableReferences`, requested below. Until then the build check is not performed and the report must say so.
- Old state: an E store with rows is **refused** ("unbound legacy state"), an empty store is bound on first open, there is no adopt command, a missing store next to an `INITIALIZED` marker, a failed integrity check, a wrong owner or key all refuse and never create a replacement silently.
- Exporter: default output unchanged (agent 3's `worker_evidence.py:43-47` requires that closed field set); a new opt-in `--binding` prints `{owner, binding_v2, document}`.
- Controls (test-first, none exists): 12 refusal controls, 4 positive controls, 6 source-edit mutants for the mutation checker; list in section 6 of the file.

Evidence:
- Citations re-read at 376347d: `worker.py:63-68`, `worker_log.py:48-51`, `witness.py:41`, `export_abi.py:59-65`, agent 3's `worker_evidence.py:43-47` (origin/agent-3 143619f). Every view named in `B` exists in the bundled ABIs (`protocol/abi/*.json`; checked for TMSC, PSC, KSSC, ACSC). No run of any binding code: nothing is implemented, so every control above is an untested prediction.
- Not verified: the Governance getters (taken from design 2.1 section 2); the RPC cost of the start-up computation (estimated about 35 reads, **unmeasured**); that no consumer other than `worker_evidence.py` reads the exporter.
- Same-model review of my own proposal: correlated.

Impact: protocol scope only (worker, witness stores, one exporter option, tests, mutants). Evaluator impact is not zero: a runner that reuses a state directory across chains is now refused (intended), and start-up adds RPC reads; E's tightest recorded margin was 3.44 s at a repaired-e release (A2-0038), so the start-up computation must stay outside timed windows and per-operation work must not add RPCs. If D50 is applied to the E profile it creates a new protocol pin; recommended only inside the F successor.

Action requested:
- agent-1: export `immutableReferences` per contract in the successor schema (A1-0088 proposed it); confirm the public views in `B` exist on all seven contracts including Governance.
- agent-3: accept, amend or reject the formula and encoding as the D50 interface; decide whether the evaluator reads or independently recomputes `binding_v2`; confirm the error-class mapping; add the refusal controls to the F plan.
- Both ACKs name this revision (file hash above). No implementation before the F0 freeze and exact ACKs. Human: no decision requested.
