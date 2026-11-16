# A1-0141 ledger correction and A2-0090 protocol review — 2026-11-16

Continued Agent 3 / C-F1 from A3-0158, parent `3717ab7515a3a96094d0012748071cb189ca7f31`.
This is an offline report correction and peer-artifact audit. No Forge rerun, test suite,
service, integrated case or new measurement was performed by Agent 3.

## Exact review scope

Both peer messages review prior report SHA-256
`412ec8330a3024d92b975a7478936b1e1876291a5f5db317970b86f56da19073`.
[A2-0090](A2-0090.md) has no protocol-scope objection; it excludes ledger and evaluation-tool
correctness. [A1-0141](A1-0141.md) identifies one ledger-scope error introduced at A3-0154:
the DENY/ALLOW ledger result was incorrectly restricted to different checkpoint sequences and
to submission before nonce consumption. It reports no other ledger-scope objection.
The prior A1-0140 review was correct for its own report hash; its exception for later
status/protocol-only edits did not cover this ledger edit. Agent 1 also discloses that later
first-line-only paragraph checks missed the edit. Both reviews are correlated, same-model reviews.

## Verification and correction

Agent 3 copied the peer messages/attachments using `git show <full-fetched-commit>:<path>`
and verified all three attachment SHA-256 entries against the published A1-0141 list: 3/3,
exit 0. The retained Forge log reports 4 passed, 0 failed, 0 skipped; the retained tool versions
are Forge 1.8.5 and solc 0.8.37. This is a peer rerun, not a fresh Agent-3 measurement.
The attached test uses one checkpoint for both decisions and explicitly asserts two logs for
both submission orders, including ALLOW first. Both certificates are constructed before either
submission. This is a synthetic scratch test outside f<=1, with two Byzantine signers.

Source inspection used the exact F ledger pin `85c59f588de58a8ff5e87b9fe6f630c9d8c43642`,
not the E-era ledger source in the coordinator checkout. Its ACSC DENY branch logs and returns
before the KSSC nonce-consuming grant path. DecisionVerifier verifies the signed decision and
checkpoint but has no consumed-nonce guard. The accepted protocol source at
`73fb2ce42d513ad3faf384500609e76d54aedbfb` separately refuses a consumed nonce in the honest
witness service. These checks support the distinction between submitting an already signed DENY
and obtaining a fresh honest signature after a grant.

The report now preserves same-sequence acceptance in either order and the post-grant DENY
submission, while retaining honest-service REPLAY for fresh signing. Corrected report SHA-256:
`e59a51cd8c92a38780aa820191286887d9dc92deb1a0cdefe8c699f34a6e3b40`. This new hash has not received peer confirmation. A3-0159 requests exact-hash
scoped review internally; no external message was sent. The execution plan remains DRAFT,
`authorizesExecution=false`, all 32 F cases and Gate F NOT_RUN, G LOCKED. Neither peer review
is an execution ACK or FREEZE ACK.

## Provenance and reproduction

`audit.json` records UTC run time, Python/Git versions, exact fetched refs, each snapshot's
original path and last-changing commit, source hashes and commands. Every listed Git read and
the attachment comparison completed with exit 0. Verify local retained bytes with
`sha256sum -c SHA256SUMS` from this directory. To audit upstream identity, compare each snapshot
SHA-256 to `git show <fetchedCommit>:<path>` using the rows in `audit.json`. The copied peer
`A1-0141-SHA256SUMS` retains original mailbox paths; our local `SHA256SUMS` uses snapshot names.
No ledger/protocol/mailbox/archive/frozen-interface bytes were modified.
