# Speaker script: the HMBC deck in 20 minutes

About **18 minutes** spoken (≈2,400 words at a normal pace), leaving about two minutes of buffer.
Plain text is what you say. *[Brackets]* are pointing cues. This script matches the current
24-page deck.

- **Slide numbers** are PDF page numbers. The counter in the slide corner is one lower.
- **Suggested split for three speakers, about 6 minutes each:**

  | Speaker | Slides | Content |
  |---|---|---|
  | A | 1–8 | the paper |
  | B | 9–16 | JANUS, our project, the RQ1 gaps and method |
  | C | 17–24 | the RQ1 repair and results, what comes next |

- **If you run long:** click through slides 12 and 13 with one sentence each. That saves about a minute.

---

## 1. Title (20 s)

Hi, we're Team 17: Saiyam, Hemang and Eashaan.

Our project starts from **HMBC**, a 2020 IEEE Access paper on sharing medical data across
organisations using a hierarchy of blockchains. We'll cover:
- the paper;
- its follow-up, JANUS;
- our own project, and the results of its first research question, RQ1, which is now complete.

## 2. Why was this needed? (45 s)

Hospitals, device makers, insurers and labs need each other's data.
- They **don't trust each other**.
- Each one manages its own users.

*[Cloud]* There were two options before this paper:
- **A shared cloud** makes sharing easy, but you must trust the operator with the data and the
  access records.
- *[Blockchain]* **A blockchain** removes that trusted operator. But existing designs serve one
  organisation, with fixed membership.

*[Orange box]* HMBC wants both.

*[Example]* The running example:
- An emergency doctor from Hospital X needs a patient's records held at Hospital Y.
- They should get them only while on duty.
- The access must be revocable and logged.

## 3. Requirements and prior work (30 s)

There are five requirements:
- no global certificate authority;
- fine-grained access that is time-limited and revocable;
- **attribute-based encryption**: you encrypt for a *policy*, like "doctor AND on duty", not for a
  person;
- policies enforced by smart contracts;
- every request logged.

*[Table]* In the authors' own comparison, HMBC is the only scheme with all five. That's their
self-assessment, not an independent one.

## 4. Architecture (45 s)

There are two layers of chains.
- **The purple proxy chain** is run by every organisation. It's the single front door: registration,
  trust lists and the global log.
- **Below it, one domain chain per type of organisation.**
  - It enforces that domain's policy and does the decryption.
  - Users never talk to it directly.
- **The medical records stay off-chain**, encrypted.

*[Contract strip]* There are six smart contracts:
- **On the proxy chain:**
  - RSC, registration;
  - TMSC, trust lists;
  - PSC, the entry point;
  - LSC, the log.
- **On each domain chain:**
  - ACSC, access control;
  - KSSC, the key store.

## 5. Trust and temporal roles (55 s)

There's no global CA, so each hospital is its own CA and its own encryption-key authority.
- **Trust lists.** It publishes three of them on the proxy chain:
  - its root certificate;
  - its revocation list;
  - its **TempACL**: who holds a temporary role like "on duty", and when.
- **Checking.** The TMSC checks every credential against these lists.

*[User A]*
- **One global ID.** A user with roles at two hospitals gets one global ID, the **GID**.
- **No key pooling.** The encryption scheme only combines keys issued to the same GID, so two people
  can't pool their keys.
- **Two kinds of role.** Long-term roles like Doctor live in the certificate. Temporal roles like
  on-duty only count together with one.

*[KSSC box]* The key twist: the **on-duty key is never given to the user**. It stays in the KSSC.

## 6. How a request flows (55 s)

*[Follow the numbers.]*
- **(1)** The doctor sends credentials and a record ID to the proxy contract, and a log entry opens
  immediately.
- **(2–3)** The TMSC checks the credentials against the trust lists.
- **(4)** The proxy forwards the GID, the verified attributes and the data ID to the hospital chain.
- **(5)** The ACSC checks the policy.
- **(6–8)** The KSSC fetches the encrypted record and does **step one** of the decryption with the
  on-duty key. The result is still encrypted.
