# Scoped review of A2-0066

Classification: tested reconstruction/extension result; deliberate mutation
controls. Paper-derived HMBC2020 reconstruction. No original-paper vulnerability
or incorrect authorization/binding claim. Author review is correlated; the human
prohibits extra agents.

The twelve-path delta is pinned at publication
0297adb6e784b9667befbc6330e1dfcb3ec81e3e, compared with
3b86183b8f537e32fc2f2c3be8b650735ab8173a. The sole production change is
rpc_binding_view.py at file-changing commit
1d667b93b28a79c4648c947ac9380d4169fa7fb5. It requires the full minimal lowercase
hex quantity spelling before conversion. It also re-encodes each decoded getter
result and compares exact bytes. This closes the earlier prose/decoder mismatch
without changing the D50 request schedule, preimage, shared wire or dependency.

## Independent before/after controls

The same probe script uses hand-assembled ABI words and synthetic raw-reply
clients, without the owner test helpers, transport or ABI encoder as an expected
result generator. The previous434-file scratch snapshot is hash-verified before
the old-source run. It reproduces all eight acceptance gaps and exits1 on the
explicit refusal assertion; this is the expected baseline failure, retained in
baseline-probes.txt.gz. Fifteen valid/malformed controls still pass.

The new source passes all fifteen controls and twelve refusal properties, with
zero acceptance gaps. Canonical quantities including odd-length positive values
and canonical uint/bool/address/address-array replies retain their values.
Trailing bytes for all four ABI types and a non-minimal array offset refuse.
Negative, plus-signed, whitespace and negative-latest-block suspicions remain
refuted as in the previous review. Labels from the old diagnostic probes are
retained for exact row comparison; their actual outcomes describe the new source.

Focused owner RPC/binding-open tests pass153/153, including all47synthetic RPC
tests and106binding-open tests. The no-live fixture selector/setup guard is
retained. These tests use temporary loopback HTTP fixtures; no Anvil, ledger
deployment, protocol service or integrated scenario is launched.

Fresh owner mutation runner:32/32detected after an unmodified passing control,
442.764s/exit0. Default9export files match.

A2-0066 reports7live plus47fake-node tests and its own mutation trials. The live
results are read and hash-pinned owner evidence only. They are not independently
rerun or adopted. The owner preserves10initial red cases, a test-constant mistake
and the32/33mutation trial with equivalent R38 removed. No peer evidence is edited.

## Limits and next action

Rejecting non-minimal node quantities is the owner's explicit parser policy.
These probes do not authenticate a node or prove native source-state truth,
reorg safety, complete exports, timing, durability, secrecy or Byzantine consensus.
Reads still select block NUMBER without a hash-pinning/reorg bracket guarantee.
The carried chain.py parser was not re-audited. D56's extra evaluator Governance
reads remain separate from unchanged D50 S0.

Witness-side views, Worker factory, CLI, supervised witnesses, real transport/clock
and H2/H5/H6 coverage remain pending. The runtime recipe must supply the exact
reviewed published schema, retain check_responses=True and validate handler
behavior. A2-0064 remains the latest isolated source READY, with no peer consumer
mapping ACK or full runtime READY inferred from this partial correction.

Agent2 can continue its owned runtime wiring and then publish a complete exact
READY/mapping. Agent3 next reviews source-state/sign-time and the exact producer
schema/path/lock choreography for store/export row completeness, then the fault
oracle/finite model. Complete runtime READYs and separate exact execution FREEZE
ACKs precede services/scenarios. C-F1 WORKING; qualified historical E unchanged;
all32Fcases/GateF NOT_RUN/G locked. No human action required.
