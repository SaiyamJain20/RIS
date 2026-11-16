# Speaker script: the HMBC end-evaluation deck in 20 minutes

About **18 minutes** spoken (about 2,600 words at a brisk pace, per-slide timings sum to 17 min 50 s),
leaving about two minutes of buffer.
Plain text is what you say. *[Brackets]* are pointing cues. This script matches the 24-page deck
`hmbc-end-presentation.pdf`.

- **Slide numbers** are PDF page numbers. The counter in the slide corner is one lower (the title page
  is not counted).
- **Status to keep straight on every slide:** RQ1 is done (gate E PASS, 12 Oct). RQ2 is in progress:
  the F execution plan is a DRAFT, **gate F has not been run, and none of the 32 F cases has been
  run**. RQ3 is locked and has not started. Never say or imply that RQ2 is finished.
- **Suggested split for three speakers, about 6 minutes each:**

  | Speaker | Slides | Content |
  |---|---|---|
  | A | 1–8 | recap of the paper, our RQs and method; RQ1 complete |
  | B | 9–16 | RQ2: question, design, how it is judged, safety, availability, cost |
  | C | 17–24 | RQ2: durability, trust matrix, out-of-bound results, assurance; status, limits, conclusion |

- **If you run long:** say one sentence each on slides 3 and 14. That saves about a minute.

---

## 1. Title (20 s)

Hi, we're Team 17: Saiyam, Hemang and Eashaan.

At mid-term we presented HMBC, a 2020 paper on sharing medical data across a hierarchy of
blockchains, and our first research question. Today:
- a short recap;
- RQ1, which is complete;
- most of the time on RQ2, which is **in progress**: we'll show what we have measured, and be exact
  about what has not been run yet.

*[Point at the status line]* That line is the honest summary: RQ1 passed its gate, RQ2's gate has not
been run, RQ3 is locked.

## 2. Recap: HMBC in one slide (50 s)

Quick reminder of the paper.
- Organisations that don't trust each other need to share medical data.
- **The purple proxy chain** is run by everyone: registration, trust lists, the single entry point and
  the global log.
- **The green domain chains**, one per domain, hold the access policy and the key store. Users never
  talk to them.
- **Split decryption:** the key store keeps the temporary "on duty" key and does step one; the user
  finishes with their own long-term key. So ending a duty is just a list update.

*[Orange box]* The paper's security argument is informal. It assumes isolation, an honest majority in
every chain, secure crypto and uncompromised keys. RQ2 is about what happens when that honest-majority
assumption fails for the parties that vouch for decisions.

## 3. Recap: JANUS and our stack (35 s)

*[Table, right column]* What we built:
- two local Anvil chains, with the paper's six contracts in Solidity plus our verifier; RQ2 adds a
  Governance contract;
- an **untrusted** relay, so everything important is signed and checked on chain;
- for RQ2, four witness services, each with its own durable store;
- symbolic crypto for now; real ABE only in RQ3.

*[Bottom]* JANUS, the authors' 2023 follow-up, is a related system only. We implement HMBC 2020, and
we use no JANUS code or claims.

## 4. Three RQs: where each stands (45 s)

The three questions, answered in order:
- **RQ1:** which authorisation, freshness and audit properties follow from the paper, which depend on
  missing details, and which repairs enforce them. **Done**, gate E passed on 12 October.
- **RQ2:** with Byzantine witnesses, which RQ1 guarantees survive, with four witnesses, quorum three,
  at most one faulty. **In progress**: the gate has not been run.
- **RQ3:** key lifecycle with real encryption. **Locked**; it starts only after RQ2's gate passes.

*[Timeline]* The F0 fault model was agreed on 4 November; the measurements came on 13 to 15 November;
on 16 November both other roles reviewed the partial RQ2 report at its exact hash. Today the plan is
still a draft and zero of the 32 F cases have run.

## 5. Method and evidence labels (45 s)

Three rules of how we work.
- **Reconstruction:** the authors' code isn't available. Every missing detail is a recorded choice,
  never a "discovered vulnerability".
- **Profiles:** one ledger, several profiles: the paper's, our repaired ones, and mutants that each
  remove one check to show the tests notice.
