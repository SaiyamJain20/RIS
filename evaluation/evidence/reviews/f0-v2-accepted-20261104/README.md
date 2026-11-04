# F0 accepted; exact v2 publication — 2026-11-04

Result: **F0 design accepted for owned implementation only. Integrated execution
remains locked.** A1-0110 and A2-0058 both ACK the entire freeze JSON SHA-256
`f9f0906faf8dbfb9ccd2d06a794c715bb6a3167b6f273a50347742db41196df5` in their
ledger/protocol scopes. These are genuine freeze replies, distinct from earlier
candidate8 design and candidate2 mapping ACKs. No source READY or run ACK is
inferred. The request's pending status remains immutable publication-time prose.

The separate acceptance is `communication/F0_ACCEPTANCE_CANDIDATE2.json`, SHA-256
`03dcf485668430b1f28552d2bbafcae9a6c64ff9df0090c50bcae753793a432d`.
`interfaces/v2/FREEZE.json`, SHA-256
`7bb1d243d546dcc6ab76dea3edcb23a74240bd96fe274ae3ca0ff56f6aff83cd`, publishes
all 14 candidate2 payloads byte-for-byte with their original paths/hashes. Their
old titles and pending prose remain unchanged; the sidecars carry live state.
The accepted candidate8 matrix still has 14 components and 32 NOT_RUN cases.
All controls, required evidence, numeric bounds and mutant exclusions remain.

## Exact incoming provenance

| Reply | Observed branch commit | File-changing commit | Message SHA-256 |
| --- | --- | --- | --- |
| A1-0110 | d8eddf1e9d194df29e8016e3749c9e0935b5e5a7 | d8eddf1e9d194df29e8016e3749c9e0935b5e5a7 | 864d0e456d55c500c9ffd05c30082643ffc28c3a03ef594c24e832ce782043b9 |
| A2-0058 | 5639e8f638645acf0bf122109f8bae2ffc2b6fc4 | 092a823233f8e912e676d7f88233369b2c08e3c0 | 78032a940997ba05ec4fd22d6f37e6b9d3de555ec268f0dfc112489f8abe3423 |

Agent2's later tip changes STATUS only. Exact message copies are in this
directory; hashes, headers, request relation and ancestry were checked. The
ancestry scan reviews 341 communication paths across the three pinned branches
and finds no incomparable conflicting bytes. It does not infer agreement from
timestamps, stale status prose or silence.

## Verification and limits

`commands.json` records exact argv, UTC, exit codes and stdout/stderr hashes.
`publish.py` checked inputs and receipts before creating the acceptance and new
publication. It is intentionally a one-time creation command, not an updater.
`verify.py` independently checks the resulting linkage, all 14 copied payloads,
4 historical base hashes, prior ACK hashes, preserved 32-case numeric plan,
350 ledger/142 protocol E/52 protocol F0/4 new owner-review manifest entries,
and 142 E source entries again at historical commit 376347d. Both exit 0.
Tools: Python 3.13.13, Git 2.54.0. No fixtures or cryptographic randomness were
generated; inputs are the previously ACKed synthetic candidate2 bytes.

The owner A2-0058 check log reports 33 specification checks and 0 failures.
Its four-file manifest and output hashes were verified; the owner helpers were
not rerun. Previously verified 385 schema/signature checks concern identical
candidate bytes and were not repeated. No new Forge, TLC, ProVerif, RPC, full
module suite, runtime pool/store/exporter, recovery, timing or gate run occurred.
This is specification/receipt acceptance, not a measured reconstruction result,
an HMBC vulnerability, or an implementation parity claim. Reviews use the same
model family and are correlated; no substitute reviewer/extra agent was spawned.

A2-0058 N-1 is resolved by the already accepted plan: historical E evidence and
inventories stay immutable at historical commits; approved F edits to E-listed
source receive new F source hashes. E behavior/assertions/default exports/legacy
fingerprints require actual isolated regressions, and later integrated E parity
needs exact new source/run ACKs. `communication/F_SOURCE_READY.md` states this
handoff rule without changing the candidate interface.

Next: owned test-first implementations and independent evaluator/model work,
exact source READY/mapping receipts, then a separate fully pinned execution
FREEZE and affected ACKs. No service lease exists. Qualified E remains historical;
F gate NOT_RUN, G locked. No peer module/mailbox edits, archive changes, worktree,
dependency installation, external deployment or main push occurred.

Recheck from the repository root, preserving evidence outputs if archiving a new
run (this command refreshes only this review's verification output):

```
python3 -B evaluation/evidence/reviews/f0-v2-accepted-20261104/verify.py
python3 communication/build_prompts.py --check
git diff --check
```
