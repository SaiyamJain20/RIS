# Correlated author review: retrospective governance RPC acquisition

Tested paper-derived HMBC2020 extension with synthetic transports and real
signature/schema/ABI verification. Caller approval is a reconstruction fixture,
not discovered producer intent or an HMBC vulnerability. No extra agents were
started; this is same-author review and offers no independent reviewer assurance.

Compared accepted R6 sections 1-4, exact owner Governance/TMSC source and the
existing frozen context/history/state boundaries. owner-provenance.json records
file-changing commits and SHA256; all 899 owner source blobs are freshly compared
to the same exact fetched tips by preflight/postflight. No owner runtime executes.

- Full signed history/context is checked first, including other signed types when
  the governance subset is empty. Observations come only from each stored digest.
- Every live/superseded/refined governance digest gets one exact closed capture.
  Shared getters/headers deduplicate by exact hash/contract/calldata. Conflicting
  number/timestamp plans refuse before I/O. ADD alone reads the tombstone getter;
  REMOVE/SET preserve the authority-existence and canonical typed field checks.
- Two independent caller-selected endpoint identities are checked before and
  after all state/header reads. All exact selected headers are checked again
  after getters; safe intervals also check numeric canonicality and EIP-1898
  requireCanonical=true. Fault/clear intervals preserve competing hashes without
  asserting safe canonicality. There is no latest/numeric eth_call fallback.
- ABI identity/paths, caller inputs and RPC object/origin inventory are bracketed;
  mutable transport arguments cannot rewrite retained RPC parameters. Partial
  RPC refusals/budget/deadline failures retain status and no completed result.
  Existing output directories refuse rather than overwrite prior evidence.
- The final governance history checker independently consumes assembled raw state
  and separate TEST-ONLY approvals. Approval hash/reason/basis are recorded in the
  transcript. Observations remain unsigned exporter claims; signature binding of
  observation, actual signing time, latest head and approval policy remain false.
- A-B-A recurrence/refinements, ADD/REMOVE/SET, q2, empty subset, fault and clear,
  and bit1/bit5 death exclusions have positive controls. Empty SET/eight-admin
  and canonical field edge cases are covered by the focused governance-state suite.
- Six narrow in-memory bypass/valid pairs exercise the state/history composition,
  chain-ID equality, final identity checks, header reread, approval input drift
  and canonical equality. They are sensitivity demonstrations, not exhaustive
  mutation/branch coverage or actual producer faults.

No unresolved product-code issue found in this correlated review. Synthetic
transports cannot establish actual node support, RPC truth, chain ancestry,
producer-rule violation, approval policy, sign-time/latest-head, complete stores,
native deaths, persistence, quorum/consensus or gate completion. A blocking
injected transport cannot be preempted by the cooperative deadline; RpcClient's
per-call timeout is a separate control. File endpoint equality cannot prove no
transient change-and-restore. The collector intentionally does not switch consumers.

71 exact missing-module RED reasons were verified before implementation; initial
RED/GREEN and mutant trial precede the complete bracket. Product/test bytes are
unchanged since the first GREEN; final focused/mutant/root checks are bracketed.
The mutation helper's unused unreachable branch was removed before preflight;
no runtime/product source changed as a result. No helper stability claim before
preflight. Explanatory/shared documentation follows the final input bracket.

Complete runtime READY/mapping and exact separate execution FREEZE ACKs remain
required; A3-0096/97 stay open. Remaining AccessDecision/GrantReceipt source-state
and producer/schema/path/lock completeness, fault oracle and finite model remain.
Historical qualified E unchanged; all 32 F cases/Gate F NOT_RUN, G locked.

Final fresh results: 71 new / 449 focused / 2834 root tests PASS; six bypass/valid
pairs PASS. All recorded direct-child process receipts are STOPPED. The final
bracket verifies 899 owner / 260 local / 5 helpers / 8577 carried inputs and
52 F0 pins / 31 frozen payloads. 394 communication paths have no divergence;
peer tips/revisions are unchanged. No product edit after the first GREEN.
An initial evidence-assembly assertion mistakenly required capturedAt equality;
only that timestamp differed. Corrected branch/file comparison passes and the
failure is retained in assembly-note.json. Product/runtime inputs were unchanged. The verifier correction after postflight
is retained with original source and hashes in helper-correction.json.