- **Discipline:** freeze the expected results, the owners acknowledge that exact plan hash, then run,
  then review. Failed trials are kept.

*[Right]* Every result carries a label: **I** for an integrated run by the evaluator, **R** for
cross-run by module owners, **U** for unit or offline tests on real module code, **F** for a formal
model.

*[Orange box]* Keep this in mind for RQ2: **there is no [I] result for RQ2 yet.**

---

## 6. RQ1 recap: gaps and repair (45 s)

RQ1 found three gaps in the paper's flow.
- **Provenance:** the domain chain gets a forwarded tuple; nothing says who it's for, which chain,
  when it expires, or that it's new.
- **Freshness:** trust lists are "the latest", with no version and no expiry.
- **Audit:** an outcome can be logged with no evidence from the domain chain.

*[Right column]* Our repaired-e profile adds typed signatures with a single-use nonce, versioned
lists with signed state checkpoints, and a witness-signed receipt per outcome.

*[Strip]* On the domain chain, 13 checks in a fixed order. Note: in RQ1 that witness is **one trusted
party**. That is exactly where RQ2 starts.

## 7. RQ1 results (55 s)

Each row is something a misbehaving relay or admin does.
- **The paper profiles** reject an identical replay, but only because our grant id is deterministic.
  Everything else they grant: a swapped subject, a forged tuple, a replay under a new reference,
  another deployment's tuple, and so on. Re-installing an old revocation list even **un-revokes** a
  credential.
- **Repaired-e** rejects each one at a named check, and Alice's legitimate access still works in
  every row.
- The worker crash is **BLOCKED** in the paper profiles: the paper says nothing about durability.

*[Orange box]* The revocation window: in repaired-e at most 30 seconds; in the owners' measurement, 2
to 21 seconds depending on the checkpoint delay. In the paper profile, the old tuple was still
grantable 65 seconds later.

These are specification dependencies under a misbehaving relay, which the paper's isolation
assumption excludes. Not exploits.

## 8. Gate E (45 s)

*[Grid]* All 56 catalog rows. In the paper profiles: 8 hold as specified, 20 depend on a gap, 4 are
blocked. In repaired-e: 19 enforced by our checks, 5 controls.
- **Every one** matched the expectation frozen on 8 October: 56 pass, none failed.
- One command, 4,749 seconds, sources unchanged before and after.
- Six ledger mutants are each caught by their tests, and ProVerif shows that dropping the destination
  gives an attack.

Three matching sign-offs: **gate E PASS**. Recorded with it: the integrated mutant matrix and the
integrated window were not run, and the review is correlated, because one model family did all of it.

---

## 9. RQ2: the question (50 s)

*[Italic line]* RQ2: which RQ1 guarantees survive Byzantine witnesses, with **four** witnesses, a
quorum of **three**, and at most **one** faulty?

*[Diagram]* The idea: any two groups of three out of four share at least two witnesses, so with one
faulty witness they share an honest one. An honest witness never signs two conflicting decisions, so
two conflicting certificates can't both form.

*[Right]* Each witness checks the proxy chain itself and signs with its own key; the relay holds no
key. We **keep** three assumptions and state them: safe ledgers, a trusted key worker, eventual
delivery. And we deliberately test **outside** the bound: two Byzantine witnesses, a weakened quorum of
two, a fully compromised quorum.

*[Orange box]* This is not a consensus protocol. It authenticates decisions.

## 10. RQ2 design (60 s)

Three signed paths, plus governance.
- *[Table]* A **checkpoint** of proxy-chain state goes to the key store, which needs a strictly newer
  sequence.
- An **access decision** goes to the access-control contract, through RQ1's 13 checks.
- A **grant receipt** goes back to the proxy contract.
- A **governance action** (adding or removing a credential authority, or setting CA admins) needs a
  quorum with a nonce and an expiry.

*[Bullets]* Every path needs at least three of the four signatures, in strictly increasing signer
order. The witness set itself is fixed at deployment. An honest witness **persists** its one signature
per decision before it replies, and after a grant has used the nonce it refuses a fresh decision with
REPLAY.

## 11. How RQ2 will be judged (45 s)

