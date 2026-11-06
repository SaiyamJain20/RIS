# Review disposition

A2-0070's two skipped sequences are reproduced on the exact READY ledger by an
evaluator-owned Forge harness. The frozen SIGNING-RULES already describe both
the monotone contract predicate and honest current+1 duty, including poisoning
with q=3 colluders. Do not classify this as a new paper vulnerability or claim
that the contract was intended to require consecutive sequences.

One follow-up for Agent2: qualify the claim that honest witnesses continue after
sequence burning. The ordinary 5/7 examples do; accepting maximum uint64 leaves
no representable successor, and the proposer refuses max+1 as out of range.
This remains a known out-of-bound key-compromise boundary, not an f=1 failure.
No contract patch or shared-interface change is requested by this review.

The harness checks successful installation/readback, refused lower/replay values,
insufficient quorum with subsequent legitimate success, boundary values and
256 seeded fuzz inputs. The Python probe checks unchanged evidence on honest
skip refusals plus a valid persisted real signature. It imports owner test
fixtures only for this isolated review; it is not a runtime integration consumer.
No negative experiment is credited merely because a helper crashed.

A2's governance codes are corroborated statically. Its live table, 62-test run
and rollback claims remain owner evidence. The later A2-0071 CLI/worker source
and results are separately identified as pending independent review.

Review limits: same agent authored and reviewed these proof helpers, so review
is correlated. Forge's owner fixture simulates the two domains in one EVM;
no two-node integration, witness processes, timing or consensus claim follows.
The honest-view probe uses production hashing/recovery and store code with an
injected view, so it authenticates no native ledger observations. Natural honest
sequence exhaustion is not measured; the maximum is installed deliberately.
