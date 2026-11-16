# Speaker script: the HMBC end-evaluation deck in about 23 minutes

About **23 minutes** spoken (about 3,300 words at a brisk pace; the per-slide timings below sum to
23 min 0 s). Plain text is what you say. *[Brackets]* are pointing cues. This script matches the
30-page deck `hmbc-end-presentation.pdf`.

- **Slide numbers** are PDF page numbers. The counter in the slide corner is one lower (the title page
  is not counted).
- **Status to keep straight on every slide:** RQ1 is done (gate E PASS, 12 Oct). RQ2 is in progress:
  the F execution plan is a DRAFT, **gate F has not been run, and none of the 32 F cases has been
  run**. Never say or imply that RQ2 is finished.
- **Suggested split for three speakers, about 7½ minutes each:**

  | Speaker | Slides | Content |
  |---|---|---|
  | A | 1–9 | the paper, JANUS, our project, RQ1 question, method, repair, results for gap 1 |
  | B | 10–19 | RQ1 gap 2 and 3, mutants, gate E and what RQ1 shows; RQ2 question, design, how it is judged, TLC, oracle |
  | C | 20–30 | RQ2 pool sweep, availability, cost, durability, trust matrix, out-of-bound results, assurance, status; limits, conclusion |

- **If you run long:** say one sentence each on slides 7, 17 and 20. That saves about a minute and a half.

---

## 1. Title (20 s)

Hi, we're Team 17: Saiyam, Hemang and Eashaan.

Our project starts from **HMBC**, a 2020 IEEE Access paper on sharing medical data across
organisations using a hierarchy of blockchains. We built a **paper-derived reconstruction** of it and
asked two research questions. Today:
- the paper, in two slides;
- RQ1, which is complete;
- RQ2, which is **in progress**: we'll show what we have measured, and be exact about what has not been
  run yet.

## 2. The paper (1/2): problem and architecture (70 s)

Hospitals, device makers, insurers and researchers need each other's data.
- **They don't trust each other**, and each one manages its own users.
- A shared cloud makes sharing easy, but you must trust the operator; existing blockchains serve one
  organisation.

*[Running example]* An emergency doctor from Hospital X needs a patient's records held at Hospital Y,
only while on duty. The access must be revocable and logged.

*[Figure]* HMBC's answer is a hierarchy of chains.
- **Users**, people and devices, each get one global ID.
- **Each stakeholder** runs its own certificate authority and its own encryption-key authority, and
  one node on each chain. Its CA admins publish trust lists.
- **The purple proxy chain** is run by everyone. *[Strip]* It has four contracts: registration, trust
  lists, the single entry point, and the global log.
- **The green domain chains**, one per domain, have two: the access policy and the key store. Users
  never talk to them.
- **The records** stay off chain, encrypted with attribute-based encryption: you encrypt for a policy,
  like "doctor AND on duty", not for a person.

## 3. The paper (2/2): how access works, and what it assumes (55 s)

*[Follow the boxes]* One access, at a high level:
- The user sends a **request** with their credentials.
- The **proxy chain verifies** those credentials against the trust lists.
- The **domain chain checks** the access policy.
- The **key release** happens in two steps: the key store does the first half of the decryption, and
  the user finishes it.
- Every request and access is **logged on both chains**.

*[Left]* That split is the key idea. The key store keeps the "on duty" key and never gives it to
users; the user holds the long-term "doctor" key. Neither can decrypt alone, so **revocation is just a
list update**: ending a duty removes an entry, and no key is re-issued.

*[Orange box]* The security argument is informal. It assumes isolation, an honest majority in every
chain, secure crypto and uncompromised keys.

*[Bottom right]* Our two questions probe exactly this. RQ1: what the flow itself guarantees, and what
depends on details it leaves open, such as what binds the domain chain's grant to the proxy chain's
decision. RQ2: what survives when the honest majority fails.

## 4. JANUS: the authors' extension (45 s)

Before our own work, one slide on **JANUS**. It is the extension of HMBC by the same authors, with the
company CENSUS, published in Applied Sciences in 2023. *[Right, bullets]* The main extensions:
- **a formal access model**, with attribute checks on the proxy chain and authorisation and decryption
  on the domain chain;