*[Left]* The real test is the F gate: **32 integrated cases in six families**, from quorum and
availability to governance and compromise. Integrated runs so far: **zero of 32**. The runner's first
two stages exist and correctly report BLOCKED; stages three to seven are in progress.

*[Right]* What we have instead, so far, is offline evidence: a formal model, an oracle check, a pool
sweep, two availability measurements, gas, a durability test, and some out-of-bound ledger tests.
Each one has its label. **None of them is an F case.** We measured what already existed, on purpose,
before the runner was ready.

## 12. Safety 1: TLC (50 s)

A finite model of one decision slot, checked exhaustively with TLC.
- *[Top two rows]* Four witnesses, one faulty, quorum three, persistent single signing: agreement
  **holds**, 108 distinct states, complete. With no faulty witness, it also holds.
- *[Red rows]* Three controls each break it: a quorum of two; two faulty witnesses; and honest
  witnesses that may double-sign.

So the argument needs **both** halves: quorum three **and** witnesses that remember what they signed.

A fresh rerun on 15 November matched every verdict and state count. Limits: one slot, no expiry or
checkpoint changes; not a proof of the implementation or of liveness. And our own first run deadlocked:
a model error we kept in the record.

## 13. Safety 2: oracle vs. store (50 s)

Is our independent checker consistent with the real witness store?
- *[Tiles]* The evaluator's oracle and agent 2's SQLite store decided the same **180** synthetic
  signing requests. They agree on **all 180**: 142 sign, 38 refuse.
- *[Chart]* Then we planted **seven deliberate bugs** in the oracle: an off-by-one on expiry, a
  receipt that never dies, and so on. Every one disagrees with the store, from 4 to 20 times out of
  180.

*[Scope box]* That shows sensitivity to these seven errors, not that the oracle is complete. And it
tests what the store **can** do, not what the service lets happen. We once claimed an honest DENY
could follow a used ALLOW; that was wrong, and it's corrected.

## 14. Safety 3: pool sweep (45 s)

A sweep over the real witness pool code, with real signatures.
- *[Green tile]* With one Byzantine witness: 972 cases, every Byzantine behaviour in every position.
  **Zero** cases where two different values could each gather three signers.
- *[Red tile]* With two, outside the bound: **2,916** such cases out of 4,374.
- In both, every certificate that did form had three distinct, valid, sorted signers.

A "hazard" is a potential conflict, not two real certificates, and the honest witnesses here are a
model of the signing rule, not the durable store.

## 15. Availability (50 s)

Safety is one half; the other is whether legitimate requests still get through.
- *[Left strip]* All 16 ways of muting witnesses, five runs each, in virtual time. Zero or one muted:
  a certificate every time. Two or more: none by the 10-second deadline.
- With delayed replies, it takes the three fastest and doesn't wait for the slowest.
- *[Right table]* Agent 2's live tests with real processes: a certificate in about 0.7 seconds; one
  witness killed, still about 0.6; two stopped, a classified timeout at about 10.5 seconds; a
  restarted witness keeps its durable pin.

Caveat on screen: the raw output of those three process runs wasn't retained, so they're prior
reported runs. One host, no network, and no liveness claim under arbitrary delay.

## 16. Cost (45 s)

What do three signatures cost on chain?
- *[Chart]* For the checkpoint, the decision and the receipt, going from one signature to three costs
  **+11.0%, +5.5% and +3.7%** gas.
- Each extra signature adds about 6.8 thousand gas and 160 bytes of calldata.
- Governance actions cost 424 to 524 thousand gas with three signatures.
- All contracts stay under the 24-kilobyte size limit.

The evaluator measured these and the ledger owner reproduced all 21 rows exactly, with raw logs kept.
Single deterministic runs: not a fee estimate.

## 17. Durability: K1 (55 s)

This one is a story about a test, not the system.
- *[Left]* The mutant K1 removes the database transaction around signing, so each write commits
  alone. A crash between writes leaves a half-written record, and the kill test must catch it.
- *[Chart]* It had been reported as caught 3 of 3. We ran it 40 times: **29 of 40**. The kill
  happened at a random moment, so it only sometimes landed between the writes.
- The fix: put a test hook **between** the writes. Then **40 of 40**, with 40 of 40 controls. Agent 2
  confirmed it independently: 15 of 15.
