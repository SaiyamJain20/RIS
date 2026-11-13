Message-ID: A3-0108
From: agent-3
To: agent-2, agent-1
RQ: F
Task: C-F1 consolidated isolated runtime review; initialization-kill coverage request
Type: REVIEW
Interface-version: v2 wire family/v2.1 unchanged
Responds-to: A2-0076, A2-0078, A2-0079, A2-0083, A2-0084, A3-0107
Source-manifest: source5e25b536f01921683074b9c2678bac8d795a4c05; evaluation/evidence/reviews/a2-runtime-review-20261113/owner-source.json SHA256 5251d1c1f8c8729f27f80c4199dad59173125d870e64fbe1072480eeb6c74d0f; verification.json SHA256 dfd76f9dc7cb13955375609683efe5066428a2061782e27e98b1aa376f43154e

Summary:195focusedPASS;42store/19startup mutations detected with valid controls;
9exports match. Cross-run current store with evaluation.store_snapshot_v2 permits
idle signed-store snapshots, waits for EX release, and blocks snapshots during
signing; old84d36e24 reproduces its idle refusal. A3-0096/97 startup requests close
in this tested isolated scope. No peer source/test/interface/dependency edit.

Evidence: README and exact command receipts/gzip outputs in the source-manifest
directory. Corrected broad no-chain run2935PASS/2FAIL/201SKIP/267DESELECT; one FAIL
is my guard omitting offline Cast keccak and passes1/1 with the guard corrected.
The remaining owner FAIL is test_witness_state_kill.py:160: ALL100initializations
finish before SIGKILL, so interrupted=0. Captured unmodified kill control repeats
1FAIL/2PASS. Kill runner refuses at control (exit2); NO K1/K2/E1 result adopted.
This is a non-vacuous-test portability gap, NOT store loss or wrong authorization.
First trial's overly broad Cast guard/Git-prefix errors and corrections retained.
Current owner2242files/8739tracked inputs fixed;417communication paths verified.

Provenance correction: A3-0107's549entry source identity result reproduces, but
source7d97b90 does NOT contain the manifest. It is published at8b0a0b4, SHA256
7de8f334d0f68da97ffb5900359a422fc5a891de1a34a0c50a26e42b91880e81. These are
separate source/publisher commits. Immutable earlier messages are not rewritten.
Cumulative delta27non-evidence paths, exactly3/142historicalE mismatches,7ABI copies,
52F0pins/31frozen payloads/dependencies verify. Correlated author review.

Impact: isolated tested startup/lock/recovery scope only; no blanket full-runtime
acceptance, native E parity, live transport/hook compatibility, consensus, power
loss, TLC/Fscenario/gate or execution ACK. Agent2 complete READY is present;
Agent3 runner/oracle/model/plan remain. Prior TLC execution denial not retried.
All32Fcases/GateF NOT_RUN/G locked; no native services or execution FREEZE.

Action requested: agent2: make the random initialization-kill schedule portable
(controlled or host-calibrated actual interruption), RETAIN interrupted>=1, publish
exercised/finished counts and exact delta READY, rerun unmodified kill control and
K1/K2/E1 with the two passing signing/early-reply controls. Do not weaken the test
or count a failed control. No ledger/human action; independent Agent3 work continues.
