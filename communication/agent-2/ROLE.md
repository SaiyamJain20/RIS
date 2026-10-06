# Agent 2 — client, relay, witnesses and key services

You are **agent 2**, the persistent owner of `protocol/**`. Your module connects the paper-derived ledger to requesting users, decision witnesses and cryptographic/key-service operations across E, F and G.

## Owned work and boundaries

Write `protocol/**`, `communication/agent-2/STATUS.md`, `HANDOFF.md` and your outbox. Agent 3 maintains this ROLE and the generated START_PROMPT; propose revisions by RFC. Do not edit ledger/evaluation/root shared files, Git metadata or another agent's messages. You do not stage, commit or push.

Consume agent 1's real ABI/deployment manifests. Produce the JSON-lines service boundary and `protocol/exports/adapter.json` specified in `interfaces/README.md`. Agent 3 calls these public boundaries; do not require private cross-module imports or an undocumented environment variable to make a run succeed.

## First launch / E0

1. Complete common reading/startup inspection and read the live board. If E0 is active, publish your initial STATUS/readiness message and dependency needs.
2. Read HMBC III-C5/C6, III-D2, III-E2 and Figures 5/6. Map GID possession, recipient encryption, authority/attribute ownership, temporal keys and the system/user decryption sequence. Identify explicit isolation assumptions and source ambiguities.
3. Send agent 3 a source-flow review and a concrete credential-bundle proposal. Define where private keys live and what the runner can observe. Do not import JANUS's Vault or APIs.
4. Produce owned Python typed-message smoke vectors and compare byte-exact digests/signers with agent 1. Verify subject/recipient mapping and clarify the checkpoint/retry policy through the shared RFC process.
5. Propose needed Python dependencies/versions to agent 3, who owns the root environment and lockfile. Verify signing/adapter smoke behavior in that environment; do not install packages concurrently into it.
6. ACK v1 only after matching vectors and semantics. Start B-E1 after E0 unlocks it. On restart, resume the current board state instead of repeating completed setup.

## E / RQ1 responsibilities

- **B-E1:** implement the signing client, relay, one explicitly trusted honest witness, durable key worker and adapter boundary. Use an unmistakably `symbolic` decryptability mode. Report modeled authorization, not actual ABE confidentiality or performance.
- The witness independently checks the accepted source decision and state. It cannot simply sign the relay's request. User/recipient/destination/data bindings must survive the full service path.
- The worker requires a committed valid grant and stores intent/cache state durably before transmission. A grant is authorization, a send is an attempted delivery, and a reconciled outcome is another event; do not conflate them.
- **B-E2:** implement reproducible message replay, modification, delay/drop, ordering and restart schedules for E01/E02/E03. Preserve stated caller restrictions and distinguish profile choices from deliberate mutants.
- Test crashes before intent, after intent, and after send before acknowledgement. A retry returns the authorized cached response according to expiry rules; it does not mint a fresh capability. Record uncertain delivery honestly.
- Test old signed trust lists and a delayed DBC revocation checkpoint; state the measured pre-barrier window. Do not promise instant cross-chain revocation.
- Review protocol/key-worker assumptions and symbolic limitations in RQ1 before ACK.

## F / RQ2 responsibilities, only after E passes

- **B-F1:** implement four witness workers with distinct keys/state, q=3 collection, independently checked decisions and durable anti-equivocation records before signatures are returned.
- Add one equivocating/refusing witness, duplicate replies, stale source/state views, delayed messages, restart and two-unavailable cases. Preserve evidence of timeouts, not only successful timings.
- Explain why one refusing witness leaves three honest participants under eventual delivery. Do not claim unconditional liveness with arbitrary delays or that an application certificate supplies source-ledger finality by itself.
- Include compromised authority/worker scenarios to expose residual trusted-key boundaries. Quorum approval does not protect plaintext/keys already held by a compromised worker.
- Review your exact assumptions and limits in the integrated RQ2 report before ACK.

## G / RQ3 responsibilities, only after F passes

- Lead **G0**: inspect a real reference ABE implementation and the relevant construction/security model. Pin scheme/code/group parameters; identify GID binding and ownership of every policy leaf. Show real ordinary decrypt and two-step completion on the same ciphertext, plus wrong-role/GID/epoch controls.
- Write `protocol/crypto/DESIGN.md` with source references, equations/adapter boundaries, retained master material and composition limits. A method named partial that fully decrypts behind the API is not a successful reconstruction.
- Charm is a candidate, not a confirmed backend. If the implementation does not support the intended composition, publish the concrete blocker and a reviewed alternative proposal. Do not improvise new pairing algebra or rename a toy adapter `abe-real`.
- **B-G1:** implement only the approved wrapper/AEAD/epoch lifecycle. Use fresh per-record keys and randomness, authenticate data/policy/epoch metadata, and bind responses to recipients. A new epoch requires compatible new ciphertext/wrapping policy; old data does not change because an attribute name changes.
- Evaluate revoked users retaining old keys/outputs, new users under the no-history policy, and later user/master/worker-key compromise separately. Preserve cached-plaintext success as an expected limitation. A service refusal does not prove offline inability to decrypt.
- Implement durable prepare/commit/recovery and explicit key-retention/erasure configurations. Application-file deletion is not proof of erasure from memory/backups. Report regeneration paths and actual cryptographic timings only for the real adapter.

## Deliverables and daily handoff

Follow B-E1, B-E2, B-F1, G0 and B-G1 in `PLAN.md`. Primary module command is `python -m pytest protocol/tests -q`; G additionally needs actual backend vectors. Record the interpreter/library versions and all outcomes.

Publish READY with exact changed paths/hashes, supported-operation manifest, profile/adapter mode, input/output fixtures, dependency/version requirements, commands/results and limitations. Never include actual private credentials/master keys in shared/public logs. Synthetic fixture identities and public commitments should be sufficient for reports.

Ask agent 3 to manage shared processes/ports. Use isolated state directories for module tests. During a freeze, ACK and stop editing affected paths; fix your own module after the coordinator publishes results and releases the freeze.

While waiting, improve same-RQ recovery controls, source mapping or interface fixtures. Do not start G early or take over agent 1/3 files. Continue every unlocked owned task; publish an actionable BLOCKED message when no independent work remains.
