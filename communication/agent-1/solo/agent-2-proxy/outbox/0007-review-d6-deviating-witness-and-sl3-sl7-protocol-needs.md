Message-ID: S2-0007
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-1, agent-3 (proxy)
RQ: E
Task: D-6 protocol-scope confirmation of testtools.deviating_witness as an SL4 runner input; R11; protocol needs for SL2-SL7 and P3
Type: REVIEW
Interface-version: v1
Responds-to: A1-0061 (D-6); S3-0001 §2 (SL4 "protocol needs"); S2-0001 R11
Source-manifest: protocol pin 0716a8e2d46f985f35a612d42acaae02ab8701a4 (manifest d16ddad8.., 108 entries); `git show 0716a8e:protocol/testtools/deviating_witness.py` sha256 0511ba571b71d960d8ffbe4b8c811da99ed7de53a4b7515ac425c5291cc3c2d7 (= working tree, = 108-entry manifest entry); repo HEAD 10a1212

Summary:
- **D-6 (protocol scope): confirmed, with conditions.** `testtools.deviating_witness` at pin 0716a8e may be used as an SL4 runner input for the three receipt-binding rows and, later, the no-receipt-binding mutant probe. The custody, invocation, checks and never-publish list are below.
- **No new protocol tool or code is needed for SL2-SL7 or for P3** (mutants, window).
- **R11 (non-strict JSON) is not a risk for SL4** if the runner passes the same deployment bytes the adapter is pinned with. That is a plan condition, not a code change.
- **New disclosure:** assumption **A31** ("collect_decision retries at most once per newly accepted checkpoint") is **not enforced by protocol code**. The witness is stateless. This matters for SL6's "do not re-collect" rule (§3).
- This is a static review: no service or test was started. Correlated self-review.

## 1. D-6: `testtools.deviating_witness` as an SL4 runner input

**What it is.** It is a TEST-ONLY **deliberate witness deviation** (AGENTS.md category: deliberate mutation; assumption A40). It is a defence-in-depth control outside the honest-witness assumption: never an HMBC attack, never honest-witness behaviour.

It signs a GrantReceipt in which exactly one PSC-bound field (`requestDigest`, `gid` or `dataId`) differs from the consistent receipt. It is not one of the adapter's operations, not in `exports/adapter.json` and not imported by `hmbc_protocol/**` (tested: test_supplement_controls.py:100-107).

**Pinned bytes.**
- `protocol/testtools/deviating_witness.py` is sha256 0511ba57.. at 0716a8e and in the 108-entry inventory.
- Its imports are all in the same inventory: `hmbc_protocol/{eip712,keys,messages,wire,chain,ledger,abi}.py` and `abi/*.json`.
- The runner already materializes the protocol snapshot from git blobs at the pin (e1.py `_git_blob`/`materialize_owner`), so these bytes are what runs.
- It is **not** in start-contract-r1, which covers only `faulty_adapter`. The SL4 plan must therefore name it as an owner command with its sha256, and my SL4 ACK will cover that command.

**Invocation (exact).** cwd = the materialized protocol snapshot. Environment = the plan's `serviceEnvironment`; no PYTHONPATH is needed, because `-m` puts the cwd on `sys.path`.

```
python -m testtools.deviating_witness --deployment <D> receipt --grant-id <0x..> --field requestDigest|gid|dataId --at-block <N>
```

- `--deployment` comes **before** the `receipt` subcommand.
- `<D>` must be **the same file, by sha256, that the adapter was pinned with** for that deployment (see R11 below).
- `<N>` is the honest receipt's `dbcBlockNumber`, from that row's own `attest_grant`. Then every field except the altered one equals the honest receipt (test_supplement_controls.py:186-201).
- Do **not** pass `--value`. The default alteration is deterministic: `keccak256("hmbc-test-deviation:"||field||original)`, truncated to 20 bytes for `gid`. That is the recipe owner tests and agent 1's rehearsal used.

**Behaviour the runner may rely on** (deviating_witness.py):

| Line(s) | Behaviour |
|---|---|
| 37-38 | refuses unless the deployment's `fixture.keyDerivation` contains `TEST-ONLY` |
| 39-40 | refuses any field outside the three |
| 41-47 | refuses a non-decimal or non-existent block |
| 48-50 | refuses a grant that is not allowed at that block |
| 57 | refuses an altered value equal to the original |
| 59 | validates the receipt shape with `wire.grant_receipt` |
| 60-62 | signs with the witness key derived inside the process from `fixture.witnessSet.keyLabels[0]` |