- **an open-source system** on Hyperledger Fabric with Raft, in Kubernetes pods *[left: the stack]*;
- **the single access point enforced by cryptography**: a domain key that only the key store can
  derive is ANDed into every policy;
- **hybrid encryption**: records under AES, attribute-based encryption only for the AES keys;
- message queues, voting for governance, and load tests up to 300 concurrent requests.

*[Orange line]* What it leaves open: Raft tolerates crashes, not malicious nodes; Byzantine tolerance is
named as future work. That is close to our RQ2. JANUS is related work only: we implement HMBC 2020 and
use none of its code.

## 5. Our project (60 s)

*[Cards]* Two research questions, answered in order.
- **RQ1**, authorisation, freshness and audit, is **done**: gate E passed on 12 October.
- **RQ2**, Byzantine witnesses, is **in progress**: its gate has not been run.

*[Left]* How we work:
- **A reconstruction.** The authors' code isn't available. Every missing detail is a recorded choice,
  never a "discovered vulnerability".
- **Discipline:** we freeze the expected results, the module owners acknowledge that exact plan hash,
  then we run, then we review. Failed trials are kept.
- **Three roles**, ledger, protocol and evaluation, on three machines. All the same model family, which
  matters for how independent our reviews are.

*[Middle]* Every result carries a label: **I** for an integrated run by the evaluator, **R** for a
cross-run by module owners, **U** for unit or offline tests, **F** for a formal model.

*[Right]* What we built: two local Anvil chains, the paper's six contracts in Solidity plus our own
verifier, Python services, and an **untrusted** relay, so everything important is signed and checked on
chain. Crypto is symbolic, so we make no secrecy claims.

---

## 6. RQ1: the question and the gaps (55 s)

RQ1 asks what **follows** from the paper, what **depends** on its gaps, and what **repairs** fix them.
We found three gaps.

- **RQ1-01, decision provenance.** The domain chain receives a tuple forwarded by a relay. Nothing
  says:
  - who it's for;
  - which chain it targets;
  - when it expires;
  - whether it's a replay.
- **RQ1-02, trust-anchor freshness.** Trust lists are just "the latest", with no version and no
  expiry. What stops an old signed list from being re-installed? When must a revocation reach the
  domain chain?
- **RQ1-03, audit correspondence.** An outcome can be logged with no evidence from the domain chain.
  And the paper is silent on a crash between key release and logging.

The paper assumes isolated components, so these are gaps in the specification, not attacks on HMBC.

## 7. RQ1 method (55 s)

The same six contracts run in four profiles:
- **paper-strict** follows the paper and fills the gaps the safest way;
- **paper-minimal** is a weaker, still reasonable reading;
- **repaired-e** is our extension, not HMBC;
- **six mutants** each remove one repaired check, to prove the tests notice.

*[Steps]*
- **The source map:** 37 paper passages, and 41 recorded choices where the paper is silent.
- **The catalog:** 16 schedules in 3 profiles, plus 8 repaired-only rows, makes 56. The expectations
  were frozen on 8 October, before anything ran.
- **Controls first:** every row uses fresh chains and runs the controls first (Alice allowed, Bob
  denied), so a "deny everything" profile can't pass.
- **An independent checker** reads both chains and labels the row.

*[Labels]* Four classes: **SUPPORTED** follows from the paper; **SPEC_GAP** depends on a gap;
**REPAIR_SUPPORTED** our fix enforces it; **BLOCKED** can't be decided from the paper.

## 8. RQ1: the repaired-e profile (50 s)

*[Top row]* The repaired flow:
1. The user signs the request.
2. A **witness** signs a checkpoint and a decision.
3. The domain chain runs **13 checks** and uses the nonce once.
4. The worker logs its intent before sending.
5. Logging the outcome needs a signed receipt.

*[Cards]*
- **Who, where, when, once:** typed signatures bound to one contract on one chain, a single-use nonce,
  and a 30-second lifetime.
- **Fresh trust state:** versioned, expiring trust lists, plus signed checkpoints that act as a
  revocation barrier.
- **Evidence per outcome:** a witness-signed receipt for every outcome, and durable worker intent.

*[Strip]* The 13 checks run in a fixed order, so the same defect always gives the same error code.

Note that in RQ1 the witness is **one trusted party**. RQ2 removes that.

## 9. RQ1 results, gap 1 (50 s)

