# Declared GrantReceipt history state coverage

Goal: the next internal C-F1 slice under accepted R6 sections 3/5 and the frozen
revision-9 history layout. Paper-derived HMBC2020 extension; synthetic inputs.

Approach: compose verify_signed_history with verify_receipt_signature for every
declared live/superseded receipt digest. Select PBC observation from the signed
record, DBC observation from a closed caller capture. Require exact digest
coverage and agreement of repeated headers, state calls and grant-event bytes.
Alternative normalized exporter assertions omit the independent raw ABI join;
RPC acquisition and death/transition proofs remain separate work.

Files: evaluation/receipt_history_v2.py, its synthetic pytest controls, this
evidence directory, evaluator README and Agent 3/shared live documentation only.
No dependency, wire, interface, peer-module or existing-consumer changes.

- [ ] Write tests and retain expected missing-module RED before product code.
- [ ] Implement the pure composition; retain GREEN and deliberate bypass controls.
- [ ] Run focused and root regressions with owner/local/carried source brackets,
      exact peer communication provenance, tools/commands/exits/fixture hashes.
- [ ] Review diff in a separate author pass, publish exact owned paths on agent-3,
      verify remote, release both original persistent locks, update memory.

Review focus: omitted superseded receipts, wrong observation selection, shared
event nonce contradictions, cross-capture same-height forks, empty subsets and
fault/clear/bit1/bit5 exclusions. A receipt has no expiry refinement. Checking
superseded supplied states does not prove a possible safe-ledger transition or
executed-receipt death. One-owner signatures are not quorum evidence, even q=3.
No RPC authenticity, ancestry/latest-head/sign-time, log-range or export/store
completeness, native deaths, producer misconduct, persistence, delivery, consensus,
TLC/E parity/F scenario/gate inferred. G locked; integrated execution locked.

Ruling: keep review in this chat because explicit project instructions prohibit
extra agents; review is correlated. Existing F0 acceptance and the user's
continuation request authorize routine internal implementation; no new approval
or worktree is needed. Cost if wrong: this isolated evaluator does not close F.

Startup: initial exclusive-create attempt found the existing persistent lock;
no inode was replaced. PID absence did not establish lock ownership. Memory and
skills were read before the correct kernel flock succeeded. Repository reads,
fetches and edits followed acquisition. Future first action must be flock itself.