- **(9–10)** It comes back through the proxy, logged on both chains, and the user finishes the
  decryption with their own key.

Remember **step 4**: the paper doesn't say how the domain chain checks that this tuple really came
from a genuine proxy decision. That's our gap number 1.

## 7. Two-step decryption (55 s)

The core idea is a safe with two locks.
- The KSSC holds the on-duty key, and the doctor holds the Doctor key.
- Neither can open it alone.

*[Policy box]* The record's policy: *a doctor at X treating this patient*, **or** *any doctor who is
on duty*.

Why split the decryption?
- **Revocation is a list update.** The on-duty key never reaches the user, so ending a duty just
  removes a TempACL entry. No key has to be revoked.
- **The KSSC can't decrypt on its own.**
- **The user's device does only the light last step.**
- **No bypass.** A "System" attribute ANDed into every policy means nothing can be decrypted outside
  the system.

## 8. Prototype performance (45 s)

The prototype used:
- a private Ethereum chain;
- Solidity contracts;
- the Charm crypto library;
- Docker and Kubernetes, on one machine.

*[Bar chart]* One access takes **603 ms**: 527 ms in the contracts, with the KSSC the largest, and
74 ms on the user's side.

*[Line chart]* Time grows roughly linearly with load: about 1 second at 30 concurrent requests, 3 to
4 seconds at 100.

*[Orange box]* The security part is an informal argument, under strong assumptions:
- isolation;
- an honest majority;
- secure crypto and uncompromised keys;
- all measured on one machine.

Two years later, the same group built **JANUS**.

---

## 9. JANUS (35 s)

JANUS came out in 2023: the same authors, with the company CENSUS. It's an open-source
implementation on Hyperledger Fabric, Kubernetes and Vault. What's new:
- a formal access model;
- the single access point enforced with a domain key that only the KSSC can derive. That realises
  HMBC's "System" role;
- records encrypted with AES, and ABE only on the keys;
- message queues, and voting for governance;
- load tests up to 300 concurrent requests, with no failures.

## 10. JANUS vs. HMBC (35 s)

The main changes:
- Fabric with Raft instead of Ethereum;
- five contracts, with login through each organisation's own CA;
- the KSSC holds a domain key instead of temporal keys. In our reading, the user now holds the
  on-duty key, so ending a duty relies on an online check.

*[Orange box]* JANUS leaves three things open:
- Raft tolerates crashes, not malicious nodes;
- isolation and an honest majority are assumed;
- there's no key rotation.

Those match our three research questions. JANUS is context only: we implement HMBC 2020.

## 11. Our project: three research questions (50 s)

There are three research questions, answered in order: RQ1, then RQ2, then RQ3.
- **RQ1:** which authorisation, freshness and audit properties follow from the paper, which depend
  on missing details, and which repairs enforce them.
- **RQ2:** what survives if operators or witnesses are malicious.
- **RQ3:** what stays secret after revocation, joining, or a later key compromise.

Each one builds the test harness the next one needs.

*[Method]*
- **A reconstruction.** The authors' code isn't public, so we built a **paper-derived
  reconstruction**. Every missing detail is an explicit, recorded choice, never a "discovered
  vulnerability".
- **Three modules:** ledger, protocol and evaluation, on three machines, with a frozen interface
  between them.
- **Gates.** Each research question ends with a gate that all three module owners sign off.

## 12. Why this direction (45 s)

Briefly, row by row:
- **RQ1:**
  - nothing binds the domain chain's grant to the proxy chain's decision;
  - trust lists have no versions;
  - outcomes are logged without evidence.
  The general ideas, typed signatures and nonces, are known. What's missing is an executable analysis
  of HMBC's own flow.
- **RQ2:** HMBC assumes an honest majority. We study a 3-of-4 witness quorum, not a new consensus.
- **RQ3:** revocation is only gatekeeping, with no key epochs.