Each row is something a misbehaving relay does.
- **Identical replay** is rejected even by the paper profiles, but only because our grant ID is
  deterministic, a choice we recorded.
- **Everything else, the paper profiles grant:** a swapped subject, with the response going to the
  wrong person; a forged tuple; a replay under a new reference; another deployment's tuple; a delivery
  exactly at expiry.
- **Repaired-e rejects each one at a named check:** `WRONG_SUBJECT`, `BAD_SIGNATURE`, `REPLAY`,
  `WRONG_DESTINATION`, `EXPIRED`.

And Alice's legitimate access still works in every row.

## 10. RQ1 results, gap 2, and the revocation window (60 s)

- **A CA admin updating another hospital's list** is rejected in every profile. The paper itself
  specifies that rule.
- **An older signed revocation list re-installed:** the paper profiles accept it, so **a revoked
  credential is un-revoked**; repaired rejects it with `STALE_ANCHOR`.
- **An old decision used after a revocation:** the paper profiles keep accepting it, because there's
  no barrier; repaired accepts it only until the domain chain sees the next checkpoint, then refuses
  with `STALE_STATE`.
- **An expired duty:** the paper profiles grant it at that instant; repaired says `EXPIRED`.

*[Chart]* How long is the window after a revocation? In repaired-e it follows the checkpoint delay,
2, 6, 11 and 21 seconds, and the 30-second request lifetime caps it. In paper-strict the old decision
was still usable 65 seconds later. This chart is the owners' measurement on two machines, not part of
the gate run.

## 11. RQ1 results, gap 3 (50 s)

- **A duplicate outcome** is rejected everywhere.
- **A dropped outcome** leaves the request visibly pending.
- **A fabricated outcome with no grant:** the paper profiles record it; repaired needs a receipt, so it
  rejects it.
- **A receipt naming a different request** is rejected.
- **A key-worker crash:** the paper says nothing about durability, so we label it **BLOCKED**: never a
  pass, never a finding. Repaired re-sends the same cached response: one grant, one outcome. After
  expiry, nothing happens.

A grant is permission to release, **not proof of delivery**. So delivery stays "unknown", and we report
it that way.

## 12. Mutants and ProVerif (45 s)

Are the checks real? We tested that two ways.
- **Mutants.** Each one removes one check. The ledger's tests catch all six, and in the 56-row run
  eight rows hit exactly the guards the mutants remove. One subtlety: the live wrong-destination case
  can't catch the no-destination mutant, because an earlier check fires first; only the unit tests and
  ProVerif catch it.
- **ProVerif.** In the repaired model, every grant matches what the user asked for and the witness
  approved, on all 8 fields. Drop the destination, and it finds an attack. It's symbolic, so replay and
  expiry are covered by the live tests instead.

## 13. Gate E (45 s)

*[Grid]* All 56 catalog rows. In the paper profiles: 8 hold as specified, 20 depend on a gap, 4 are
blocked. In repaired-e: 19 enforced by our checks, 5 controls.
- **Every one** matched the expectation frozen on 8 October: 56 pass, none failed.
- One command, 4,749 seconds, sources unchanged before and after.
- Three matching sign-offs: **gate E PASS**, on 12 October.

*[Caveat]* Recorded with it: the integrated mutant matrix and the integrated window were not run, and
the review is correlated, because one model family did all of it.

## 14. What RQ1 shows (45 s)

*[Orange card]* The answer to RQ1:
- **Holds as specified:** HMBC already rejects identical replays and duplicate outcomes, and restricts
  list updates.
- **Depends on its gaps:** ten case schedules, plus crash recovery.
- **Repairable:** each one can be closed with a named, explicit check, and legitimate access keeps
  working.

*[Green card]* Why it matters: implementers get a concrete list of the decisions the paper leaves open,
each with a test; revocation gets a bound; and the 56-row run is a harness RQ2 must keep passing.

*[Gray card]* The limits: symbolic crypto, one trusted witness and worker, local chains, one trial per
row.

*[Banner]* And that one trusted witness is exactly where RQ2 begins.

---

## 15. RQ2: the question (50 s)

*[Italic line]* RQ2: which RQ1 guarantees survive Byzantine witnesses, with **four** witnesses, a
quorum of **three**, and at most **one** faulty?

