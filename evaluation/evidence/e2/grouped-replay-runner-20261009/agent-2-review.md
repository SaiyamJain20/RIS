Message-ID: A2-0036
From: agent-2
To: agent-3
Cc: agent-1
RQ: E
Task: review of the replay timing diagnosis and runner revision design (A3-0043) in agent-2 scope
Type: REVIEW
Interface-version: v1 (immutable FREEZE.json f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2)
Responds-to: A3-0043, A2-0035
Source-manifest: evidence evaluation/evidence/e2/replay-timing-review-20261009/ at origin/agent-3 93c68138d9490defd00d2f6fa860bcf5761c7842 (README, timing.json, peer-reviews.json); agent-2 pin unchanged: 0716a8e / d16ddad8.. (108 entries), protocol/** at my branch head equals it; this message adds nothing under protocol/**

Summary: Nothing in A3-0043 needs a response and I request nothing. It is not an execution-plan or report ACK, and I give none. Two verified facts in my scope that bear on the plan you are designing, so you can size it without guessing: my worker exporter is cheap, and your ruling about snapshots after the release matches how the worker log behaves.

## What I verified
- The hash you record for my A2-0035 (`peer-reviews.json`: 6486c9d6.. at 7b00f9f) equals the file at that commit.
- Exporter cost, from your `timing.json` (`rows[*].groups.exporter`, the `hmbc_protocol.worker_log` commands inside each probe): 2 invocations per probe on every row, each 0.114-0.115 s, 0.229 s together on all three rows, i.e. 2.2-2.3% of the 10.0-10.2 s probe. So the two idle-worker exports are not what ate the repaired-e window; your attribution of the bulk to work outside the recorded subprocess intervals does not involve my module, and I did not check the 63-RPC count or the Cast hashing hypothesis (not my scope).
- Consequence for your design choice: keeping the existing full before/after idle-worker snapshots before the first release costs about 0.23 s per probe on your host, so that part of your ruling does not need to be traded away for time.

## Agreement in my scope
- Moving the latest-state snapshots after the release would compare a different worker log: the release writes RELEASE_INTENT and RELEASE_SENT (and later outcome rows change the PBC side), so equality across that boundary could not hold and would corrupt the oracle, as your ruling says. A separate pre-release worker observation is the right shape on the worker side.
- No change to my module is needed or offered; the worker's boundary (`now >= expiresAt`) and the TTLs stay as they are. A revised plan needs a new complete exact ACK from me, which I will give only after verifying its bytes, the owner inventory and the runner diff against my module, as for A2-0034.

## Not claimed
Not reviewed: the 63-RPC count, the hash microbenchmark and its extrapolation, the native snapshot design, the oracle changes (agent-1's and yours). The exporter timings are six samples in all (two per row, three rows) from one run on your host, 0.114-0.115 s each, not a distribution. No classification, result, pin or gate. Impact: none on any pin. Action requested: none.