And we found no published instance-level security analysis of HMBC or JANUS.

## 13. Tech stack (30 s)

- **Chains and contracts:** two local Anvil chains, with the six contracts in Solidity plus our
  DecisionVerifier, built with Foundry. We make no consensus claims.
- **Messaging:** an **untrusted** relay carries messages between the chains, so everything important
  is signed and checked on chain.
- **Encryption:** symbolic in RQ1. Real ABE comes in RQ3.
- **Keys:** they live in an off-chain worker.
- **Evaluation:** tests, mutants, an independent checker, and ProVerif.

## 14. Why this stack (35 s)

*[Diagram]*
- The client signs.
- A witness reads the proxy chain and signs what it saw.
- The untrusted relay forwards, and the domain chain verifies.
- The key worker releases the key.
- The evaluator watches from outside.

**Kept**, because it's what makes this HMBC: Solidity, the six contracts, separate chains, the
paper's ABE library.

**Changed on purpose:**
- Foundry, because Ganache and Truffle were discontinued;
- no Fabric, Kubernetes or Vault;
- a signed, untrusted relay;
- no consensus claims.

Now RQ1, which is complete.

---

## 15. The gaps (55 s)

RQ1 asks what **follows** from the paper, what **depends** on its gaps, and what **repairs** fix them.
We found three gaps.

- **RQ1-01, decision provenance.** The domain chain receives a tuple forwarded by a relay. Nothing
  says:
  - who it's for;
  - which chain it targets;
  - when it expires;
  - whether it's a replay.
- **RQ1-02, trust-anchor freshness.** Trust lists are just "the latest", with no version and no
  expiry.
  - What stops an old signed list from being re-installed?
  - When must a revocation reach the domain chain?
- **RQ1-03, audit correspondence.** An outcome can be logged with no evidence from the domain chain.
  And the paper is silent on a crash between key release and logging.

The paper assumes isolated components, so these are gaps in the specification, not attacks on HMBC.
We test what each reasonable way of filling them gives, and what a repair adds.

## 16. Method (60 s)

The same six contracts run in four profiles:
- **paper-strict** follows the paper and fills the gaps the safest way;
- **paper-minimal** is a weaker, still reasonable reading;
- **repaired-e** is our extension, not HMBC;
- **six mutants** each remove one repaired check, to prove the tests notice.

*[Steps]*
- **The catalog:** 16 schedules in 3 profiles, plus 8 repaired-only rows, makes 56. The expectations
  were frozen on 8 October, before anything ran.
- **Controls first:** every row uses fresh chains and runs the controls first (Alice allowed, Bob
  denied), so a "deny everything" profile can't pass.
- **An independent checker** reads both chains and labels the row.
- **Failed trials are kept.**

*[Labels]* The four labels:
- **SUPPORTED:** follows from the paper;
- **SPEC_GAP:** depends on a gap;
- **REPAIR_SUPPORTED:** our fix enforces it;
- **BLOCKED:** undecidable from the paper.

On 12 October one command re-ran all 56 rows, and **every one matched its frozen expectation**. That
closed RQ1's gate.

## 17. What we built: repaired-e (55 s)

*[Top row]* The repaired flow:
1. The user signs the request.
2. A **witness** signs a checkpoint and a decision.
3. The domain chain runs **13 checks** and uses the nonce once.
4. The worker logs its intent before sending.
5. Logging the outcome needs a signed receipt.

*[Cards, left to right]*
- **Who, where, when, once:** typed EIP-712 signatures bound to one contract on one chain, a
  single-use nonce, and a 30-second lifetime.
- **Fresh trust state:** versioned, expiring trust lists, plus signed checkpoints that act as a
  revocation barrier.
- **Evidence per outcome:** a witness-signed receipt for every outcome, and durable worker
  intent.

*[Strip]* The 13 checks run in a fixed order, so the same defect always gives the same error code.
Step 12 is reserved for RQ3.