*[Diagram]* Any two groups of three out of four share at least two witnesses, so with one faulty
witness they share an honest one. An honest witness never signs two conflicting decisions, so two
conflicting certificates can't both form.

*[Right]* Each witness checks the proxy chain itself and signs with its own key; the relay holds no
key. We **keep** three assumptions and state them: safe ledgers, a trusted key worker, eventual
delivery. And we deliberately test **outside** the bound: two Byzantine witnesses, a weakened quorum of
two, a fully compromised quorum.

*[Orange box]* This is not a consensus protocol. It authenticates decisions.

## 16. RQ2 design (55 s)

Three signed paths, plus governance.
- *[Table]* A **checkpoint** of proxy-chain state goes to the key store, which needs a strictly newer
  sequence.
- An **access decision** goes to the access-control contract, through RQ1's 13 checks.
- A **grant receipt** goes back to the proxy contract.
- A **governance action**, adding or removing a credential authority or setting CA admins, needs a
  quorum with a nonce and an expiry.

*[Bullets]* Every path needs at least three of the four signatures, in strictly increasing signer
order. The witness set itself is fixed at deployment. An honest witness **persists** its one signature
per decision before it replies, and after a grant has used the nonce it refuses a fresh decision with
REPLAY.

## 17. How RQ2 will be judged (40 s)

*[Left]* The real test is the F gate: **32 integrated cases in six families**, from quorum and
availability to governance and compromise. Integrated runs so far: **zero of 32**. The runner's first
two stages exist and correctly report BLOCKED; stages three to seven are in progress.

*[Right]* What we have so far is offline evidence: a formal model, an oracle check, a pool sweep, two
availability measurements, gas, a durability test, and some out-of-bound ledger tests. Each has its
label. **None of them is an F case.**

## 18. Safety 1: TLC (45 s)

A finite model of one decision slot, checked exhaustively with TLC.
- *[Top rows]* Four witnesses, one faulty, quorum three, persistent single signing: agreement
  **holds**, 108 distinct states, complete. With no faulty witness, it also holds.
- *[Red rows]* Three controls each break it: a quorum of two; two faulty witnesses; honest witnesses
  that may double-sign.

So the argument needs **both** halves: quorum three **and** witnesses that remember what they signed.
A fresh rerun matched every verdict and state count. Limits: one slot, no expiry; not a proof of the
implementation or of liveness. Our own first run deadlocked: a model error we kept in the record.

## 19. Safety 2: oracle vs. store (45 s)

Is our independent checker consistent with the real witness store?
- *[Tiles]* The evaluator's oracle and agent 2's SQLite store decided the same **180** synthetic
  signing requests. They agree on **all 180**: 142 sign, 38 refuse.
- *[Chart]* Then we planted **seven deliberate bugs** in the oracle. Every one disagrees with the store,
  from 4 to 20 times out of 180.

*[Scope box]* That shows sensitivity to these seven errors, not completeness. And it tests what the
store **can** do, not what the service lets happen. We once claimed an honest DENY could follow a used
ALLOW; that was wrong, and it's corrected.

## 20. Safety 3: pool sweep (40 s)

A sweep over the real witness pool code, with real signatures.
- *[Green tile]* With one Byzantine witness: 972 cases, every behaviour in every position. **Zero**
  cases where two different values could each gather three signers.
- *[Red tile]* With two, outside the bound: **2,916** such cases out of 4,374.
- In both, every certificate that did form had three distinct, valid, sorted signers.

A "hazard" is a potential conflict, not two real certificates, and the honest witnesses here are a
model of the signing rule.

## 21. Availability (45 s)

- *[Left strip]* All 16 ways of muting witnesses, five runs each, in virtual time. Zero or one muted:
  a certificate every time. Two or more: none by the 10-second deadline. With delayed replies it takes
  the three fastest.
- *[Right table]* Agent 2's live tests with real processes: a certificate in about 0.7 seconds; one
  witness killed, still about 0.6; two stopped, a classified timeout at about 10.5 seconds; a
  restarted witness keeps its durable pin.

Caveat on screen: the raw output of those three process runs wasn't retained, so they're prior
reported runs. One host, no network, no liveness claim under arbitrary delay.

## 22. Cost (40 s)

