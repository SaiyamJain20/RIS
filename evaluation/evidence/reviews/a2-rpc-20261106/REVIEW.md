# Scoped review of A2-0065

Classification: tested reconstruction/extension results and explicit parser
choices. Paper-derived HMBC2020 reconstruction; no original-paper defect claim.
Author review is correlated under the no-extra-agents instruction.

## Actionable owner finding: quantity parser accepts separators

At source 3b86183b8f537e32fc2f2c3be8b650735ab8173a,
`protocol/hmbc_protocol/rpc_binding_view.py` lines 116–122, `_int` checks only
string/prefix/length before `int(v, 16)`. A raw `eth_chainId` reply `0x1_0`
returns decimal string `16`. `0x01` and `0xA` also normalize to `1` and `10`.
These are accepted by the existing public API despite the module's broad claim
that malformed/noncanonical replies are refused. The separator case contains a
character outside a hexadecimal digit alphabet. The returned numeric value can
still equal the expected manifest value; no false authorization or bad binding
was demonstrated.

Agent2 should reject separator-bearing quantities before conversion, with a
focused regression. If the intended contract is canonical lowercase quantities,
apply its full spelling rule consistently to chain IDs and block numbers; retain
`0x0` and odd-length canonical positive quantities. This is an owned parser fix;
Agent3 does not edit protocol code or prescribe a new shared wire contract.

## ABI canonicality is weaker than the prose

Hand-assembled canonical uint/bool/address/address[] returns still decode with
trailing `deadbeef`; the decoded values are unchanged. An address array with a
64-byte offset and an unused word also decodes. `eth_abi.decode` is not an exact
canonical encoding comparison. These five observations do not demonstrate an
incorrect D50 result and are not elevated to an authorization vulnerability.
Agent2 should narrow the broad canonical-refusal claim or, if exact canonical
return bytes are intended, enforce the chosen policy and test it. Do not silently
turn an internal parser policy into an additional D50 request or schema rule.

## Refuted suspicion and positive controls

Negative, plus-signed and space-containing quantities (`0x-1`, `0x+1`, `0x 1`)
are REFUSED. A latest block with number `0x-1` is also REFUSED. The initial source
inspection suspicion about negative values was not reproduced. Preserve all four
refuted probes. Fifteen controls pass, including canonical quantities and four
ABI output types, malformed quantities, short uint, invalid bool and bad address
padding. Twelve separate property probes produce eight permissive acceptances;
a successful probe command is not twelve passing refusal properties.

## Source, tests and owner correction

The sole new runtime module is RpcBindingView. Its seven ABI fixtures match
Agent1's exact 85c59f5 export bytes. All 434 tracked protocol entries at this source
are hashed and checked in scratch before/after execution. Of the previous READY's
408 entries, only `protocol/evidence/af2-state/README.md` changes at this later
source; the previous manifest still verifies at its original source/publication.
No new runtime READY manifest is inferred from Agent3's review inventory.

Fresh isolated selection: 2072 PASS / 201 schema-review SKIP / 206 DESELECT,
42.25s pytest / 42.663s command / exit0; includes all26 new non-live RPC tests.
All7 new live tests are explicitly excluded. The selector and setup guard add
`live_f` and `live_e` to the existing prohibited chain/build fixtures. The tests
use synthetic loopback HTTP servers, which terminate within the test fixtures;
no Anvil, ledger deployment, protocol service or integrated scenario is started.
Default9export files match. No owner mutation runner, live7test result, full
owner suite or evaluator root suite was rerun/adopted in this review.

A2-0065 corrects the prior owner claim that Foundry was absent: their carried
fixtures use an installation outside PATH. Their reported live F/E deployment
checks and earlier full-suite live coverage are owner evidence only. Their new
live test source and output are hash-pinned in inputs-before.json. This correction
does not convert Agent3's explicitly isolated selections into live evidence and
does not establish a new E parity or F gate. Existing frozen evidence is preserved.

## Remaining boundaries

Reads are selected by block NUMBER. No EIP-1898 hash selection or reorg bracket
is implemented in this view; this is a disclosed safe-ledger limitation, not a
newly discovered consensus flaw. The binding document records an anchor hash but
that alone cannot prove all reads came from it. D56's separate evaluator reads
of both Governance getters and compiled MAX_ADMINS remain necessary; do not alter
D50 S0 or its48/55request schedule without an exact RFC and affected ACKs.

Witness-side views, Worker factory, supervised witness processes, CLI, real
transport/clock and H2/H5/H6 coverage remain pending. Exact supplied published
schema and enabled response checks remain runtime recipe requirements. Full
runtime source READYs/mapping plus separate complete source/tools/config/run
FREEZE ACKs precede integrated services. C-F1 WORKING; qualified historical E
unchanged;32Fcases/GateF NOT_RUN/G locked. No human action required.
