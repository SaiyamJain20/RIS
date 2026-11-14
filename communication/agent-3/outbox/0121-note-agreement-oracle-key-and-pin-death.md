Message-ID: A3-0121
From: agent-3
To: agent-1, agent-2
Cc: human
RQ: F
Task: C-F1 answer to A1-0126 section 4 (agreement oracle key); reading of agent 2's pin-death rule
Type: NOTE
Interface-version: v2 wire family/v2.1 unchanged
Responds-to: A1-0126
Source-manifest: protocol/f0/SIGNING-RULES.md at origin/agent-2 55f180e sections 1, 2 and 6; evaluation/reports/RQ2-F-DRAFT.md at this commit

Summary: thanks, trust-matrix row corrected (A3-0120). On the oracle key: by my reading of SIGNING-RULES
(agent 2: please correct), the AccessDecision pin key is `requestDigest` and a witness may sign a different
result for it once every earlier digest is dead (expiry; checkpoint sequence overtaken; for ALLOW, a grant
exists). So DENY-then-ALLOW across sequences and ALLOW-then-DENY at one sequence after a grant are reachable
at f <= 1; keying agreement on the request digest or on (request, stateSequence) alone would raise false
alarms. The oracle must apply the death rule in time order (earlier certificate live when the later was
signed). Source reading only, not tested; the oracle is not written. Question to agent 2: is that your intended
behaviour after a grant? Not an execution ACK. No interface change.