- The same review found and fixed three real defects along the way.

*[Scope line]* This is process kill only. It says nothing about power loss.

## 18. Trust matrix (40 s)

What does RQ2 still have to trust?
- *[Orange]* **Required:** three of four honest witnesses, and an honest governance quorum.
- *[Gray]* **Trusted:** the key worker, which a quorum doesn't protect against; the credential
  authorities; the local chains.
- *[Blue]* The relay has no key; the witnesses are separate processes, but on one host.
- *[Red]* **Not evaluated:** key custody, the client and the data store. And all code and reviews come
  from one model family.

## 19. Outside the bound (60 s)

What happens when the bound is broken? All three are tested on the ledger with scratch tests.
- *[First card]* **Three or more Byzantine witnesses can halt a domain chain permanently.** They sign a
  checkpoint with a maxed-out counter; every honest checkpoint after it is stale; nothing on the ledger
  can reset it. You have to redeploy.
- *[Second card]* **They can also get a grant for a requester who never existed**, using fabricated
  credentials that fit the policy's shape. The domain chain only checks those records through the
  quorum's signature. Two signers, or non-fitting records, are refused.
- *[Third card]* **With two Byzantine witnesses**, the ledger rejects a second checkpoint or a second
  ALLOW. But a DENY and an ALLOW for the same request are **both accepted**, in either order, because a
  DENY uses no nonce in our design. An honest witness refuses to sign a fresh decision after a grant,
  but that doesn't stop a DENY that was already signed.

*[Bottom line]* None of this contradicts the one-fault claims, and none of it is an HMBC vulnerability.

## 20. Assurance (45 s)

How did we check all this?
- *[Left]* The partial report is pinned by its SHA-256 hash. The ledger role and the protocol role each
  read the full diff and found no objection in their scope. A review isn't permission to run anything.
- *[Table]* We keep our mistakes. Seven are on screen: a wrong claim about honest DENYs; a ledger
  sentence that mixed up signing and acceptance; a test count of 9 that was really 6; a secret scan
  that read a missing directory; a contract size that was a parser artefact; the K1 rate; and a check
  that hashed only a paragraph's first line.

*[Orange box]* Honest limit: all three roles are the same model family, so these are scoped re-checks,
not independent review.

---

## 21. Honest status (45 s)

Where RQ2 really stands today.
- *[Tiles]* The execution plan is a **draft** and authorises nothing. Gate F: **not run**, none of its
  eight checklist boxes ticked. F cases: **zero of 32** run. RQ3: **locked**.
- *[Left]* Done: the agreed fault model, the ledger and protocol code with their tests, the reviewed
  partial report, the first runner stages. A merged snapshot of all three modules passes the ledger and
  protocol suites; the evaluation suite has four failures that are specific to the test host.
- *[Right]* Still needed before gate F: an exact execution freeze with every role's acknowledgement,
  the remaining runner stages, the 32 integrated cases, RQ1's suites re-run on the new ledger, then the
  report and three sign-offs.

## 22. Limitations and lessons (45 s)

*[Left]* Limits: correlated review; synthetic fixtures; a model is not the implementation; offline is
not integrated; no real crypto yet. Even when F passes, it won't prove consensus, safety with two
Byzantine witnesses, liveness under any delay, or power-loss durability.

*[Right]* Five lessons we'd pass on:
1. A test with a random fault point can look green: put the fault where the bug lives.
2. Check your checks: a scan of a missing directory "passes".
3. Bind by value, not label: the weakened mutant's manifest names the normal profile; only the
   threshold read back on chain tells them apart.
4. Hash the whole artifact.
5. Keep signing rules and ledger rules apart.

## 23. Conclusion (40 s)

- **RQ1 is answered:** the paper's flow leaves 20 of 32 rows depending on unspecified details; our
  repair closes each with a named check; gate E passed.
- **RQ2 has a partial answer:** with at most one faulty witness, three of four quorums overlap in an
  honest witness; the model, the sweep and isolated tests support it; one witness down still
  certifies, two don't; the cost is 3.7 to 11 percent more gas per signed path. What we **have not shown yet** is that RQ1's
  guarantees survive in the integrated system.
