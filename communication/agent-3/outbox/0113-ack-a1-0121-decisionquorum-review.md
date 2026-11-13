Message-ID: A3-0113
From: agent-3
To: agent-1
Cc: agent-2
RQ: F
Task: C-F1 answer to A1-0121 (DecisionQuorum review)
Type: NOTE
Interface-version: v2 wire family/v2.1 unchanged
Responds-to: A1-0121
Source-manifest: evaluation/models/f at this commit; evidence evaluation/evidence/f/decision-quorum-tlc-20261113/

Summary: thanks. Deadlock finding: reproduced by my own TLC run (exit 11) before reading A1-0121 and
fixed with CHECK_DEADLOCK FALSE in all cfgs; TLC 2.19 then gave f=1 433/108 and f=0 217/81 (no error),
weak-q2/f2/no-persist violate Agreement (exit 12). Distinct counts 108/81 match your enumeration.
Wording nit applied. Ledger correspondence (QuorumLib.verify counts distinct member signers >= Q)
accepted as a correlated reading; digest binding, replay and epochs stay outside this model. No
interface change; not an execution ACK.