**Output:** exactly one JSON line `{schemaVersion:"hmbc-test-deviating-witness/v0", testOnly:true, deviation:{field, original, altered}, receipt, signatures:[sig]}`, exit 0.

**Refusals:** `SystemExit("refusing: …")` gives exit 1, stdout empty and the message on stderr.

**Mutation evidence** (protocol/evidence/mutation-check.json): TEST-ONLY guard DETECTED, field guard DETECTED, `--at-block` format DETECTED. `if not allowed` is a documented equivalent survivor: `wire.grant_receipt` still refuses a zero `grantExpiresAt`.

**Owner tests:** test_supplement_controls.py:58-82 (repaired-e WRONG_SUBJECT and mutant-no-receipt-binding ACCEPT), 109-129, 186-218. They passed in my latest full run (`protocol/evidence/p2-t1-t3/green-full-suite.txt`, 1375 passed).

**Custody.**
- The witness key never leaves the tool process. Nothing it prints contains a key (tested: test_supplement_controls.py:129).
- The runner holds no witness key and must not derive one. Every key is publicly derivable from its label (S2-0003 PK-10), so this is a **procedural** custody rule, not secrecy.
- A non-zero exit can also be a Python traceback, not only `refusing:`. A `ChainError` from an RPC failure is a `RuntimeError`, which `main()` does not catch. The traceback contains no key, because the key is derived only after the chain reads, but it can contain RPC URLs.
- Treat any non-zero exit as a failed trial, keep it, and publish stderr only as a hash plus the first line.

**Checks the runner should perform on each artifact** (my recommendation for the SL4 oracle; the tool itself does not self-verify its signature):
1. Exactly the named field differs from the honest receipt at block N.
2. The signature recovers to the configured witness address under the evaluator's **own** EIP-712 encoder. The GrantReceipt domain is `HMBCReceipt` v1 on the **PBC** PSC (messages.py:52-53).
3. `testOnly == true` and `deviation.field` equals the row's field.

**What the runner must never publish:**
- any private key or seed, or anything derived from a key label;
- raw release tokens. SL4 rows have no RELEASE, but the D1 Alice control does; keep the SL1 practice (`tokenSha256`, no `token` field; S2-0005 preimage scan 0/790);
- the deviating artifact presented as an honest-witness receipt. Keep `testOnly` and `deviation` in the published evidence, and label the rows A40 deliberate deviation, not an HMBC result;
- any use of the tool against a deployment not marked TEST-ONLY (the tool refuses anyway).

**The receipt-signature and positive rows need no tool:**
- signature control: the production `attest_grant`, with one bound field edited and the honest signatures kept;
- positive control: the production `attest_grant`, unchanged.

**SL4 note:** honest `attest_grant` requires PBC status 1 and refuses after an outcome is recorded (witness.py:155-157). Attest each row's honest receipt **before** any report on that request. `attest_grant` has no expiry check, so receipts may be obtained after grant expiry (catalog: "receipts may reconcile after expiry").

## 2. R11: non-strict JSON in `deviating_witness` (deviating_witness.py:77-78)

- **The difference:** the tool reads the deployment with plain `json.loads`, so duplicate keys are last-wins and NaN is accepted. The adapter uses `strict_loads` (adapter.py:51-57, 284). A file with duplicate keys could therefore mean one thing to the adapter (refused) and another to the tool.
- **Why it is not a risk for SL4:**
  - The adapter refuses to start on such a file (`strict_loads` raises in `main()`).
  - The runner validates every deployment with `frozen_validate('LedgerDeployment', …)` before use, for D1 and D2 in `e1._profile`. I cite by name because e1.py is being edited for SL2 and its line numbers move.
  - If the tool receives the **byte-identical** file the adapter was pinned with, its parse equals the strict parse.
- **Condition for the SL4 plan:** the tool's `--deployment` path equals the adapter's `--deployment` path for that deployment. Equal sha256 is enough.
- **Change in E: none.** Changing the tool now would move its pinned hash and force a new protocol pin, for no gain. If agent 1 wants it fixed, it is a one-line change (use `adapter.strict_loads`) plus a test, after gate E. Classified as a hardening item, not a defect affecting results.

## 3. Protocol needs per remaining slice (checked against pin 0716a8e)

