Message-ID: A3-0079
From: agent-3
To: agent-1, agent-2
RQ: F
Task: C-F1 / additive E carrier schema publication
Type: READY
Interface-version: v2 wire family; explicit v2.1 schema revision
Responds-to: A1-0114, A2-0060, A3-0078, A1-0112
Source-manifest: interfaces/v2.1/FREEZE.json sha256 232b84bb7f997b687a5dc671d79ab6ecdd592d17cd38e531d8460d33ed81660a; schema sha256 d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3

Summary: INTERFACE_READY for the separately published additive E source-closure
schema. Exact proposal ACKs of manifest7810ad105330de73920450d82f4850ebb6de0846396e5bb786818e700e49bb0a
are verified: A1-0114 introduced/observed2b3d389278ecd83d67a10a5d7e4610da90fcae95,
message sha256b55ce757215305d41152b069487a8d4f6950a02c2980ccae9f8a95ea390e89f9;
A2-0060 introducedb35d014012765ce96424365e714f76fe8de48482, observed with latest
source34af33d1efbf4af57cea5c5ddf282da48cfc6f04, message sha256f5b462be848c8f1cb7a2632e5991f372dde2d23b9af5736cf4b18ae5ca03c6c1.
Receipt communication/E_SOURCE_CLOSURE_ACCEPTANCE.json sha256
511e235f3aff86a57822e26136282f97bcb9550e84c95263b14ed1bbab8e9fb6
records the original ACK observationd689e38a32b33ad2caa69b7b7000e4fe592b5fdd.

The new schema equals the base plus precisely the two ACKed additions.135old
non-union definitions/all other top-level values remain equal. The copied x-status
annotation stays byte-equivalent to the ACKed proposal (A1's note is useful;
publication README supplies live status without silently changing the patch).
Wire family v2, old schema/freeze, all proposals, D50 preimage, thirteen inherited
payloads, F carriers and default v1 unchanged. Explicit schema_revision='v2.1'
opts the isolated evaluator into the new branch; default v2 still refuses it.

Evidence: evaluation/evidence/f/e-source-closure-publication-20261104/README.md,
PLAN/REVIEW, exact ACK copies, provenance/source/tool/input/output hashes and
commands/UTC/exits. Tests-first27RED ->226focusedPASS;68existing validator tests
also PASS on successor; full root1884PASS/396.61s/exit0/202selected inputs stable.
Four actual reviewed E/Fbase/q2/bit7 owner manifests and four successful operation
examples remain compatible.14v2payloads/73old interface-proposal files/52F0pins/
418reviewed ledger entries verified. Correlated author review; no extra agents.

Impact: owned opt-in migration may now proceed. Old ten-source E remains historical
compatibility with its known omission. New F-tree E successor uses the v2.1 marker
and twelve-source map; no source field enters D50 B. Whole-manifest equality stays
mandatory. Agent2's partial pool/service progress is read, not source READY; no
owner tests rerun/adopted here. No integrated service/runtime/TLC/new E parity or
gate result; qualified historical E unchanged,32Fcases/GateF NOT_RUN/G locked.

Action requested: BOTH owners receipt this exact new freeze/schema hash in affected
scope. Agent1: migrate opt-in E successor export, retaining default v1, and publish
new source READY/mapping evidence. Agent2: explicitly select successor schema in
adapter/tests with whole-manifest equality, retaining D50 preimage; publish matching
source READY/mapping evidence. Prior A3-0077 still reviews exact aef3daa F exports
for isolated consumption; no need for another READY just to relabel old log prose.
These proposal ACKs/new publication are not a complete source migration or execution
ACK. Complete source READYs and separate run/tools/config/source FREEZE with exact
affected ACKs precede integrated services/scenarios. No human action required.
