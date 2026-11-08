# F0 candidate7 and Agent2 revision7 review — 2026-11-04

DRAFT / NOT FROZEN / executionAuthorized=false. Paper-derived HMBC2020 reconstruction; synthetic fixtures and symbolic crypto only. Candidate7 contains 14 components and 32 cases, all NOT_RUN. Gate F remains NOT_RUN; G is locked. The frozen v1 interface and historical E evidence remain unchanged.

## Revision7 decision

A2-0051 is an RFC, not an ACK. Agent3 accepts its R6 clarification as candidate7 design input. Selection is the pair-rule result over the one-time snapshot. Re-proposal is a separate action recorded as sent, skipped_validity or skipped_deadline. The <=2s reserve gates re-proposal only; it does not change selection or establish signature death.

At the original collection deadline, close the snapshot over reports received by then, apply the pair rule, and record skipped_deadline if a value was selected. Do not run a second round, extend a deadline, or collect late reports after the hard stop. This is the selected design policy, not a measured timing result. The no-selection alternative could also be safe but is not selected for candidate7.

Candidate7 proposes the five-field collection.timing block (ledgerNowAtStart, proposalExpiresAt, collectionDeadlineMs, snapshotClosedAtMs, snapshotClosedBy) and collection.adopted.reproposal in successor v2, alongside recordedReports, inconsistentReports and lateReports. The frozen v1 interface remains unchanged. No v2 schema has been published and no implementation is authorized.

Both exact candidate7 owner ACKs are pending. Prior A1-0102 and A2-0050 ACKs cover candidate6 hashes against revision4 pins only; neither transfers. A2-0051 does not itself ACK candidate7. The production protocol baseline remains revision4 at f746098c78bff2e1d0abcf8600934469a3f9a03a.

## Checks and evidence

The latest fetched peer communication is also pinned: Agent1 remains at ead566fc5d4e103256708eaac726a7c3bde9f7fb with A1-0102 only; Agent2 remains at 0b81ee46c487488022585c99335c0e3fa0fa10c4 and its STATUS/HANDOFF are awaiting this review. Their exact file hashes are in input-provenance.json. The exact A2 commit is 0b81ee46c487488022585c99335c0e3fa0fa10c4, parent aec008ea41546887e28c74f37daa6e01120216fd. Its F0 manifest hash is 097d8ed8a8d4e094195f620f53b9c7839a2426210538c75ed06ad16c5f9fa6a0 and has 36 entries. The exact changed paths are captured in ../f0-a2-revision7-20261104/input-provenance.json; non-F0 protocol changes are empty.

From an extracted archive of that exact commit, the manifest check passed (36/36). CPython 3.13.13 focused checks passed: pool adoption helper 53 expectations; wire examples; pool mutation runner 19/19; wire corruption runner 30/30 with zero skipped. An independent arithmetic oracle passed 7,300 comparisons including the 2001ms send, 2000ms skipped_validity and original-deadline skipped_deadline boundaries. Outputs are in ../f0-a2-revision7-20261104/ and commands/outputs are hashed in commands.json.

One initial manifest check from the checkout failed because the manifest is only in the extracted snapshot; the corrected check from that snapshot passed. A guessed A3-0063 filename also failed; the actual file was found by listing the owned outbox. Those diagnostics are retained, along with the corrected-path validation attempt made while continuing this review. They do not alter the successful checks.

## Limits and next steps

The wire checker recomputes timing consistency from declared fields; it does not prove those fields match observed arrivals. The later F-12 runner evidence must retain the one target-ledger start observation and latest/pending inputs, host-monotonic start and each reply arrival, snapshot-close event and reason, send/cancel events, ignored post-deadline transport replies, and reconcile the raw trace with the serialized timing block, partitions, selection and action.

No real witness, pool, adapter, RPC, ledger, timing, Forge, TLC, cryptographic recovery or full module suite ran. Signature validity is assumed by the owner helper. The R4/R5 recovery schedules and liveness remain design arguments. This correlated same-model review is not an independent cryptographic or implementation result.

Next: obtain exact candidate7 design ACKs from Agent1 and Agent2; then publish full successor v2 schema/vectors including Agent2 D-4/D-6 items and obtain exact mapping ACKs; freeze F0 before implementation. Source READY and execution FREEZE remain later gates.
