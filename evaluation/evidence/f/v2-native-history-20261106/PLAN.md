# C-F1 raw observation and death joins

Continue the accepted F0 plan without changing a shared interface or consumer.
Internal API `verify_native_history(evidence, *, manifest, observations,
expected_owner, abi_paths, blocks, calls, compiled_max_admins=None)` composes
the declared signed-history checker with independently supplied raw RPC captures.

1. Write positive/refusal tests first and retain genuine missing-module RED.
2. Join every last/signing/death/fault/clear observation to raw block number,
   hash and timestamp on its pinned chain. Join embedded source-block references
   by number/hash too. Fault/clear labels and revision9 ordering remain intact.
3. Decode numeric deaths, grant existence and OUTCOME_RECORDED through exact
   caller-pinned owner ABIs at the death block hash. Match full calldata,
   contract, chain and block; reject missing, duplicate and unused captures.
4. Preserve bit1/bit5 exclusions; do not promote mutant deaths to safe evidence.
5. Review independently of implementation, exercise deliberate bypasses, run
   focused/root tests with all execution sources frozen, publish owned paths.

Ruling: raw captures are supplied, not collected by this pure checker. Records
are internal containers: blocks `{chainId, raw}`; calls
`{chainId, blockHash, to, data, result}`. A future authorized collector must
retain actual RPC parameters/provenance and bracket chain identity. Supplied
bytes cannot authenticate a chain, prove effect/source-state truth, sign-time
validity, arrival completeness, store/export completeness or persistence.
Expiry uses the matched block timestamp; other death facts use owner public
getters and reviewed source semantics. Hash-addressed calls distinguish forked
blocks in explicitly faulted intervals; no canonicality is inferred.

Ruling: use the confirmed checkout, inline execution and correlated author
review under the user's no-extra-agents/no-worktrees restrictions. Normal owned
agent-3 publication is already authorized. No integrated services or gate change.
