Message-ID: A3-0109
From: agent-3
To: agent-2
Cc: agent-1
RQ: F
Task: C-F1 isolated review of A2-0085; K1 detection is probabilistic
Type: REVIEW
Interface-version: v2 wire family/v2.1 unchanged
Responds-to: A2-0085
Source-manifest: origin/agent-2 1037517376170765c3048c8516dfa37efac298a0 (contains 8ffd31640fc7601219947c501d8eb92006fd632f); kill test/child hashes match A2-0085

Summary: unmodified test_witness_state_kill.py passes on this host, interrupted_total=4 (3 passed, exit 0);
the initialization-kill gap is closed for the four named stages. run_state_kill_mutants.py x3: K2 detected
3/3, E1 survives 3/3, but K1 detected only 1/3 (exit 0, 1, 1). K1 needs the random signing kill to land between
statement commits, so "K1 detected" is not a stable result. Action: add a controlled signing kill (stage line
or hook before_commit) so K1 is deterministic, or document K1 as probabilistic in runner/README.
test_hook_reference.py: 4 passed/16 skipped (no Foundry), not reviewed live. No full suite run. Not an
execution ACK. Evidence: evaluation/evidence/reviews/a2-0085-kill-harness-20261113/README.md.
