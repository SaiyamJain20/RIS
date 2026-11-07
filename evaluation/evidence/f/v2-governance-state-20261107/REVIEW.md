# Correlated author review: governance supplied-state checker

Classification: tested paper-derived extension and deliberate evaluator mutations.
Consent allow-lists are an explicit reconstruction choice, not an HMBC defect.
No new paper finding is claimed. Review is by the same author because the user
forbids additional agents. No independent peer review is implied.

Compared accepted R6 sections 3/4 and the frozen boundary to the implementation;
exact spec/owner source SHA256s and file-changing commits are in
owner-provenance.json. No protocol/ledger implementation is imported/executed.
The complete four-type source-state story is still unfinished.

| Duty | Implemented/checked | Scope remaining |
| --- | --- | --- |
| Signature and destination | Existing bound-signature checker reconstructs B, caller-selected owner/version/domain; q2 control stays q2 | One signature, no threshold certificate |
| Governance structure | Exact published GovernanceAction validator, sorted nonzero bounded admins, ADD/REMOVE/SET, empty SET and eight-admin positives | No claim about raw transaction calldata |
| Nonce | Exact current+1 including first/max successor and saturated-current refusal | Supplied raw getter, no actual historical signing-time proof |
| Current membership | Governance witnessSetVersion and TMSC root membership; ADD also reads tombstone | No later transition/execution proof |
| Approval | Every closed canonical tuple validated; exact action/root/admins match; unrelated valid entries and duplicates allowed | Caller-pinned TEST-ONLY fixture, not authenticated witness configuration/policy |
| Expiry | Exact supplied PBC timestamp < expiry <= timestamp + public maxGovernanceTtl | No latest-head/contemporaneity or actual sign-time guarantee |
| Capture identity | Exact PBC/hash/callee/calldata, canonical ABI re-encoding, duplicate/missing/extra/unused captures refuse | RPC/ledger authenticity and acquisition remain unproved |

Seven deliberate in-memory bypasses individually remove nonce, current witness
version, ADD existence, ADD tombstone, REMOVE/SET existence, approval match and
expiry checks. Each original refuses its invalid fixture; the matching mutant
accepts it while a legitimate ADD still succeeds. This is narrow sensitivity,
not exhaustive branch coverage or proof of all source-state duties.

Review added a valid eight-admin/list-search control and an expiry-renewal/time
control. The latter deliberately shows two caller-supplied time observations
can satisfy the checker without establishing actual signing time. Initial69 RED
and69 GREEN precede these two additions; final bracket covers71 tests. Initial
trials had command receipts but no complete source bracket. Claims below must
use final frozen runtime inputs only. The mutation helper had an unexecuted
syntax typo corrected before input freeze; no product code changed after GREEN.

A missing READY/ACK stays missing. A1/A2 unchanged; A3-0096/0097 remain open for
corrupt-config chainId overflow/schema startup refusals. No local owner rerun or
new E parity is claimed. Complete runtime/mapping and separate exact execution
FREEZE ACKs precede services. G locked; all32 F cases and Gate F NOT_RUN.

Remaining: governance history/digest coverage and exact RPC acquisition with
explicit unsigned observation/approval provenance; AccessDecision/GrantReceipt
state joins; producer schema/path/lock completeness; independent fault oracle
and finite TLC model. No native death/RPC truth/store completeness/durability,
consensus, timing/performance or gate result follows from this slice.

Final fresh71 new/315focused/2721root tests PASS. Seven narrow controls pass.
All899owner/256local/5helper/8497carried inputs stable;52F0pins/31payloads match.
392communication paths/no divergence; owner tips unchanged. Verification SHA256 ea45af3dbf110cca0d8cac0ff6212bfae8cac9abe5f4bb6b62f12e4e523170e8.
Ten predecessor receipts plus own11th independently checked. No unresolved
product-code finding found in this correlated review; remaining scope above
is not implemented or proved. Runtime bracket precedes explanatory/shared edits.
