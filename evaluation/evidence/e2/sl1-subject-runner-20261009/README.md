# SL1: E01 subject-substitution runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059/A1-0061). **This is correlated self-review**, not
independent review.

**Status:** runner implemented and unit-verified; plan frozen as S3-0005. No service, chain, adapter
or worker has run. **No catalog row is completed by this checkpoint.**

## Catalog rows and frozen expectations

| Row | Expected outcome | Class | Error |
|---|---|---|---|
| E01-subject-substitution-paper-strict | CONDITIONAL | SPEC_GAP | – |
| E01-subject-substitution-paper-minimal | CONDITIONAL | SPEC_GAP | – |
| E01-subject-substitution-repaired-e | REJECT | REPAIR_SUPPORTED | WRONG_SUBJECT(2) |

Compromised-relay stress lies outside the paper's secure-isolation assumption (A01). This is a
reconstruction/specification-gap comparison, not an HMBC exploit.

## Recipe (`integration-plan.json` sha256 6fd5809b..)

Each profile row gets a fresh Anvil pair. PBC listens on port 18545 (chain ID 18545); DBC listens on
port 18546 (chain ID 28545). Automining, cancun.

1. **Deployment D1 (controls).** Owner deployment and bootstrap, which includes the wrong-admin
   rejection (code 16). Then Alice: allow, release, completion, one outcome. Then Bob: policy denial
   (code 9). This is the existing `e1._profile` path, unchanged.
2. **Deployment D2 (stress), fresh, on the same chain pair.**
   - Reset the relay and CA-admin balances to 1000 ETH.
   - Owner deployment `<run>-subject`; its contract addresses must be disjoint from D1's.
   - Own bootstrap, again with the code-16 check.
   - Own production adapter and 0700 state.
3. **Stress on D2.** Alice's real signed, logged PBC request. The relay changes **only** `gid` to
   registered Bob:
   - paper profiles: the ForwardedRequest passed to `policyEnf`, with Alice's verified records;
   - repaired-e: the request passed to `consumeDecision`, with Alice's original ALLOW certificate and
     records.

   The pre-release collector (`collect_subject_substitution`) takes whole block-anchored snapshots
   before and after: grant, request, both nonces, access count, decoded histories of both chains, and
   the idle worker.
   - **Paper:** a grant for Bob with zero native recipient and TTL `policyEnf + 30 s`; Alice's
     request is still FORWARDED.
   - **Repaired-e:** mined status 0, Rejected(2), no logs, nothing changed.
4. **Paper completion only** (`execute_subject_completion`, new):
   1. Read the registered PBC recipient keys for both subjects (A35 expectation).
   2. One production `release` on the substituted grant.
   3. Snapshot.
   4. Run `finish_decryption` on the **same** response with `keyref:user:bob` (expect decryptable)
      and `keyref:user:alice` (expect WRONG_SUBJECT).
   5. Snapshot.

   Then `check_subject_completion` (A3-0049) requires exactly one worker intent/send/cache delta,
   completions that change nothing, and every step inside the grant lifetime. No outcome is reported
   for Alice's request.
5. `e2.execute` accepts a row only with these complete proofs:
   - repaired-e: no completion file may exist;
   - paper: completion required, with Bob decryptable, Alice WRONG_SUBJECT and no outcome.
6. Solo ACK records are verified before snapshots and services.

**Cast hashing:** checkpoint policy per read group and submit, plus run start and end.

## Verification so far (`manifest.json`)

**RED.** The new tests were run against the pre-SL1 sources in a scratch copy:

- collector: 12 failed, 1 passed;
- plan: 18 failed.

*Honest note:* this RED was demonstrated **after** writing the code, by restoring the HEAD versions
of the changed files in scratch. It was not a strict test-first order.

**GREEN.**

- targeted: 31 passed;
- full suite `.venv/bin/python -m pytest -q -rs`: exit 0, **856 passed, 0 failed, 0 skipped**,
  253.66 s;
- the inputs bracket (1959 files) was stable.

**Negative controls that must fail:**

- release routed to Alice's key;
- cache gid not Bob;
- an extra send;
- Alice able to decrypt;
- Bob refused;
- a completion that changes the worker;
- completion requested on repaired-e or without the stress;
- a non-boolean flag.

**Plan-level controls:**

- strict mode or a combined probe is refused;
- an edited probe, classification, control or freshness text is refused;
- no solo records gives BLOCKED before services;
- each incomplete proof gives FAILED.

## Limits

- **D2 wiring is not yet live-tested.** The paths for the second deployment, adapter and bootstrap
  in `e1._profile` have only had a static undefined-name check and code review.
- Paper rows need the release before `policyEnf + 30 s`; the expected margin is about 20 s
  (estimate, not measured). Any expiry fails visibly; there is no TTL change.
- **Delivery unknown.** Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness
  assumptions. No authors' implementation claim.
- **Do not touch these files until the run** (they are in the plan's `agent3Sources`):
  - `evaluation/**/*.py`, including evidence scripts;
  - `evaluation/fixtures` and `evaluation/scenarios` JSON;
  - `interfaces/v1/**` and `interfaces/proposals/v1/**/*.json`;
  - root `AGENTS.md`, `SPEC.md`, `PLAN.md`, `uv.lock` and `pyproject.toml`;
  - `evaluation/toolchain.json` and `evaluation/host-tools.json`.

  Any change means a new plan and new ACKs.
