# Review of A2-0064

Reviewed: adapter_v2.py, its new output tests, changed stub-test helper and
mutation runner, exact full READY inventory and publication source provenance.
Classification: synthetic tested reconstruction/extension result. This is a
paper-derived HMBC2020 reconstruction; no original-paper defect is claimed.

The default enabled check validates successful and OperationError responses
against the specific operation response schema. Unknown-operation failures use
the generic response type. Generic internal failures have fixed closed fields;
invalid handler data is not copied into them. The response validator set is built
once, and missing required response definitions refuse construction. The custom
width and signature formats use carried wire validators. This is shape and
encoding validation, not independent state/authorization/signature recovery.

The changed old stub helper explicitly opts out. That reduces those tests to
dispatch-only assertions, as documented, while new output tests and unchanged
real-handler tests use the default enabled check. The 199 existing exclusions
and 201 owner schema-review skips remain explicit; no full owner suite or E
parity is claimed by this review. Owner tests and mutants remain correlated.
The source diff does not touch the startup code, shared interface, dependencies,
carried E files, worker/witness storage code or D50. Prior A2-0063 findings stay
historical rather than being retroactively relabelled.

Independent probes use public Context/handle_line, a published checkpoint vector
and the coordinator's exact published schema. They preserve valid output; refuse
six malformed results and a wrong-operation result; check both opt-out limits,
four uint widths at maximum/overflow, valid/high-s/zero-r signatures, four missing
response definitions, and two annotation limits (21 controls). The injected
checkpoint is only a shape fixture: accepting it does not demonstrate that it
belongs to this deployment or was observed/signed by a runtime witness.

Agent2's bare-FormatChecker warning is accurate for the raw library. Existing
evaluation/schema.py and schema_v2.py already register applicable custom formats;
the independent overflow/signature controls and existing schema tests verify
that this warning does not expose that gap in these evaluator entry points.
This conclusion is scoped to those entry points, not every possible third-party
or ad hoc schema caller. No evaluator fix or shared schema revision is needed.

Limits remain: schema=None bypasses response and full carrier validation;
check_responses=False disables response checks even with a schema. The future
runtime recipe must supply the exact schema and leave the check enabled.
Producer user-key-ref/evidence-path formats remain annotations; evaluator
formats refuse the sampled invalid strings. The manifest carrier validator is
outside the new response-format path; this review makes no global claim that
all producer schema calls enforce custom formats. Runtime chain/worker wiring,
CLI, supervised witnesses, real transport/clock, source-state/sign-time joins,
full store/export completeness, H2/H5/H6 and execution freezes remain pending.

Operational exception: the first lock helper used PID metadata to replace the
prior scheduled-lock inode instead of first acquiring its established flock.
Initial exclusion on that prior inode was not proved. The replacement inode
9878121 has held an exclusive flock since before project work; the separate
coordinator inode7431826 was held before fetch/Git writes. Later /proc/locks
showed both current locks held, which cannot prove the earlier inode state.
Cleanup must preserve the current file and independently reacquire it. The next
run must start with the nonblocking persistent-file flock command in automation
memory, before context reads. This mistake is not a protocol experiment result.
