# A3-0162 offline baseline executor

Continue Agent 3 / C-F1 from A3-0161, parent 0aac1cc0. Scope: evaluation code,
synthetic tests, this evidence receipt and Agent-3/shared coordination records.
No owner package execution, services or integrated cases in this implementation run.

1. Write failing synthetic-command tests for exact recipe/source/runtime/tool
   pins, lexical venv interpreter paths, ordered commands, separate byte logs,
   expected exit/output, source mutation, timeout and owned descendant cleanup.
2. Implement a low-level baseline recipe executor. Require an exact recipe hash;
   validate the complete selected source-root inventory before/after each command.
   Use explicit environments, absolute tool paths and owned process groups.
3. Build inspectable recipes for ledger suite/mutants, protocol pytest and five
   TLC controls. Test recipe contents only; do not execute owner packages.
4. Run focused compatibility checks, self-review, retain commands/exits/tool and
   source hashes, update live continuation records and publish exact owned paths.

Ruling: this is an internal executor and recipe builder, not a FREEZE/ACK parser
or a new service entry point. It cannot authorize integrated execution. Future
stage-3 orchestration must verify the exact execution FREEZE/role ACKs first.
The reviewed report, packet, DRAFT plan and frozen interfaces remain byte-identical.
Existing record_command merges streams and assumes synchronous children; retain
it unchanged for E and implement separate stream/descendant handling here.
No delegation/worktrees: explicit project instructions take precedence over skill
defaults. Self-review is correlated, not a second independent reviewer.
