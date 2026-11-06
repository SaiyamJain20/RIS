# Correlated author review

Reviewed against accepted EXPORT-LAYOUTS revision9, published BOUNDARY and pinned
ledger source85c59f5 (manifest70f541cd..). No second agent was launched, per user
instructions. Author review has correlated blind spots.

- Composition retains real owner signature recovery, anchored context, orphan
  refusal, legal A->B->A/generation order, faults/clears and bit1/bit5 exclusions.
- Every declared last/signing/death/fault/clear block requires exact chain,
  number, hash and timestamp. Embedded source references carry no timestamp;
  they require number/hash only. Safe intervals reject conflicting height hashes.
- Numeric death facts equal decoded currentCheckpoint.sequence/governanceNonce.
  Grant death derives grant ID from requestDigest/KSSC/DBC and checks exists and
  request identity in grantDetails. Receipt death checks getRequest.status2 for
  the exact request. OUTCOME_RECORDED is ledger status, not delivery evidence.
- Pinned full ABI inventory and exact calldata/chain/contract/block keys prevent
  trusting exporter getter names or arbitrary normalized values. Strict codec
  refuses trailing/malformed results. Shared reads are deduplicated; duplicate,
  missing and unused captures refuse. All input objects remain unchanged.
- Seven deliberate in-memory check bypasses admit controls refused by real code;
  actual source remains unchanged. Positive faulted and cleared same-height forks
  remain labelled outside safe-ledger assumptions. Fake death facts are refused.

Retained first implementation run:62PASS/1FAIL because the test supplied a
malformed signature but expected ValueError rather than schema ValidationError.
Corrected fixture uses a canonical wrong-owner signature so it reaches recovery.
No production guard was weakened. Final68PASS. Initial63 missing-module failures
are genuine RED. Subsequent extra controls exercise already implemented behavior.

Ruling on boundaries: raw caller-supplied captures cannot authenticate RPC origin,
prove that a getter was actually called at its labelled block, or recover omitted
history. No live collector, source-state/sign-time semantic oracle, snapshot row
projection, arrival/timing or persistence is claimed. A future authorized capture
layer must bind actual RPC parameters and chain identities. These are outstanding
C-F1 work, not deferred defects hidden behind test totals. No gate closes here.
