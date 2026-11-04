# Correlated author review

User instructions prohibit extra agents and peer edits; no independent reviewer
was launched. Reviewed the complete owned source/tests and exact owner ABI copies
against the accepted BOUNDARY, existing RpcClient/AbiContract, and prior context
checker. This is correlated author review, not an owner or external ACK.

Findings and disposition:

- Initial direct result write could leave a partial published file after OSError.
  Added a controlled interrupted-write case before fixing: 1 FAIL/52 PASS. Root
  cause was writing the final path before all bytes were written. Changed only
  that publication to pending-file plus rename; 53 PASS. This is process-level
  output hygiene, not power-loss durability; no fsync claim.
- Added real RpcClient subprocess coverage with a hash-pinned synthetic CLI:
  54 PASS. Actual RPC argument encoding, checkpoint-policy tool hashes, subprocess
  output parsing and every raw command-log digest run without a server. Neither
  the command nor its dataset is claimed to be Cast or a running ledger.
- E v2.1 explicit selection and the same address on distinct chains both pass.
  No global address uniqueness assumption. Real owner-exported function signatures
  are consumed, including indexed ksscForChain(uint256) and witness arrays.
- ABI inventory/pins are checked before RPC, then all ABI bytes and the caller's
  manifest are checked again before publication. Snapshot metadata prevents a
  transport callback from altering the in-flight reference configuration.
- All code/getter calls use explicit historical block numbers. After BOTH chains
  are read, both chain/genesis/deployment/anchor identities are checked again.
  Transient drift restored between boundaries remains undetectable. A malicious
  consistent RPC is outside this safe-ledger/tool trust boundary.
- Raw call failures and invalid return bytes retain a failed transcript without
  a result. A finite aggregate deadline surrounds each call; the existing real
  RpcClient also limits subprocess time. An arbitrary blocking injected transport
  cannot be preempted. This is documented, not described as a measured S0 bound.
- Six in-memory removals independently demonstrate sensitivity to genesis,
  deployment, final chain identity, ABI drift, manifest drift and the deadline.
  Existing code/getter reconstruction and signature checks remain unchanged.
- The first full-suite attempt correctly refused source drift when this author
  added two evidence Python scripts during execution. Its failed manifest and
  interrupted run (1 FAIL/896 PASS/exit2) are retained. The source selector was
  traced, all discovered scripts completed, and a complete153-entry execution
  inventory captured in addition to the236 selected test inputs before the
  fresh full rerun. No source-stability check was weakened or product bug
  invented to explain the scheduling mistake.
- A2-0062's differential uses Agent3's _expected_views to construct synthetic
  values. Its alternative reconstruction path is useful cross-implementation
  evidence but is not an independent expected-value oracle, author or live chain.
  Only its immutable source/output hashes are verified here; it is not rerun.
- A1-0116 is ledger code reading. Read Governance at exact 85c59f5 and the partial
  witness implementation at 051cf67: constructor chain ID/TTL, typed domain and
  witness TTL enforcement support the stated separation. No new runtime safety
  proof is inferred. Keep D50's frozen S0 unchanged and collect both getters in
  the evaluator as BOUNDARY already requires. No new ACK/source READY/execution
  authority follows from either note.

No remaining known blocker to this isolated collector checkpoint. Signing-context
wiring, exporter history/orphan/WAL/native completeness, fault oracle, finite model
and integrated checks remain unfinished C-F1 work. Gate F stays NOT_RUN; G locked.
