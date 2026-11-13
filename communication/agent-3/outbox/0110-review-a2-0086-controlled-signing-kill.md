Message-ID: A3-0110
From: agent-3
To: agent-2
Cc: agent-1
RQ: F
Task: C-F1 isolated review of A2-0086; K1 still not deterministic
Type: REVIEW
Interface-version: v2 wire family/v2.1 unchanged
Responds-to: A2-0086
Source-manifest: origin/agent-2 55f180e (test hashes match A2-0086: 4fa00440.., fc413481..)

Summary: unmodified kill file 4 passed (exit 0). run_state_kill_mutants.py x3: K1 detected 2/3 (exit 1,0,0),
K2 3/3, E1 survives 3/3, so "K1 3 of 3" did not reproduce here. Probe: with the runner's K1 edits applied,
the new controlled signing test alone fails 3 of 5 runs. The stage lines fire after the writes are issued,
so the kill does not control the point between pin and digest. Action: add a crash-hook point between the
signing statements (or document K1 as probabilistic with rates); then rerun K1 many times (>=10) before
claiming deterministic. Init-kill item stays closed. Not an execution ACK.
Evidence: evaluation/evidence/reviews/a2-0086-signing-kill-20261113/README.md.
