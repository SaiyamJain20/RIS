# Correlated author review

Reviewed receipt_state_v2.py and independent raw ABI/EIP-712 fixtures against
accepted R6 sections3/5, KSSC grantDetails/GrantIssued and PSC getRequest/
_checkReceipt at the exact owner revisions in owner-provenance.json.

The checker composes signature/domain/membership/version, grant-id derivation,
allowed/existing grant, pending request and its destination/expiry, declared
GrantIssued fields and raw hash/height/time joins. Late receipts are intentionally
allowed. The extra recipient/issuedAt/log-field joins are evaluator consistency
checks, not an assertion that the current producer performs them. No complete
producer-validation or history acquisition claim is made. q2 is an explicit
fixture, and the one stored signature is never counted as a quorum.

Safe-interval conflicting headers refuse; fork/fault/clear history handling is
left to later composition. The nonce/nonceConsumed event fields are decoded but
not compared to a recovered AccessRequest. Log-range completeness, actual RPC
truth and signing-time observation authenticity remain unproved.

Inspected valid expired reconciliation, expiry equality, issuance-at-observation,
wrong/absent/duplicate event, wrong grant/request/recipient/time, capture/source
pins, independent signature/owner/domain/profile controls. Six narrow bypasses
preserve positive controls. Initial fixture, selector and harness failures and
helper revision are retained. This review is weaker than independent review;
no extra agent was launched. No actionable product defect found in this slice.

Fresh verification: 72 new/246 focused/2906 root PASS; root 650.91s/command 651.231s/exit0. Six deliberate bypasses detected with valid controls.
