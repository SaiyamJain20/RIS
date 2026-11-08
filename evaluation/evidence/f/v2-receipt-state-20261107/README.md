# GrantReceipt supplied-state consistency

C-F1 WORKING; integrated execution stays LOCKED. Internal evaluator extension
for the paper-derived HMBC2020 reconstruction, synthetic fixtures only.

receipt_state_v2.verify_receipt_signature composes the caller-pinned single-owner
EIP-712 signature/context with exact raw ABI captures. It checks the derived grant
ID, existing allowed DBC grant, pending PBC request and destination/subject/data/
key-epoch/original-expiry bindings. Exactly one DECLARED GrantIssued log must
match grant fields, recipient commitment, signed DBC block reference and raw
issuance timestamp. Its block cannot follow the supplied DBC observation.
Same-height conflicting hashes refuse under this checker's declared safe interval.
Missing, duplicate, malformed or unused blocks/calls refuse. Exact reviewed ABI
bytes are required. No consumer, owner module, frozen wire or dependency changes.

Late reconciliation remains valid after request/grant expiry. A receipt grants
no fresh release and proves neither attempted sending nor delivery. The supplied
log is not cryptographically included by this checker; counting one declared log
cannot establish that no log was omitted. Event nonce/nonceConsumed are decoded
but this slice does not reconstruct the request nonce or its consumption.

## Reproduce and limits

Run `.venv/bin/python -m pytest evaluation/tests/test_receipt_state_v2.py -q`.
Exact broader argv/cwd/UTC/exits/output SHA256 and deterministic gzip outputs are
in *-command.json/*.log.gz; command process-group receipts are in the ignored run.
Source/spec provenance records branch tip, exact file-changing commit and SHA256.
Owner runtime counts are not adopted. Inputs-before/after bracket owner sources,
selected local runtime inputs and all tracked baseline blobs including historical
fixtures; frozen payload and accepted F0 pins verify. Tools/environment digest
are recorded; no environment values or secrets are published.

Initial 72 RED failures were all the expected missing evaluator module. The
first implementation run passed71 and exposed a positive FIXTURE inconsistency:
its getter retained the old hash after moving its observation. One fixture line
was corrected; original RED test bytes/hash and failed trial remain. Product
code was unchanged. Corrected72 GREEN passes. Initial author trials precede the
complete runtime bracket. No product/test edit follows the corrected GREEN.

The first focused command named nonexistent test_evm.py (exit4, no tests). The
corrected selector uses test_evm_codec.py. Initial mutation harness exit1 omitted
schema ValidationError from its accepted refusal classes; corrected harness
accepts the same two classes as tests. Original helper bytes and exact revision
maps are retained; blanket helper stability is NOT claimed. No product/test
change or removal of a negative expectation was needed.

Six independent in-memory bypasses remove allowed-grant, pending-request,
original-request-expiry, event/grant equality, observation-height or bound-signature
checks. Each retains a valid control and exposes the intended false control.
This is sensitivity evidence, not exhaustive mutation/coverage or a paper flaw.

Review is correlated author review under the no-extra-agent rule. This establishes
supplied state/event consistency only. RPC/chain truth, ancestry, signing time,
latest head, complete log ranges/store/export/history, witness persistence/policy,
native deaths, quorum/consensus, cryptographic performance, new E parity, TLC,
F scenarios and all RQ gates remain outside this evidence. These conclusions do
not establish producer misconduct or an HMBC-author implementation vulnerability.

## Continuation

Receipt history/RPC acquisition and explicit observation/log-range provenance,
AccessDecision source-state duties, producer/schema/path/lock completeness, then
fault oracle/finite model remain. A3-0096/97 startup requests stay open. Complete
runtime READY/mapping and separate exact execution FREEZE ACKs precede services.
Three known historical E source differences still require inventory/E regressions
in the next full protocol READY. Qualified E unchanged;32Fcases/GateF NOT_RUN/G
locked. No new peer ACK, services, worktree, extra agent, main push or human action.

## Verified results

72 new/246 focused/2906 root PASS; root 650.91s/command 651.231s/exit0. Six deliberate bypasses detected with valid controls.

Inputs-before SHA256 `a2e6b78a6d7475f289da3fc8c40c526ca98793d5b5b92a2665b85e6b519c3925`; inputs-after `24bb4a17df85805d2f87a686c68d6c0788ea826bb112a742513bfe0fe36b6d86`.
Verification JSON SHA256 `f51b60a226e9d8167b6f6ada9aca0dad01f65c8c798962eaccb1471dee0a67f1` checks 13 predecessor command receipts; its own receipt is independently checked after exit.
899 owner and262 selected local runtime inputs are stable;8626 tracked baseline blobs match initial HEADa905fbf.52 accepted F0 pins/31 frozen payloads verify.395 communication paths/no divergence; peer tips unchanged.

The postflight verifier source is retained as verify.py.txt with its artifact hash and recorded command; it is separate from the four original bracketed helper inputs. Helper corrections are pinned by helper-revision.json. Focused/mutation/full-suite commands partly overlap; elapsed records are not performance measurements. No product/test change follows the corrected GREEN.
