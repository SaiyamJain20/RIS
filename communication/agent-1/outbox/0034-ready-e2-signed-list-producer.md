Message-ID: A1-0034
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: E2 preparation (ledger-owned, prepared ahead and disclosed): TEST-ONLY signed trust-list producer for the E02 schedules
Type: READY
Interface-version: v1 (FREEZE f700292e..); a new owner export element `hmbc-ledger-signed-list/v0` whose `item` uses frozen v1 wire shapes
Responds-to: A1-0030 (its "E2 list mode" limit), A1-0033
Source-manifest: ledger/evidence/source-manifest.sha256 sha256 b99b83e509a4ce42992df63a6fdbf42300756cef07942720e8a711ebed697fe7 (143 entries, `sha256sum -c` 0 failures), at the commit carrying this message

Summary: **The E02 schedules now have a ledger-owned input producer**, as the E1 bootstrap does
(A1-0030). Those schedules are signed-list rollback, pre- and post-barrier revocation, expired duty
and equal-version content.
- `ledger/tools/sign_list.sh` signs one RevocationList or TemporalAcl for a pinned deployment:
  version, validity, revoked serials and OnDuty windows.
  - It is read-only and writes no key.
  - Its `item` has exactly the shape of a bootstrap `trustLists` entry.
- **Prepared ahead of E2 and disclosed as such:** no E2 case was run and no gate is claimed.
- **Owner live check:** 24/24 on paper-strict, paper-minimal and repaired-e. Every E02 trust-anchor
  behaviour lands on the frozen native codes.
- Contract sources, tests, deploy, bootstrap producer and exports are unchanged since 25d1e6b. The
  only test-utility change is two `envOr` list cheatcode declarations in `test/utils/Vm.sol`; forge
  is 166/0 and check_mutants 7/7 after it.

## Contract

- **Command:** `ledger/tools/sign_list.sh <pbc-rpc> <deployment.json> <out.json> <crl|tempacl>
  <H1..H4> [--version N] [--valid-for S] [--revoke s1,s2] [--duty label:fromAgo:untilIn]...`.
  - The version defaults to the on-chain version + 1. An explicit `--version` allows equal or older
    content.
  - `--revoke` serials must be strictly ascending, and `--duty` entries must be in ascending gid
    order; otherwise TMSC rejects with MALFORMED.
  - It refuses (exit 1, no file) on an unknown authority or a chain/address mismatch.
- **Output** `{schemaVersion "hmbc-ledger-signed-list/v0", testOnly, binding (as A1-0030), item
  {kind, call, submitterRole, submitter, list, signature, signer}}`. The runner submits `item.list`
  and `item.signature` via `item.call` from `item.submitterRole` (CA-Admin key only).
- **Old-list replay needs no producer call:** replay an earlier artifact, such as the bootstrap's
  `trustLists[0]`, unchanged.

## Owner live check (`ledger/evidence/signed-list-check/`; `tools/check_sign_list.py`, exit 0, 117 s)

| Step (TMSC.checkCredentials(alice) after it) | paper-strict / paper-minimal | repaired-e |
|---|---|---|
| OnDuty window ending in 3 s, read after 5 s | EXPIRED | EXPIRED |
| window restored (next version) | NONE | NONE |
| H1 CRL revoking serial 101 | REVOKED | REVOKED |
| replay of the bootstrap's older signed H1 CRL | **accepted, Alice NONE again** (rollback, SPEC_GAP) | **Rejected(STALE_ANCHOR)**, Alice stays REVOKED |
| equal version, different content | accepted | Rejected(STALE_ANCHOR) |
| unknown authority H9 / DBC RPC | refused | refused |

- The 12 produced lists (48 leaves) are valid against the frozen schema, and 0 private keys appear.
- **Disclosure:** a first run exited 1 (22/24) because of a typo in my check's expectation table
  (paper step-4 submission written "NONE" instead of "ACCEPT"). The ledger behaviour was the same. I
  fixed the table and re-ran from fresh chains; the evidence is the re-run.

## How the E02 cases use it (ledger facts; the schedules and oracle are agent 3's)

- **signed-list-rollback:** install a revoking v2 via `sign_list.sh crl H1 --revoke 101`, then
  replay bootstrap `trustLists[0]`.
- **pre-/post-barrier revocation:** revoke via `sign_list.sh`. Before vs after a new accepted
  checkpoint is the runner's ordering (`collect_checkpoint`/`acceptState`). The barrier is
  DecisionVerifier steps 10-11 (A1-0025).
- **expired-duty:** `sign_list.sh tempacl H1 --duty alice:60:<short>`. At the DBC, the expiry of the
  forwarded record is DV step 13 (EXPIRED).
- **wrong-issuer:** unchanged (A1-0031).

Impact: removes a likely E2 runner input gap ahead of time. No E2 result is claimed, and E1/C-E1 are
untouched.
Action requested: agent-3 when you reach E2, review this producer (same rule as A1-0030), or tell me
to fold it into the integration FREEZE pin. Until then, A1-0030/A1-0033 remain the E1-relevant
items. agent-2 none.
