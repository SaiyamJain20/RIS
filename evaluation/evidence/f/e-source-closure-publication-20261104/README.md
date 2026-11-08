# Additive E source-closure schema publication — 2026-11-04

Classification: **tested reconstruction/interface migration result**. This closes
an embedded source-provenance omission in the opt-in E carrier of our paper-derived
HMBC2020 reconstruction. It is not an original-paper vulnerability, source/runtime
authentication, integrated parity, cryptographic implementation or gate result.
Synthetic fixtures only; no integrated services or deployments.

## Exact authority and publication

Proposal: interfaces/proposals/v2-e-source-closure/MANIFEST.json,
sha2567810ad105330de73920450d82f4850ebb6de0846396e5bb786818e700e49bb0a.
Both exact affected ACKs are verified/copied here: A1-0114 and A2-0060. The acceptance
receipt records full observed/file-changing commits, message paths/hashes/scopes;
Agent2's proposal ACK is not a publication receipt or source READY.

New communication/E_SOURCE_CLOSURE_ACCEPTANCE.json sha256
511e235f3aff86a57822e26136282f97bcb9550e84c95263b14ed1bbab8e9fb6.
New interfaces/v2.1/hmbc.schema.json sha256
d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3.
New interfaces/v2.1/FREEZE.json sha256
232b84bb7f997b687a5dc671d79ab6ecdd592d17cd38e531d8460d33ed81660a.

The schema applies exactly the two ACKed add operations: a third disjoint E carrier
and its union branch.135old non-union definitions and every other top-level value
remain equal. The copied x-status annotation remains as ACKed; README supplies live
status. Source-complete marker is hmbc-ledger-deployment/v2.1; interfaceVersion and
all wire/signing domains stay v2. The new map describes twelve module build inputs,
not twelve deployed contracts. Old ten-source E remains historical compatibility
with its known omission. New consumers select the revision explicitly; old default
remains v2. D50 preimage, whole-manifest equality and default v1 remain unchanged.

## Fresh verification

commands.json records actual argv/cwd/UTC/exits/durations/output hashes. Logs:

- red.txt.gz (lossless original output): all27 new tests failed before implementation (missing selector/schema;
  expected exit1). No selector/schema implementation preceded this RED.
- focused.txt:226PASS/exit0 (27new +68existing validator +131certificate tests).
- successor-corpus.txt: all68 existing v2 validator tests pass against the actual
  successor schema. Only this independent test process's schema path is selected;
  no production/global state or source is modified. Separate command receipt saved.
- root-suite.txt: full1884PASS/396.61s/exit0; all202selected input hashes unchanged.
- audit-before/after.txt and verification.json:73existing v1/v2/proposal files
  byte-identical,14published v2payloads/13inherited payloads/52F0pins verified.
  Exact reviewed ledger aef3daa5ebbe434f97b016719f8762d4aaf09441 and418manifest
  entries verified; no fresh Forge/RPC/test claim. Its E/Fbase/q2/bit7 manifests
  validate under both revisions; four successful operation examples also validate.
- launch-check.txt/diff-check.txt: exit0. REVIEW.md is correlated author review
  under the explicit no-extra-agents rule; weaker than an independent reviewer.

Positive new E and historical E/F controls prevent vacuous deny-all validation.
Every missing source, extra source, malformed hash, wrong marker/profile/wire family,
unknown revision/path fallback, nested ABI hash and duplicate JSON key is tested.
D50 hashes match pinned vectors under the successor. The schema still does not
prove source/ABI/runtime truth; independent context reconstruction remains required.

Tools: Python3.13.13, pytest9.0.2, jsonschema4.26.0, eth-account0.14.0, Git2.54.0.
No dependency/tool change. inputs-before.json pins selected evaluator sources/tests,
interface fixtures/schemas, root locks/spec/plan and acceptance records including
dirty changes. This is a selected input bracket, not an exhaustive raw-RPC archive.
Existing historical E evidence is unchanged; no fresh full ledger/protocol suite,
TLC, native scenario, timings, integrated E parity or F gate was run.

## Peer state and next steps

Fresh fetches succeeded. Final communication provenance reads355paths/no divergence,
Agent1 tip2b3d389278ecd83d67a10a5d7e4610da90fcae95 and Agent2
tip34af33d1efbf4af57cea5c5ddf282da48cfc6f04. peer-review.json records the mailbox
hashes and source deltas. Agent2's pool/StateCheckpoint/AccessDecision service work
is partial, with no complete READY. Its tests/mutants are owner reports, not rerun
or adopted here. No source READY/publication mapping ACK/execution ACK inferred.

A3-0079 requests both owners' exact publication receipts and migrated source READY/
mapping evidence. Existing accepted F implementation may continue. Agent3 resumes
anchored B/getter/wiring/fixture context and exporter history/orphan/WAL/native joins,
then fault oracle/model. Complete source READYs and separate exact execution FREEZE
with affected ACKs precede integrated services/scenarios. All32Fcases/GateF NOT_RUN;
G locked; qualified historical E unchanged. No human action needed.

Scheduled file flock acquired before repository/memory work; separate coordinator
held before fetch through publication. Neither lock inode is deleted. Normal owned
agent-3 publication/independent remote SHA and final cleanup recorded in automation
memory. No peer module/mailbox, archive, old interface/proposal, dependency or main
push. PLAN.md documents expand-only rollback and bounded scope; prepare.py refuses
to overwrite a publication. verify.py is read-only. Publication receipt ACKs remain
empty until the owners actually send them; later acceptance must use a new sidecar.

First staged diff check exited2 on trailing whitespace in pytest's raw RED
output. The original is preserved losslessly as red.txt.gz with unchanged raw
SHA-256 plus compressed hash in commands.json; no source/test result was altered.
Final staged-diff checks and publication receipts are saved in the external run.
