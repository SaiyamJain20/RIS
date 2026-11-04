# Revision9 export-layout amendment review

Classification: tested extension-specification/checker result, not a runtime or
paper vulnerability. Synthetic fixtures only. No F implementation or gate run.

Reviewed A2-0056 introduced at52f39437771b0d5615b29015725c9f91d469d976,
observed atdcad9745a594770654810ca366ed78c6e559539f; the intervening change is
Agent2 STATUS/HANDOFF only. Agent1 8a943a7c64e881ac0686587f01a9ebfaf2368706
contains A1-0107/0108, the ledger facts and scoped revision9 re-ACK. Complete
333-path communication selection uses file-changing commit ancestry, not mtimes;
no incomparable conflicting revisions were found. See input-provenance.json.

Fresh verification:350 ledger/142 protocol E/52 F0 manifest entries agree with
their exact owner blobs. D50r5, wire r8, signing rules and their selected helpers
remain byte-identical to64ec86a; their unchanged suites were not rerun. The three
D50 bindings and14 profile cases are independently reproduced from declared data
and the ledger generator's closed table. All233 scratch input files retain their
pre/post hashes (scratch-input-hashes.json); no peer checkout was edited.

In the exact disposable protocol snapshot, both changed owner commands exit0:
76 layout expectations and29/29 mutation controls. Fifteen independent coordinator
probes preserve ALLOW grant-death, DENY expiry/sequence, A->B->C and A->B->A;
reject grant-death DENY, either adjacent equal generation, premature generation,
duplicate seq and death before expiry. Equality at the prior death observation
is permitted; the explicit fault-clear exception is retained.

A3-0070 accepts the exact EXPORT-LAYOUTS revision9 design in coordinator scope.
Retain generation order: each K fixes a target chain, and the mined observations
must not precede the death that permits re-signing. Equality is legitimate.
Raw block hashes and all ledger facts still need independent runner joins.
The checker deliberately does not prove completeness (including an orphan
superseded K), signature recovery, grant existence or receipt execution; the
candidate2 BOUNDARY makes these explicit future runner obligations. The byte
mapping ACK on the complete candidate2 unit remains pending from both owners.

Reproduce: python3 -B evaluation/evidence/reviews/f0-a2-revision9-20261104/review.py.
owner-commands.json records source/log hashes, UTC intervals and exits. The final
outer invocation and checks are recorded in sibling
f0-v2-candidate2-20261104/commands.json. The initial outer trial's UTC interval
was not captured; final invocation metadata is complete. Python3.13.13/Git2.54.0.

No runtime store/exporter/witness, RPC, service, Forge, TLC, full suite, measured
timing or cryptographic recovery ran in THIS layout review. Owner layout
signatures are placeholders. Same-model review is correlated. Candidate2's
separate verifier performs real recovery on its separate synthetic signing
vectors. All32 F cases NOT_RUN; G locked; qualified E/frozen v1 unchanged.