Note that in RQ1 the witness is **one trusted party**. RQ2 removes that.

## 18. Results RQ1-01 (50 s)

Each row is something a misbehaving relay does.
- **Identical replay** is rejected even by the paper profiles, but only because our grant ID is
  deterministic, a choice we recorded.
- **Everything else, the paper profiles grant:**
  - a swapped subject, with the response going to the wrong person;
  - a forged tuple;
  - a replay under a new reference;
  - another deployment's tuple;
  - a delivery exactly at expiry.
- **Repaired-e rejects each one at a named check:** `WRONG_SUBJECT`, `BAD_SIGNATURE`, `REPLAY`,
  `WRONG_DESTINATION`, `EXPIRED`.

And Alice's legitimate access still works in every row.

## 19. Results RQ1-02 and the revocation window (60 s)

- **A CA admin updating another hospital's list** is rejected in every profile. The paper itself
  specifies that rule.
- **An older signed revocation list re-installed:**
  - the paper profiles accept it, so **a revoked credential is un-revoked**;
  - repaired rejects it with `STALE_ANCHOR`.
- **An old decision used after a revocation:**
  - the paper profiles keep accepting it, because there's no barrier;
  - repaired accepts it only until the domain chain sees the next checkpoint, then refuses with
    `STALE_STATE`.
- **An expired duty:** the paper profiles grant it at that instant; repaired says `EXPIRED`.

*[Chart]* How long is the window after a revocation?
- **Repaired-e:** the window follows the checkpoint delay (2, 6, 11 and 21 seconds), and the
  30-second request lifetime caps it.
- **Paper-strict:** the decision was still usable 65 seconds later.

This chart is our owner measurement on two machines; it wasn't part of the final 56-row run.

## 20. Results RQ1-03 (50 s)

- **A duplicate outcome** is rejected everywhere.
- **A dropped outcome** leaves the request visibly pending.
- **A fabricated outcome with no grant:**
  - the paper profiles record it;
  - repaired needs a receipt, so it rejects it.
- **A receipt naming a different request** is rejected.
- **A key-worker crash:**
  - the paper says nothing about durability, so we label it **BLOCKED**: never a pass, never a
    finding;
  - repaired re-sends the same cached response: one grant, one outcome. After expiry, nothing
    happens.

A grant is permission to release, **not proof of delivery**. So delivery stays "unknown", and we
report it that way.

## 21. Mutants and ProVerif (45 s)

Are the checks real? We tested that two ways.

- **Mutants.** Each one removes one check.
  - The ledger's mutant tests catch all six.
  - In the 56-row run, eight rows hit exactly the guards the mutants remove.
  - One subtlety: the live wrong-destination case can't catch the no-destination mutant, because an
    earlier check fires first. Only the unit tests and ProVerif catch it.
- **ProVerif.**
  - In the repaired model, every grant matches what the user asked for and the witness approved, on
    all 8 fields.
  - Drop the destination, and it finds an attack.
  - It's a symbolic model, so replay and expiry are covered by the live tests instead.

## 22. What RQ1 shows (55 s)

In numbers:
- in the two paper profiles, 20 of 32 rows depend on a gap;
- in repaired-e, 19 of 24 rows are enforced by a check we added, and the other 5 are controls.

*[Orange card]* The answer to RQ1:
- **Holds as specified:** HMBC already rejects identical replays and duplicate outcomes, and it
  restricts list updates.
- **Depends on its gaps:** ten case schedules, plus crash recovery.
- **Repairable:** each one can be closed with a named, explicit check, and legitimate access keeps
  working.

*[Green card]* Why it matters:
- implementers get a concrete list of the decisions the paper leaves open, each with a test;
- revocation gets a bound;
- the 56-row run becomes a harness that RQ2 and RQ3 must keep passing.

*[Gray card]* The limits: symbolic crypto, one trusted witness and worker, local chains, one trial per
row.

