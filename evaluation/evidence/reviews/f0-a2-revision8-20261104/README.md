# Revision 8 review: bindings reproduced; two export-layout corrections

F0 specification review of the paper-derived HMBC2020 reconstruction. Synthetic
fixtures only. No F implementation, mapping ACK, freeze or RQ gate result.

Inputs are Agent2 `e5796bc80da7683d48a96b500360d666bcec522d` (A2-0055 was
introduced by `64ec86acfac2a8d3db337782e34c1b7b7e1f84b7`) and Agent1
`8f34694c8f423841148372e5672fde35e3b2659c` / A1-0106. Exact file-changing
commits, SHA-256 values and all 328 latest communication-path selections are
in `input-provenance.json`; no incomparable conflicting revisions were found.
A1-0106 is a ledger-facing design ACK, not a schema mapping or execution ACK.

Reproduce from the repository root, without installs or services:

```
python3 -B evaluation/evidence/reviews/f0-a2-revision8-20261104/review.py
```

The review verifies 350 ledger + 142 protocol E + 50 protocol F0 manifest
entries. Owner specification helpers run in an exact disposable Git snapshot;
all 231 snapshot files retain their pre-run hashes. No peer checkout is edited.
`owner-commands.json` records commands, UTC intervals, exit codes and source/log
hashes. `commands.json` records the coordinator invocation and local checks.

## Results and scoped acceptance

The independent encoder reproduces all three D50 bindings:

| Document | SHA-256 binding |
|---|---|
| E baseline | `242f7ca6977e22c97b6c1940cbc225136e9d4af71932aa7b08f156d9ed14aede` |
| E mutant-no-nonce under repaired-e base name | `ecfd60f07cce6a4b3c4057152ba675cd951650a94acb1cbf886857ccb74c266a` |
| F, now interfaceVersion v2 | `798f7d722b2c3a5d81500aa8761f6dff32a519a8e0857d9341bee1bdef00fc54` |

The new F document differs from candidate1 only in interfaceVersion. The E
baseline and immutable-reference vector are unchanged. An independent table
derived from the ledger's `tools/make_manifest.py` matches all ten profile
entries; all 14 published profile cases agree, including refusal precedence.
No free-text `mutantNote` is used for classification.

Fresh owner helper results, all exit 0: D50 126 expectations / 15 of 15
mutants; wire 77 checks / 36 of 36 corruptions; export layouts 62 expectations /
24 of 24 mutants. These checks establish their stated specification coverage,
not complete correctness. Seven additional coordinator probes expose the two
gaps below while preserving positive and negative controls.

A3-0068 ACKs D50 revision5 and the SUCCESSOR-WIRE revision8 adapter-response
rules in coordinator scope at the exact hashes. This explicitly excludes the
new exporter definition to which the wire points. A3-0069 withholds the layout
ACK pending L1/L2. No final candidate2 pins or production interface are adopted.

## L1: historical effect equality is not a no-op supersession

**Class:** extension specification inconsistency, with a tested specification
checker result. Not a measured runtime or paper vulnerability.

`SIGNING-RULES.md` section2 permits a different effect after all digests of the
current effect are dead. It imposes no ban on returning to a historical effect.
For one unexecuted Governance nonce, let both ADD tuples A/B be approved, with
distinct roots that remain non-authorities. Sign A at time t, expiry t+60; observe
its expiry, sign B at t+61, expiry t+121; observe B's expiry, sign A at t+122,
expiry t+182. Nothing is executed; the nonce and TMSC preconditions are unchanged.
All TTLs are 60 seconds, below the proposed 120 bound. The target-chain block
numbers/timestamps grow. This is a legal A→B→A history under the signing rule.

`EXPORT-LAYOUTS.md` section3 instead requires **every** superseded effect to
differ from the current live effect for K. The checker lines287–289 therefore
rejects the oldest A, although it was superseded by B, not by the current A.
The paired A→B→C history passes. Both documents and the exact rejection are in
`layout-probes.json`. These are layout fixtures, with placeholder signatures;
they do not demonstrate an actual witness execution.

Requested owner correction: make the document and checker compare successive
generations for the same K, or otherwise specify a consistent history rule that
admits the legal recurrence. Preserve rejection of an actual adjacent same-effect
no-op; do not simply remove all supersession checking. Preserve sequence, digest
uniqueness, death and target-chain checks. Publish exact amended bytes/tests.

## L2: ALLOW-only grant-death guard is missing from the checker

**Class:** tested specification-checker omission. A deliberate invalid fixture
is accepted; no claim about a runtime witness is made.

Both SIGNING-RULES section6 and EXPORT-LAYOUTS section3 say that
`overtaken-decision-grant` applies to an ALLOW decision only. The checker verifies
the AccessDecision type but never requires `effect.result == "1"`. Starting
from its history vector, a grant-death ALLOW passes; changing only the result to
DENY (`"0"`) and refreshing vHash/evidenceSha256 also passes. Ledger truth is a
runner obligation, but the result tag is already in this document and needs no
RPC or signature recovery to reject this contradiction.

Requested owner correction: enforce ALLOW for this death kind, retain its valid
ALLOW positive and DENY via expiry/sequence positives, add this exact invalid
case and a mutation that removes the guard. Keep ledger existence as a separate
runner obligation; a layout check cannot prove it.

## Limits and next permitted step

No production ledger/protocol/export/test-only bytes changed; comparison is
against pinned owner blobs, not a new runtime regression pass. No Forge, TLC,
RPC, actual witness/store/pool/exporter, full suite, timing, crypto recovery or
F gate ran. Owner-vector signatures are placeholders. Same-model review is
correlated. Historical candidate1, incomplete preparation, frozen v1 and
qualified E evidence remain unchanged. All 32 F cases remain NOT_RUN; G locked.

Agent2 publishes the exact layout amendment and tests first. Then Agent3 reviews
it and completes candidate2 with M1–M4/P1–P7/N1–N4, including Agent1's V2-named
ABI-container note and the mutant death-rule exclusions. Both complete mapping/
layout ACKs and a separate F0 freeze still precede implementation. A1-0106's
bit1/bit5 warning is retained: sequence/grant-receipt death reasoning under
affected deliberate mutants is not baseline safety evidence. No human research
action is needed.

Operational diagnostics: the first coordinator audit invocation used the wrong
ledger generator path (`ledger/script` rather than `ledger/tools`) and exited1;
the failed Git lookup exited128. The corrected invocation exited0. No owner
source or expected result was changed to fix this path error. Initial mkdir on
the existing scheduled flock file failed harmlessly; the documented persistent
file flock was acquired before repository review. Lock inode presence never
counts as an active run. Both actual locks are held through publication and
released on completion; the automation memory records cleanup.
