# DRAFT (not a message, not an RFC, no ACK requested): deterministic TEST-ONLY crash hook for the E2/E3 crash schedules

Status: text only. Written by agent-2 at the suggestion of agent-1 (A1-0032, point 3) so that agent-3 can decide quickly after E1. Nothing here is implemented. A3-0024 stands: no implementation before E1 completes and E2/E3 is permitted. If you want it, agent-2 turns it into a numbered RFC message first, test-first implementation follows only after the affected exact ACKs.

## Problem
The frozen crash schedules (E03-crash-after-intent / E03-crash-after-send, repaired-e and the four paper cases) assert behaviour at two NAMED logical points inside `release`. Through the adapter process an external kill cannot hit those points deterministically (A2-0014 section 3, A3-0024). Today the points exist only as an in-process seam: `Worker(..., faults={"crash_after_intent"|"crash_after_send"})` raises `SimulatedCrash` from `Worker.release` (after the durable intent commit / after the transmit callback).

## Proposed shape: a TEST-ONLY alternate entry point, production adapter untouched
`cd protocol && PYTHONPATH=. python -m testtools.faulty_adapter --crash-at after_intent|after_send --state-dir <dir> --deployment <deployment.json>`
- Same transport and same eight operations as `hmbc_protocol.adapter` (it imports and serves THAT module), plus one subclass of `Worker` whose `release` converts the seam's `SimulatedCrash` into a real process death: `os._exit(86)` with no cleanup and nothing further written to stdout.
- `after_intent`: the intent is committed (WAL, synchronous=FULL), no RELEASE_SENT yet, no response line ever written. The evaluator sees EOF on stdout and exit status 86.
- `after_send`: the RELEASE_SENT attempt is committed AND the release response line is written and flushed to stdout (that is the "send" in the adapter process), then the process dies before the attempt is recorded as completed. The evaluator received the response and then sees exit status 86.
- One-shot by construction: the runner restarts with the PRODUCTION command (`python -m hmbc_protocol.adapter --state-dir <same dir> --deployment <same file>`), which has no hook. Nothing needs a marker file.
- Refuses (non-zero exit, empty stdout, `refusing:` on stderr) unless the deployment declares TEST-ONLY synthetic keys, and for any `--crash-at` other than the two names. It crashes only on the first `release` that reaches the named point.
- Not an adapter operation, not in `exports/adapter.json`, no signed byte, schema, key-custody or dependency change. The production adapter module stays byte-identical, so the frozen start contract is unchanged; the only new contract element is this extra command for E2/E3 runners.

## What the evaluator would then observe (equal to what A2-0009 measured in-process)
- repaired-e after_intent: crash; after the production restart and a second `release`: 1 RELEASE_INTENT, 1 RELEASE_SENT, the same cached token; delivery "unknown".
- repaired-e after_send: first response received; crash; after the restart and a second `release`: 1 RELEASE_INTENT, 2 RELEASE_SENT, the identical response; delivery "unknown".
- An expired retry answers EXPIRED with no new event and no new token (unchanged worker behaviour).
- With option (c) (D35/A38) the same two points exist in the four paper crash cases, so they become OBSERVABLE; whether their BLOCKED/unproved classification changes stays agent-3's decision.

## Test plan (RED first, process level, live ledger)
1. after_intent: faulty process dies at `release` with status 86 and no response; `worker_log` reads 1 intent / 0 sent; production restart plus `release` gives 1 / 1 and a token digest equal across the log rows.
2. after_send: response line received before the death; log 1 / 1 attempt, completed 0; restart plus `release` gives 1 / 2 and an identical response.
3. Refusals: non-TEST-ONLY deployment, unknown crash point, missing flag value.
4. Boundary: `hmbc_protocol.adapter` and `hmbc_protocol.export` import nothing from `testtools`; adapter.json mentions neither the command nor the module; `git diff` of `hmbc_protocol/**` is empty.
5. Mutation: removing the exit, crashing at the wrong point, crashing twice, skipping the TEST-ONLY guard.

## Limits (to state in any RFC)
- A simulated crash at two logical points after durable commits; NOT power-loss durability and NOT an OS-level kill during a write. SQLite WAL with synchronous=FULL is the durability claim already made.
- Local Anvil, one machine, symbolic mode, runner played by tests.
- It must not be used to claim paper security results: it observes this reconstruction's worker, nothing about the HMBC paper beyond the stated release assumptions.

## Decisions agent-3 would need to make
1. Is an alternate TEST-ONLY entry point acceptable as the E2/E3 start-contract element, or should the production adapter gain a flag (not recommended: it puts a fault path into the production module)?
2. Does the evaluator treat "response received, then exit status 86" (after_send) and "EOF, exit status 86" (after_intent) as satisfying the named schedule steps?
3. Which agents must ACK (agent-1 only for ledger-facing facts, if any).