| Slice | Protocol pieces | Missing | Notes for the plan |
|---|---|---|---|
| **SL2** forged tuple, new reference, same nonce | production `prepare_request`, `collect_checkpoint`, `collect_decision` | none | **Forged tuple, repaired (D-S1, relay-signed):** a BAD_SIGNATURE from a wrong EIP-712 *digest or domain* would look the same as one from a non-witness signer. The runner should prove its digest is right by checking that the **honest** witness signature recovers to the witness under the runner's own digest, then sign that same digest with the relay key. AccessDecision domain: `HMBCDecision` v1 on the **DBC** KSSC (messages.py:48-49).<br>**Same nonce:** `prepare_request` keeps no nonce state (adapter.py:79-104). The one checkpoint must come **after both** forwards (witness.py:114-115). Both `collect_decision` calls must come **before** any consume: after the first consume the witness refuses with REPLAY (witness.py:122-123). |
| **SL3** dropped/fabricated outcome | production `encrypt_record`, `release`, `worker_log`; `attest_grant` (optional NOT_COMMITTED check) | none | The dropped-outcome rows **must** include RELEASE (S2-0001 R2). Paper release before `policyEnf+30` (A24), bound to the registered key (D35/A38). Expect [INTENT, SENT] with delivery unknown, and PSC status 1. |
| **SL4** receipts | production `attest_grant` + `deviating_witness` (§1) | none | §1 conditions. |
| **SL5** wrong issuer, rollback | `prepare_request` for the final REQUEST_ACCESS | none | The request must carry the **current** `TMSC.authEpoch` (repaired PSC refuses a mismatch, PSC.sol:204). |
| **SL6** barriers, expired duty | `collect_checkpoint`, `collect_decision` | none | See the A31 disclosure below. Expired duty: collect the decision **while the duty is valid at DBC now**, because the witness attests DENY with empty records once any record's `validUntil <= DBC now` (witness.py:133-134). The duty must end before the request, decision and checkpoint expiries. |
| **SL7** wrong destination, expiry boundary | a second production adapter (live-proven in SL1); `collect_checkpoint` + `acceptState` on D2 before D2's `collect_decision` | none | Expiry boundary, repaired: the effective boundary is min(request.expiresAt, decision.expiresAt) (witness.py:140; ACSC.sol:190 per A1-0060). Record which value binds. Collect the decision before the DBC clock moves. |
| **P3** live mutants | the production adapter on `mutant-*` deployments | none | Witness and worker gate on `profile == "2"`, and mutants are REPAIRED_E plus mutation bits (PSC.sol:110-122). `deviating_witness` works on the receipt-binding mutant (test_supplement_controls.py:73-82). The refusal of `mutations != '0'` is runner-side (e1.py/access_execution.py), not protocol. |
| **P3** revocation window | `collect_checkpoint` at the runner's cadence | none | The adapter never pushes checkpoints (S2-0003 PK-16). |

**A31 disclosure (classification: assumption text vs implementation, a tested reconstruction fact).**

- The frozen A31 says `collect_decision` retries "at most once per newly accepted checkpoint". **Nothing in `witness.py` or `adapter.py` counts or limits retries:** the witness is stateless.
- Before a new checkpoint is accepted, a repeated `collect_decision` for a forwarded, unconsumed request yields **another valid ALLOW**. It evaluates credentials at the *checkpoint's* source block, which is pre-revocation in SL6's window, and `decision.expiresAt` may differ, because it includes `DBC now + 30`.
- After a revoking checkpoint is accepted, the witness refuses with STALE_STATE (witness.py:116-117).
- **Safety does not depend on A31:**
  - the DBC grants at most once per grantId and per (gid, nonce);
  - a newer accepted checkpoint invalidates older decisions (sequence equality, A22).
- **For SL6 pre-barrier:** "do not silently re-collect" is **runner discipline**. Recommend the SL6 oracle asserts exactly one `collect_decision` exchange per request, from `exchanges.json`.
- **For the report:** state A31 as a caller-side policy, not an adapter guarantee.

## 4. What this review does not cover

- Ledger facts (agent 1).
- Evaluator collectors and oracles (agent 3 (proxy)).
- The SL2-SL7 plans themselves. Each still needs its own exact FREEZE and my exact protocol-scope ACK, and the SL4 ACK will restate §1 against the plan's exact command and hashes.

Evidence:
- `git show 0716a8e:protocol/testtools/deviating_witness.py | sha256sum` gives 0511ba57.. (= working tree).
- The pin manifest lists every imported module.
- Static reading of deviating_witness.py, witness.py, adapter.py, messages.py:43-59 and chain.py:27-31; protocol/evidence/mutation-check.json.
- No service or test was run for this message.

Impact: SL4 can plan on the existing tool without a new protocol pin. SL2-SL7 and P3 need no new protocol code. A31 wording needs correcting in RQ1-E.md (handled in my draft sections).
Action requested:
- agent 1: accept or amend §1 and the A31 disclosure.
- agent 3 (proxy): build §1's three artifact checks and the R11 same-file condition into the SL4 plan, and the one-decision-per-request check into SL6.
