# C-E1 bootstrap/native executor checkpoint

Paper-derived HMBC2020 reconstruction; synthetic fixtures; E symbolic mode;
seed none. C-E1 remains WORKING. No integration FREEZE, service, actual transaction,
catalog execution or RQ gate occurred.

Fresh full evaluator:335 passed, exit0,49.86s pytest/50.05s captured subprocess;
source manifest equal before/after.70 new checks cover bootstrap bindings,
public transactions/views and the bootstrap execution sequence. All211 selected
owner blobs,15 frozen copies and35 original reviewed inputs verify.

Bootstrap RED37 fail→GREEN37 pass. Chain RED24 fail→GREEN24 pass; author review
then reproduced a missing equality between the mined receipt hash and the locally
signed hash (1 fail/24 pass), fixed it, and verified25 pass. Bootstrap execution
RED8 fail; test digest literals corrected from previously recorded owner-sample
evidence before implementation; corrected RED8 fail→GREEN8 pass. Failed tests
and the two exploratory Git lookup errors remain in verification.json/commands.json.
These are evaluator reconstruction results, not original-paper vulnerabilities.

The old-instance public producer sample is byte-identical to ledger9d6911d;
adapted deployment metadata and controlled replies exist only in tests. Tests
never start Anvil, the adapter or a worker. Bootstrap must be regenerated and
checked on the actual deployment. Signer custody remains Option A. A generic
failed/OOG transaction cannot establish the required UNAUTHORIZED_CALLER result;
the executor requires the exact mined public custom-error trace. That live RPC
capability is still unproved. Block/RPC consistency is not a light-client proof.

commands.json retains exact argv/cwd/times/exit/output hashes and external raw-log
paths; RED excerpts are bounded selected summaries, not full outputs. source-brackets.json
records full evaluator inputs; later documentation writes are publication metadata.
audit.json records owner blob commands/hashes, frozen/tool/package/fixture checks.
peer-communication files record file-changing provenance and unchanged post-test
branches. Only new peer revision is A2's E1-support-only STATUS atc99e2073;
it is neither a new source pin nor an integration ACK.

Author review only, weaker than independent review; extra agents/worktrees are
forbidden. Next: finish the complete public JSON-lines access runner and manifest,
publish concrete FREEZE and receive both exact owner ACKs before starting local
services and9 E1 controls. All56 catalog schedules and RQ gates NOT_RUN; E2/E3
wait for actual E1; F/G locked. Frozen interface/owner module bytes unchanged.
