# C-F1: A2-0070 source review and isolated sequence boundary

Pin A2 partial publication b0184e7cca2be4328ccd1ce10e99b3c87eacff28 and
A1 READY source 85c59f588de58a8ff5e87b9fe6f630c9d8c43642. Review exact
communication revisions, six changed paths, full snapshots and frozen inputs.
No owner module will be edited, including in the extracted snapshots.

Expected behavior, written before the new checks:

1. KSSC accepts first sequence 5 and then 7 with three valid signatures;
   lower/equal sequences refuse. Two signatures refuse without changing state.
2. KSSC accepts uint64 maximum with three signatures. Thereafter every
   representable sequence is <= current; no later checkpoint can pass that
   predicate. Exercise representative values and seeded fuzz inputs in a local
   Forge EVM, without RPC nodes or services. This is a deliberate quorum-key
   compromise outside f=1, already anticipated by frozen SIGNING-RULES section 3.
3. Honest witness services refuse sequence skips without recording them;
   the proposer follows current+1 after ordinary skips but cannot encode max+1.
   Retain a real-signature successful witness control and unchanged store checks.
4. Review A2's thirteen-case live table as owner evidence only; do not rerun or
   adopt its 62-test live result. Static source can corroborate predicates but
   cannot establish every reported execution result.
5. Recheck source/helper/local inputs and final peer revisions. Publish one
   scoped REVIEW and restartable shared documentation on agent-3.

Use verification-before-completion and verify-and-stop. Task observer remains
active. No additional agents: the user explicitly forbids them, overriding the
review skill's delegation workflow. Review is correlated author review.

No live services, dependency/interface/default changes, peer edits, main push,
new E parity, TLC, timing, integrated F case or gate claim. C-F1 stays WORKING;
32 F cases and gate F stay NOT_RUN; G remains locked. This review is an isolated
tested reconstruction result/deliberate compromise, never a paper vulnerability.
