# Native history RPC capture — author review

Classification: synthetic tested reconstruction/extension. Correlated author review
under the explicit no-extra-agents rule; weaker than a fresh independent review.

Reviewed new collector, tests, source brackets, peer deltas and selected evidence.
Existing native/history verifiers and consumers are unchanged. No schema, source
owner, frozen byte, dependency, phase or experimental timing requirement changes.

The collector verifies declared signatures before I/O, constructs exact public ABI
calldata and deduplicates only identical chain/hash/contract/data reads. All declared
observations, fault/clear rows and embedded source references enter the capture plan.
The existing verifier checks captured number/time identities, signatures, real ABI
return facts, unused/missing captures and bit1/bit5 exclusions after acquisition.

Both deployment identity groups bracket all cross-chain reads, even empty histories.
Every selected block hash is re-read; safe-labelled blocks are also checked against
the canonical number mapping. Death calls use EIP-1898 hash objects with explicit
requireCanonical. Faulted/cleared histories retain both hashes at one height and
stay labelled conditional; no false canonicality assertion is added.

The raw transcript retains requested method, parameters, selected origin and returned
API values or exception type, including failed and timed-out calls. Mutating transport
arguments cannot rewrite the recorded request. A result path appears only after
checks, complete verification and budgets; existing output paths refuse overwrite.
The caller's source containers, RPC selection/origins and ABI contents are checked
again. RpcClient's independent command logs provide actual subprocess/tool receipts
when a later authorized recipe uses it. Synthetic client.url is merely an assertion.

Review added five behavioral controls (all passed without production edits): PBC
identity changes during DBC reads, hash-header time drift after death calls, safe
canonicality mismatch, unsupported hash calls without fallback, and argument mutation.
Seven in-memory guard removals admit false inputs rejected by the real collector.
These controls establish test sensitivity, not an exhaustiveness claim.

No unresolved Critical/Important finding in this slice. Declined to judge: actual
pinned-node EIP-1898 support, honest/authenticated RPC, transient endpoint changes
that return to the same identity, source-state/sign-time semantics, real store row
projection/completeness/lock choreography, transport timing and physical durability.
These require later reviewed source/recipes; they remain explicit limitations and
are not silently counted as satisfied. No independent reviewer or owner test rerun
is claimed. The required root suite result and stable source bracket are recorded
in README/verification.json after completion; this review alone is not completion.