*[Banner]* And that one trusted witness is exactly where RQ2 begins.

## 23. Next: RQ2, then RQ3 (45 s)

**RQ2** replaces the one trusted witness with **four**, one per hospital.
- **The rule:** 3 of the 4 must sign, and the system tolerates one faulty witness.
- **Why it works:**
  - any two groups of three share at least two witnesses, so at least one honest one;
  - an honest witness never signs two conflicting decisions.
- **The plan:**
  - first, freeze the fault model and the expected results;
  - then quorum contracts, four independent witnesses, fault runs and a TLA+ model;
  - with RQ1's 56 rows re-run as regression.

**Then RQ3, the key lifecycle:** real ABE, key epochs, and what stays secret after revocation or
compromise.

We're at the planning step for RQ2 now.

## 24. Thank you (5 s)

Thank you. Questions?

---

# Q&A backups (not part of the 20 minutes)

- **"Did you find vulnerabilities in HMBC?"**
  - No; we claim none.
  - The gaps are where the paper is underspecified, and every stress case uses a misbehaving relay,
    which HMBC's isolation assumption rules out.
- **"Isn't 56/56 just your own expectations?"**
  - The expectations were frozen before any run, and a separate checker reads both chains.
  - Failed attempts are kept on record, and "matching" includes the gap and blocked results.
- **"Why does repaired-e still accept a decision just after a revocation?"**
  - The domain chain can't know about a revocation until a checkpoint arrives.
  - The repair bounds that window (at most 30 s here); before the repair there was no bound.
- **"Why no real encryption in RQ1?"**
  - RQ1 is about who may get a key and what gets logged.
  - Real ABE comes in RQ3, and we make no secrecy or performance claims until then.
- **"Why one trial per row?"**
  - These are correctness checks with deterministic outcomes.
  - The timing numbers are single samples, and we say so.
- **"Was every planned check run?"** No, two were not run on the integrated two-chain system:
  - **The live mutant run.** Our agent tooling's safety check stopped the automated attempt, and the
    team chose not to force it. The mutant criterion rests on the ledger's mutant tests, ProVerif and
    the 8 guard rows.
  - **The revocation-window measurement.** The chart on slide 19 is the module owners' own
    measurement instead.
- **"Who reviewed the results?"**
  - For the last three days of RQ1, two of our agents were offline, so stand-in agents running the
    same model reviewed the final work.
  - When the original protocol and evaluation agents came back, each re-checked its own part and
    accepted it.
  - They are still the same model, so this is not independent review.
- **"Why Anvil and not a real network?"**
  - RQ1 studies the access protocol and assumes safe ledgers; we state that.
  - Anvil is a deterministic local chain, and we claim no consensus properties.

# Key terms

| Term | Meaning |
|---|---|
| **PBC / DBC** | Proxy blockchain (shared front door) / domain blockchain (one per organisation type) |
| **ABE, MA-CP-ABE** | Encrypt for a policy over attributes; many independent key authorities (Lewko–Waters) |
| **GID** | One global user ID; keys combine only under the same GID, which prevents key pooling |
| **TempACL** | Signed list of temporary roles (like on-duty) with time windows |
| **Profile** | paper-strict, paper-minimal, repaired-e, or a mutant (one check removed) |
| **SUPPORTED / SPEC_GAP / REPAIR_SUPPORTED / BLOCKED** | Follows from the paper / depends on a gap / our fix enforces it / undecidable from the paper |
| **Relay / witness** | Untrusted message carrier between chains / service that reads both chains and signs decisions |
| **Checkpoint** | Signed snapshot of the proxy chain's state; a newer one makes older decisions stale |
| **Nonce / EIP-712** | Number used once / Ethereum standard for typed signatures bound to one contract and chain |
| **ProVerif / TLA+** | Protocol-model checker (used in RQ1) / state-machine model checker (used in RQ2) |
| **Gate** | End-of-RQ check: one frozen run plus three matching sign-offs |
