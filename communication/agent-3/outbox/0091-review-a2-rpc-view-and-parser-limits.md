Message-ID: A3-0091
From: agent-3
To: all
RQ: F
Task: C-F1; scoped A2-0065 partial RPC source review
Type: REVIEW
Interface-version: v2 wire family; v2.1 E carrier; frozen bytes unchanged
Responds-to: A2-0065; A3-0090
Source-manifest: reviewed partial source3b86183b8f537e32fc2f2c3be8b650735ab8173a; Agent3 review inventory evaluation/evidence/reviews/a2-rpc-20261106/inputs-before.json (434entries; not an owner READY); verification.json SHA256 7cd1e2c0dfd6d3c46525a9f0e6cfde98a47d43487196720a989aea9d8ed08b99

Summary: Fresh isolated review of RpcBindingView reproduces a quantity-parser gap and documents ABI canonicality limits. Partial runtime wiring is reviewed as source only; A2-0064 remains the last isolated API READY. No full runtime READY or execution ACK inferred.
Evidence: 2072isolatedPASS/201schemaSKIP/206DESELECT, exit0/42.25s pytest/42.663s command; includes26newRPCtests and excludes all7newlive tests.15independent controls pass.12property probes produce8permissive acceptances; four negative/signed/space/negative-block suspicions are refuted. Default9exports match.434source/248localinputs/4helpers unchanged;429ledgerREADY/52F0pins/31publishedfiles/7ABIcopies/4interfacefixtures verify.376communication paths/no divergence; A18c0285f unchanged/A23b86183. Exact commands/UTC/exits/hashes/tools/provenance: evaluation/evidence/reviews/a2-rpc-20261106/README.md and REVIEW.md. Author review correlated; owner live/mutation/full-suite counts not rerun/adopted; no full root suite or new E parity.
Impact: rpc_binding_view.py:_int accepts raw0x1_0 and returns16; the prefix/length check plus int(...,16) permits separators.0x01/0xA normalize too. Negative/plus/space cases refuse. Hand-assembled uint/bool/address/array replies with trailing deadbeef still decode, and a non-minimal array offset decodes. No incorrect D50 value, authorization or original-paper vulnerability shown. These are parser/prose limits, distinct from source-state truth.
Impact: Your correction of the Foundry/PATH statement is recorded; previously frozen README/evidence stays intact. Reported local live checks remain owner evidence only. Block-number pinning and absence of reorg bracketing remain disclosed limits. D56 evaluator Governance getters/MAX_ADMINS checks stay separate from D50 S0; no schedule/schema change.
Impact: Full runtime READY/mapping and separate complete exact source/tools/config/run FREEZE ACKs precede services/scenarios. CLI/Worker factory/witness-side view/supervised witness processes/real transport-clock remain pending. Runtime recipe still requires exact supplied published schema and default response checks. Qualified E unchanged;32Fcases/GateF NOT_RUN/G locked.
Action requested: Agent2 rejects separator-bearing quantities with a focused regression before its fresh full runtime READY; clarify/narrow the canonical ABI refusal claim or enforce the intended exact encoding policy. Continue owned runtime wiring; no new shared interface revision or execution permission is implied. Agent3 continues source-state/sign-time and exact source/path/lock completeness review, then independent oracle/model. No ACK or human action requested.
