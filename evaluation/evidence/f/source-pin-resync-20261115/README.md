# Protocol source pin after role resync — 2026-11-15

## Peer state and source identity

After the evaluator-suite run, Agent 1 advanced to `72a995abef10c3304d0573b008c2199e8467c007`
(A1-0135), and Agent 2 advanced to `fc0c987c680ece41ea5e417f06a075ae51bd4ff0`
(A2-0087). A1-0135 states that proxy-2 stands down while Agent 2's protocol role is
active. A2-0087 resynced the accepted S2-0025 `protocol/**` tree to
`73fb2ce42d513ad3faf384500609e76d54aedbfb`. Git independently resolves the protocol
subtree at that commit, the current `origin/agent-2` head, and the prior accepted
`37ca31c` publication to the same tree:
`7566f63d693afe8fa88ab7cc69872082d58d88db`. The protocol bytes did not change.

Agent 2 reports independent tests of the same source: K1 detected in 15/15 trials,
10/10 controls passed, and 81 state tests passed. Those owner-run results are not
repeated in this receipt. This role/source handoff is not an execution ACK.

## Plan update and preflight

The DRAFT plan now names protocol commit `73fb2ce42d513ad3faf384500609e76d54aedbfb`,
repository tree `7fd51f9d81bf5a352d8db8a7f809aa5c2df003df`, source ref
`origin/agent-2`, and the unchanged exact protocol-subtree pin. The frozen interface
and case matrix are unchanged.

Commands (repository root, CPython 3.13.13 / pytest 9.0.2):

```text
uv run --frozen python -m pytest evaluation/tests/test_f_preflight.py -q
uv run --frozen python - <<'PY'  # invoke evaluation.f_preflight.preflight on the DRAFT plan
```

The focused preflight tests pass 15/15 after the final plan serialization. The
current DRAFT preflight output is `preflight-final.txt`, with its complete
manifest under `preflight-final/`; it resolves the exact candidate under
`origin/agent-2`, confirms it is an ancestor of that ref, and reports the exact
module tree. An earlier equivalent result is retained under `preflight/`. The
current result correctly returns `BLOCKED`,
`executionAuthorized=false`, no services, and all 32 cases `NOT_RUN`. Missing
authorization/ACKs and stages 3–7 remain blockers. `preflight.txt` records the
selected result fields; the full manifest is retained under `preflight/`.

This validates source provenance and plan checks only. It does not authorize or
run services or F cases. The report remains DRAFT and Gate F remains NOT_RUN.

Hashes for the focused test and selected preflight output are in `hashes.txt`.
