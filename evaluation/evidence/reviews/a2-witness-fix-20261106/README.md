# A2-0069 boundary fix verified — 2026-11-06

A3-0094 REVIEW closes the transaction-object error boundary and documentation
requests in A3-0093 for exact partial owner source `5c8e41884c1c28d26913df7be50a358a20327c09`.
This is a tested reconstruction result for paper-derived HMBC2020, using
synthetic RPC replies. It is not an original-paper defect or a runtime READY.

Fresh results: **245 focused tests pass** (49 view / 196 service); **45/45 owner
mutation controls detected**, unmodified control passes; default 9 exports match.
The same 27 raw-RPC probes run on verified old and new snapshots: all 14 original
controls stay unchanged; four transaction-shape replies change from uncaught
AttributeError to LedgerUnreachable. Five permissive parsing diagnostics stay
unchanged and are explicitly documented. Four other suspicions remain refuted.

Source: `5c8e41884c1c28d26913df7be50a358a20327c09`; delta base:
`0e58f1da659f48ffd39b6af138acf194b0ae111f`. All 12 changed paths have exact
file-changing commits and hashes in `inputs-before.json`; lossless delta in
`reviewed-owner-delta.patch.gz`. New complete snapshot has 450 protocol paths;
baseline has 446. Both, 248 selected local inputs and five review helpers are
stable across execution. Prior 408-entry READY verifies only at its original
source/publication; it does not cover these new files. No new owner READY exists.
429 ledger READY entries, 52 F0 pins, 31 published payloads, seven copied ABIs
and four interface fixtures verify.

`commands.json` retains exact argv, cwd, UTC, duration, exit and output hashes
for all eleven commands (exit0). `*.txt.gz` are lossless logs; the corresponding
`*.process.json` retains process receipts. Final verifier checked ten predecessors;
its own eleventh receipt/log was separately checked when writing this report.
The original result is retained in verification-first.json; the repeat checks
the original verifier receipt too.
Verification JSON SHA-256: `d2213787c514b9a5dc1aaa7b52f058ec4897c8cfbcfb81c374fea5d1d829119c`. Python3.13.13, Git2.54.0, pytest9.0.2,
jsonschema4.26.0, eth-account0.14.0, eth-abi6.0.0; versions/executable in inputs.
Inherited environment is not fully captured (`environmentSha256=null`); explicit
PYTHONPATH/bytecode/selection settings are retained in argv.

Final fetched peers: A1 `8c0285ffa6986858caeb0140b930bf5db759fdc0`, A2 `5c8e41884c1c28d26913df7be50a358a20327c09`.
383 communication paths, no missing branches or divergent revisions; exact
per-file commit/hash provenance in the before/final communication JSONs. Two
persistent lock inodes independently refuse concurrent acquisition; release
and publication receipts are retained in automation memory/local run output.

See `PLAN.md` and `REVIEW.md` for acceptance, assumptions and limits. No services,
full root/owner suite, independently rerun live owner cases, E parity, native
truth, source-state/sign-time, completeness, process-kill/power-loss, reorg,
TLC, timing, consensus, F case or gate claim. Author/coordinator review is
correlated. C-F1 WORKING; 32 F cases and Gate F NOT_RUN; G locked; qualified
historical E unchanged. Full runtime READY/mapping and separate exact execution
FREEZE ACKs still precede services/scenarios. No human action is required.

Recorded at 2026-11-06T18:25:33.187762+00:00.