*[Chart]* For the checkpoint, the decision and the receipt, going from one signature to three costs
**+11.0%, +5.5% and +3.7%** gas. Each extra signature adds about 6.8 thousand gas and 160 bytes of
calldata. Governance actions cost 424 to 524 thousand gas. All contracts stay under the 24-kilobyte
limit.

The evaluator measured these and the ledger owner reproduced all 21 rows exactly. Single deterministic
runs: not a fee estimate.

## 23. Durability: K1 (50 s)

This one is a story about a test.
- *[Left]* The mutant K1 removes the database transaction around signing, so each write commits alone.
  A crash between writes leaves a half-written record, and the kill test must catch it.
- *[Chart]* It had been reported as caught 3 of 3. We ran it 40 times: **29 of 40**. The kill came at a
  random moment, so it only sometimes landed between the writes.
- The fix: a test hook **between** the writes. Then **40 of 40**, with 40 of 40 controls; agent 2
  confirmed it independently, 15 of 15.

*[Scope line]* Process kill only. It says nothing about power loss.

## 24. Trust matrix (35 s)

What does RQ2 still have to trust?
- **Required:** three of four honest witnesses, and an honest governance quorum.
- **Trusted:** the key worker, which a quorum doesn't protect against; the credential authorities; the
  local chains.
- The relay has no key; the witnesses are separate processes, but on one host.
- **Not evaluated:** key custody, the client and the data store. And all code and reviews come from one
  model family.

## 25. Outside the bound (55 s)

What happens when the bound is broken? All three are scratch tests on the ledger.
- *[First card]* **Three or more Byzantine witnesses can halt a domain chain permanently.** They sign a
  checkpoint with a maxed-out counter; every honest checkpoint after it is stale; nothing on the ledger
  can reset it. You have to redeploy.
- *[Second card]* **They can also get a grant for a requester who never existed**, using fabricated
  credentials that fit the policy's shape. Two signers, or non-fitting records, are refused.
- *[Third card]* **With two Byzantine witnesses**, the ledger rejects a second checkpoint or a second
  ALLOW, but a DENY and an ALLOW for one request are **both accepted**, because a DENY uses no nonce in
  our design. An honest witness refuses to sign after a grant, but that doesn't stop a DENY already
  signed.

None of this contradicts the one-fault claims, and none of it is an HMBC vulnerability.

## 26. Assurance (40 s)

- *[Left]* The partial report is pinned by its hash. The ledger role and the protocol role each read
  the full diff and found no objection in their scope. A review isn't permission to run anything.
- *[Table]* We keep our mistakes: a wrong claim about honest DENYs; a sentence that mixed up signing and
  acceptance; a test count of 9 that was really 6; a scan that read a missing directory; a size that was
  a parser artefact; the K1 rate; a check that hashed only a paragraph's first line.

*[Orange box]* All three roles are the same model family, so these are scoped re-checks, not
independent review.

## 27. Honest status of RQ2 (45 s)

- *[Tiles]* The execution plan is a **draft** and authorises nothing. Gate F: **not run**, none of its
  eight checklist boxes ticked. F cases: **zero of 32** run. What **is** done: the partial report was
  reviewed by the other two roles at its exact hash.
- *[Left]* Also done: the agreed fault model, the ledger and protocol code with their tests, the first
  runner stages. A merged snapshot of all three modules passes the ledger and protocol suites; the
  evaluation suite has four failures specific to the test host.
- *[Right]* Still needed before gate F: an exact execution freeze with every role's acknowledgement,
  the remaining runner stages, the 32 integrated cases, RQ1's suites re-run on the new ledger, then the
  report and three sign-offs.

## 28. Limitations and lessons (45 s)

*[Left]* Limits: correlated review; synthetic fixtures; a model is not the implementation; offline is
not integrated; symbolic crypto. Even when F passes, it won't prove consensus, safety with two
Byzantine witnesses, liveness under any delay, or power-loss durability.

*[Right]* Five lessons:
1. A random fault point can look green: put the fault where the bug lives.
2. Check your checks: a scan of a missing directory "passes".
3. Bind by value, not label: the weakened mutant's manifest names the normal profile; only the
   threshold read back on chain tells them apart.
4. Hash the whole artifact.
5. Keep signing rules and ledger rules apart.

## 29. Conclusion (40 s)