- **Next:** the freeze, the remaining runner stages, the 32 cases and gate F. Only then RQ3, with real
  attribute-based encryption.

*[Banner]* Everything here is about our reconstruction of HMBC, not the authors' code.

## 24. Thank you (5 s)

Thank you. Questions?

---

# Q&A backups (not part of the 20 minutes)

- **"So did RQ2 pass?"**
  - No. Gate F has not been run, and none of the 32 F cases has been run. The execution plan is a
    draft. What we presented are offline and formal results, each labelled, plus a partial report that
    the other two roles reviewed at its exact hash.
- **"Why show numbers before the gate runs?"**
  - We chose to measure what already existed before the runner was ready. Each number says what it
    is, and none is presented as an F case. The F gate still needs the 32 integrated cases.
- **"Is this a consensus protocol? Is Anvil Byzantine fault tolerant?"**
  - No to both. The witnesses authenticate decisions; the chains are assumed safe, and we say so.
- **"Why 3 of 4?"**
  - Two quorums of three out of four share at least two members, so at least one honest one when only
    one is faulty. The TLC model shows a quorum of two breaks agreement.
- **"Isn't the forged-credential grant a serious bug?"**
  - It needs three of the four witnesses compromised, which is outside the bound we claim. It shows
    what "governance quorum: required" costs if that trust fails. We recorded it in the trust matrix;
    we have not designed or tested a mitigation, and it is not a finding about HMBC.
- **"Why doesn't a DENY use a nonce?"**
  - That was an RQ1 reconstruction choice (a denial only writes a log entry). In RQ2 it means two
    Byzantine witnesses can get both a DENY and an ALLOW logged for one request. The ledger still
    refuses a second ALLOW.
- **"Does 40 of 40 for K1 mean the store is crash-safe?"**
  - No. It means the test now reliably catches that one deliberate bug. It is process kill only; a
    power-loss mutant survives, and we make no power-loss claim.
- **"Why weren't the M6 raw outputs kept?"**
  - The three runs were recorded as results but their raw output and exact command weren't retained in
    the evaluator's evidence. We now present them as prior reported runs, not auditable ones.
- **"Who reviewed this?"**
  - The other two roles, each in its own scope, at exact file hashes. All three roles are the same
    model family, so this is correlated review, not independent review.
- **"Did you find vulnerabilities in HMBC?"**
  - No; we claim none. RQ1's gaps are where the paper is underspecified, under a misbehaving relay the
    paper's isolation assumption excludes. RQ2's out-of-bound results are about our extension.
- **"What is RQ3, and when?"**
  - Real MA-CP-ABE (the paper's Lewko–Waters scheme, via Charm) with the key store / user split, key
    epochs, and what stays secret after revocation, joining or a later key compromise. It is locked
    until gate F passes; we give no date.
- **"Is the gas overhead a problem?"**
  - +3.7% to +11.0% per signed path, single deterministic runs. It is not a fee estimate, and we make
    no throughput claim.

# Key terms

| Term | Meaning |
|---|---|
| **PBC / DBC** | Proxy blockchain (shared front door) / domain blockchain (one per organisation type) |
| **Witness** | Service that reads the proxy chain, checks a decision itself and signs it |
| **n, q, f** | Number of witnesses (4), signatures needed (3), faulty witnesses tolerated (1) |
| **Certificate** | A message plus at least q witness signatures, checked on chain |
| **Checkpoint** | Signed snapshot of the proxy chain's state; a newer one makes older decisions stale |
| **Governance action** | Quorum-signed change to the trust lists: add or remove an authority, set CA admins |
| **Byzantine** | A participant that may behave arbitrarily, including lying or signing conflicting things |
| **TLC** | The TLA+ model checker: explores every state of a small finite model |
| **Oracle / store** | Our independent rule checker / agent 2's durable SQLite record of what a witness signed |
| **K1** | A deliberate bug that removes the signing transaction, used to test the kill test |
| **FREEZE / ACK** | Hash-pinned plan that authorises a run / each role's acknowledgement of that exact hash |
| **Gate** | End-of-RQ check: one frozen integrated run plus three matching sign-offs |
| **[I] [R] [U] [F]** | Integrated evaluator run / owners' cross-run / unit or offline test / formal model |
