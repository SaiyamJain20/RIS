# C-F1 context-bound signature checks

Execute the accepted C-F1 successor validation work: independently encode the
four witness message types; compare frozen digests/recoveries; reject altered
fields/domains, noncanonical signatures, unknown/duplicate/out-of-order signers,
wrong witness-set versions and incorrect certificate counts. Recover checkpoint
retry reports against the configured index, including pinned single refusals,
inconsistent reports and late arrivals. Tests use only synthetic frozen vectors.

Ruling: explicit caller-supplied chain/contract/set/count context, with fixed
normative domain names/version/type order; no context inferred from an untrusted
response. Context still requires anchored source reconstruction by a future
caller. These helpers are not wired into any E/F runner or execution gate.

Ruling: fetch failed SSH publickey before work. Cached owner branches are reviewed
by exact file-changing ancestry and manifests, explicitly without claiming live
remote state. Independent isolated work uses the already accepted local contract.
No owner code is executed or adopted; no source READY/execution ACK is inferred.

Ruling: use this confirmed checkout and self-review because the human forbids
worktrees and additional agents. The review is correlated. No dependency change.

1. Write expected-behavior tests and stubs; run and preserve RED.
2. Implement the helpers; run focused tests, fix actual errors without relaxing
   the accepted contract, then bracket inputs around the full evaluator suite.
3. Review code/controls/limitations, retain commands/exits/versions/source hashes,
   update owned handoff and prepare exact reviewed agent-3 checkpoint. Attempt
   normal publication; preserve local commits on authentication failure.

Stop condition: this tested isolated slice is reviewable and restartable. Anchored
B/getters/wiring, exporter history/orphan/WAL/native joins, fault oracle/model,
owner source READY and a separate complete ACKed execution freeze remain. All32
F cases NOT_RUN, F gate NOT_RUN, G locked; historical qualified E unchanged.

Progress: Task1 complete: RED131/exit1 (unimplemented stubs), retained red.txt.
Task2 focused complete: GREEN131/exit0, retained green.txt. Full suite1857PASS/exit0 in396.51s; audit-after verified195 unchanged inputs.
Task3 author review complete in REVIEW.md; exact-path checkpoint/publication
status and lock cleanup follow in automation memory/external run record. No accepted contract or dependency changed.