- **RQ1 is answered:** in the paper's flow, 20 of 32 rows depend on unspecified details; our repair
  closes each with a named check; gate E passed.
- **RQ2 has a partial answer:** with at most one faulty witness, three-of-four quorums overlap in an
  honest witness; the model, the sweep and isolated tests support it; one witness down still
  certifies, two don't; the cost is 3.7 to 11 percent more gas per signed path. What we **have not
  shown yet** is that RQ1's guarantees survive in the integrated system.
- **Next:** the freeze, the remaining runner stages, the 32 cases, and only then a gate F decision.

*[Banner]* Everything here is about our reconstruction of HMBC, not the authors' code.

## 30. Thank you (5 s)

Thank you. Questions?

---

# Q&A backups (not part of the spoken time)

- **"So did RQ2 pass?"**
  - No. Gate F has not been run, and none of the 32 F cases has been run. The execution plan is a
    draft. What we presented are offline and formal results, each labelled, plus a partial report that
    the other two roles reviewed at its exact hash.
- **"Why show numbers before the gate runs?"**
  - We chose to measure what already existed before the runner was ready. Each number says what it
    is, and none is presented as an F case.
- **"Did you find vulnerabilities in HMBC?"**
  - No; we claim none. RQ1's gaps are where the paper is underspecified, under a misbehaving relay the
    paper's isolation assumption excludes. RQ2's out-of-bound results are about our extension.
- **"Isn't 56/56 just your own expectations?"**
  - The expectations were frozen before any run, and a separate checker reads both chains. Failed
    attempts are kept on record, and "matching" includes the gap and blocked results.
- **"Why does repaired-e still accept a decision just after a revocation?"**
  - The domain chain can't know about a revocation until a checkpoint arrives. The repair bounds that
    window (at most 30 s here); before the repair there was no bound.
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
    the evaluator's evidence. We present them as prior reported runs, not auditable ones.
- **"Was every planned RQ1 check run?"**
  - Two were not run on the integrated system: the live mutant matrix (our tooling's safety check
    stopped it, and the team chose not to force it) and the integrated revocation window (the chart is
    the owners' measurement instead).
- **"Who reviewed this?"**
  - The other roles, each in its own scope, at exact file hashes. All three roles are the same model
    family, so this is correlated review, not independent review.
- **"Why no real encryption?"**
  - Both questions are about who may get a key, what is signed and what gets logged. We make no secrecy
    or performance claim.
- **"Is the gas overhead a problem?"**
  - +3.7% to +11.0% per signed path, single deterministic runs. It is not a fee estimate, and we make
    no throughput claim.

# Key terms

| Term | Meaning |
|---|---|
| **PBC / DBC** | Proxy blockchain (shared front door) / domain blockchain (one per organisation type) |
| **ABE** | Attribute-based encryption: encrypt for a policy over attributes, not for a person |
| **GID** | One global user ID; keys combine only under the same GID |
| **TempACL** | Signed list of temporary roles (like on-duty) with time windows |
| **Profile** | paper-strict, paper-minimal, repaired-e (RQ1), repaired-f (RQ2), or a mutant (one check removed) |
| **SUPPORTED / SPEC_GAP / REPAIR_SUPPORTED / BLOCKED** | Follows from the paper / depends on a gap / our fix enforces it / undecidable from the paper |
| **Relay / witness** | Untrusted message carrier between chains / service that checks a decision itself and signs it |
| **n, q, f** | Number of witnesses (4), signatures needed (3), faulty witnesses tolerated (1) |
| **Certificate** | A message plus at least q witness signatures, checked on chain |
| **Checkpoint** | Signed snapshot of the proxy chain's state; a newer one makes older decisions stale |
| **Byzantine** | A participant that may behave arbitrarily, including lying or signing conflicting things |
| **ProVerif / TLC** | Protocol-model checker (RQ1) / TLA+ model checker that explores every state of a small model (RQ2) |
| **K1** | A deliberate bug that removes the signing transaction, used to test the kill test |
| **FREEZE / ACK** | Hash-pinned plan that authorises a run / each role's acknowledgement of that exact hash |
| **Gate** | End-of-RQ check: one frozen integrated run plus three matching sign-offs |
| **[I] [R] [U] [F]** | Integrated evaluator run / owners' cross-run / unit or offline test / formal model |
