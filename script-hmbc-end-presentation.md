# Speaker script: the HMBC end-evaluation deck in about 20 minutes

About **20 minutes** spoken (about 3,050 words at a brisk pace; the per-slide timings below sum to
19 min 45 s). Plain text is what you say. *[Brackets]* are pointing cues. This script matches the
25-page deck `hmbc-end-presentation.pdf`.

- **Slide numbers** are PDF page numbers. The counter in the slide corner is one lower (the title page
  is not counted).
- **Status to keep straight on every slide:** RQ1 is done (gate E PASS, 12 Oct). RQ2 is in progress:
  the F execution plan is a DRAFT, **gate F has not been run, and none of the 32 F cases has been
  run**. Never say or imply that RQ2 is finished.
- **Suggested split for three speakers, about 6½ minutes each:**

  | Speaker | Slides | Content |
  |---|---|---|
  | A | 1–8 | the paper, JANUS, our two research questions, RQ1 gaps, Fix 1–3, the Gap 1 result |
  | B | 9–16 | Gap 2 and Gap 3 results, what RQ1 shows; RQ2 question, design, how it is judged; Experiments 1 and 2 |
  | C | 17–25 | Experiments 3–6, the security findings beyond the bound, what RQ2 shows; limits, conclusion |

- **If you run long:** say one sentence each on slides 11, 14 and 20. That saves about a minute.

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

## 5. What we set out to answer (60 s)

Two research questions, answered in order. *[Left card]*
- **RQ1, authorisation, freshness and audit.** Which properties follow from HMBC's flow, which depend
  on details it leaves out, and which repairs enforce them?
- **Why it matters:** the paper never says what binds the domain chain's grant to the proxy chain's
  decision, how fresh the trust lists must be, or what evidence an outcome log needs.
- **How we answer it:** we run the paper's flow against our repaired profile on a frozen 56-row
  catalog, on two local chains. *[Badge]* It is **done**: gate E passed on 12 October.

*[Right card]*
- **RQ2, Byzantine witnesses.** If some of the witnesses that vouch for each decision are Byzantine,
  which RQ1 guarantees survive, and which quorum and state rules are enough?
- **Why it matters:** HMBC assumes an honest majority in every chain, and RQ1's repair trusts a single
  witness.
- **How we answer it:** four witnesses, a quorum of three, at most one faulty, assuming safe ledgers
  and a trusted key worker; the verdict comes from 32 integrated F cases. *[Badge]* It is **in
  progress**: that gate has not been run.

---

## 6. RQ1: the question and the gaps (55 s)

RQ1 asks what **follows** from the paper, what **depends** on its gaps, and what **repairs** fix them.
We found three gaps, and we'll keep their numbers and colours all the way through.

- *[Orange 1]* **Gap 1, decision provenance.** The domain chain receives a tuple forwarded by a relay.
  Nothing says who it's for, which chain it targets, when it expires, or whether it's a replay.
- *[Purple 2]* **Gap 2, trust-list freshness.** Trust lists are just "the latest", with no version and
  no expiry. What stops an old signed list from being re-installed? When must a revocation reach the
  domain chain?
- *[Green 3]* **Gap 3, audit evidence.** An outcome can be logged with no evidence from the domain
  chain, and the paper is silent on a crash between key release and logging.

The paper assumes isolated components, so these are gaps in the specification, not attacks on HMBC.

## 7. RQ1: what we built, Fix 1 to 3 (60 s)

*[Flow, left to right]* Our repaired flow in five stages: the user **signs** the request; the proxy
chain **logs it and checks credentials**; a **witness signs** a state checkpoint and the decision; the
domain chain **verifies everything, uses the nonce once, and grants**; the key worker **releases**, and
a signed receipt closes the log. The numbered badges show where each fix acts.

*[Cards]* Each fix answers the gap with the same number:
- **Fix 1, decision provenance:** typed signatures from the user and the witness, bound to one contract
  on one chain, a single-use nonce, and a 30-second lifetime.
- **Fix 2, trust-list freshness:** versioned, expiring trust lists, plus signed checkpoints that act as
  a revocation barrier.
- **Fix 3, audit evidence:** a witness-signed receipt for every outcome, and durable worker intent.

*[Bottom line]* This is our extension, not HMBC. We run the paper's flow, in two readings, and this
repaired flow on one frozen catalog of 56 rows. And in RQ1 the witness is **one trusted party**: RQ2
removes that.

## 8. Gap 1 result (55 s)

*[Grey line under the table]* From here on, result slides carry a label: **I** for an integrated run
by the evaluator, **R** for a cross-run by the module owners, **U** for unit or offline tests, **F**
for a formal model.

Each row is something a misbehaving relay does. A tick means the attack is stopped; a cross means it
gets through.
- **Identical replay** is rejected even by the paper's flow, but only because our grant ID is
  deterministic, a choice we recorded.
- **Everything else gets through the paper's flow:** a swapped subject, with the response going to the
  wrong person; a forged tuple; a replay under a new reference; another deployment's tuple; a delivery
  exactly at expiry.
- **Fix 1 rejects each one at a named check:** `WRONG_SUBJECT`, `BAD_SIGNATURE`, `REPLAY`,
  `WRONG_DESTINATION`, `EXPIRED`.

And Alice's legitimate access still works in every row.

## 9. Gap 2 result and the revocation window (60 s)

- **A CA admin updating another hospital's list** is rejected in both flows. The paper itself
  specifies that rule.
- **An older signed revocation list re-installed:** the paper's flow accepts it, so **a revoked
  credential is un-revoked**; Fix 2 rejects it with `STALE_ANCHOR`.
- **An old decision used after a revocation:** the paper's flow keeps accepting it, because there's no
  barrier; the repaired flow accepts it only until the domain chain sees the next checkpoint, then
  refuses with `STALE_STATE`.
- **An expired duty:** the paper's flow grants it at that instant; the repaired flow says `EXPIRED`.

*[Chart]* How long is the window after a revocation? In the repaired flow it follows the checkpoint
delay, 2, 6, 11 and 21 seconds, and the 30-second request lifetime caps it. In the paper's flow the old
decision was still usable 65 seconds later. This chart is the owners' measurement on two machines, not
part of the gate run.

## 10. Gap 3 result (50 s)

- **A duplicate outcome** is rejected in both flows, and **a dropped outcome** leaves the request
  visibly pending.
- **A fabricated outcome with no grant:** the paper's flow records it; Fix 3 needs a receipt, so it
  rejects it.
- **A receipt naming a different request** is rejected.
- **A key-worker crash:** the paper says nothing about durability, so for the paper's flow we record it
  as **blocked**: unproved, never counted as a pass or a finding. The repaired flow re-sends the same
  cached response: one grant, one outcome. After expiry, nothing happens.

A grant is permission to release, **not proof of delivery**. So delivery stays "unknown", and we report
it that way.

## 11. What RQ1 shows (45 s)

*[Orange card]* The answer to RQ1:
- **Holds as specified:** HMBC already rejects identical replays and duplicate outcomes, and restricts
  list updates.
- **Depends on its gaps:** ten case schedules, plus crash recovery.
- **Repairable:** each one can be closed with a named, explicit check, and legitimate access keeps
  working.

*[Green card]* Why it matters: implementers get a concrete list of the decisions the paper leaves open,
each with a test; revocation gets a bound of at most 30 seconds; and the 56-row run is a harness RQ2
must keep passing.

*[Line above the banner]* The verdict: **gate E passed** on 12 October; all 56 catalog rows matched
their frozen expectation, and the checks are real: six ledger mutants are each caught by their tests, and
ProVerif finds an attack once the destination check is dropped.

*[Banner]* And our RQ1 repair puts all decision trust on one witness. That is exactly where RQ2 begins.

---

## 12. RQ2: the question (50 s)

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

## 13. RQ2 design (50 s)

*[Diagram]* Four witnesses, one per hospital, each with its own key and its own durable store. A
collector gathers their signatures; it holds no key itself.

*[Table]* Four things get certified:
- a **state checkpoint**: a snapshot of the proxy chain's trust and authorisation state, checked by the
  hospital's key-service contract;
- an **access decision**: the outcome and credential binding for one request, checked by the
  hospital's policy contract;
- a **grant receipt**: facts that tie an outcome to a committed grant, on the shared audit path;
- a **governance action**: adding or removing a credential authority or changing its admins, with a
  nonce and an expiry.

Each needs at least three of the four signatures, and the witness set is fixed at deployment.
**Signatures alone are not enough:** an honest witness remembers what it signed, across restarts, and
replaces an old approval only once it is provably obsolete.

## 14. How RQ2 is judged (40 s)

*[Left]* RQ2 is judged by its gate on integrated cases in six families: quorum and availability; the
signing rule and Byzantine witnesses; durable state and restart; trust lists and governance; relay and
outcomes; and compromise and residual trust.

*[Right]* The gate requires that RQ1's guarantees still hold; a trust matrix; signatures that are
unique, bound and durable; safety with at most one faulty witness; the advertised limit with two; a
TLC model; and one frozen integrated run with three sign-offs.

*[Grey line]* Whether those integrated runs have happened is stated on "What RQ2 shows". They have not yet.

## 15. Experiment 1 result: why three approvals are needed (50 s)

*[Grey question]* Can two conflicting values both obtain enough approvals? We modeled one decision slot
in TLA+ and let TLC explore every reachable state.

*[Table, top two rows]* With a quorum of three and at most one malicious witness, agreement **holds**:
108 distinct states, the complete graph. With no malicious witness, it holds too.
*[Red rows]* A quorum of two, two malicious witnesses, or honest witnesses that may double-sign: each
one breaks agreement, with a counterexample trace.

*[Orange box]* So both halves are needed: the quorum of three, and each witness's persistent refusal to
sign a conflicting value. The model covers one slot; a fresh rerun reproduced all five verdicts.

## 16. Experiment 2 result: certificate collection with real signatures (45 s)

*[Grey question]* Does the collector filter bad replies while respecting the quorum boundary? Real
signatures, scripted witnesses, and nine malicious behaviours, from staying silent to using a wrong key.

*[Table]* With one malicious witness: 972 scenarios, 180 certificates, **zero** invalid and **zero**
potential agreement hazards. With two, outside the bound: 4,374 scenarios, 330 certificates, still none
invalid, but **2,916** runs end where two values could each collect three approvals.

*[Orange box]* Valid signatures alone don't give agreement; signer overlap does. The 2,916 are modeled
possibilities, not observed double grants.

## 17. Experiment 3 result: the availability boundary (50 s)

*[Grey question]* How many witnesses can stop responding before collection stops?

*[Table, virtual rows]* Over 80 virtual trials: with none or one witness silent, a three-signature
certificate every time; with two or more, none by the 10-second deadline. With delayed replies it
finished at 300 milliseconds, using the three fastest.
*[Process rows]* With real processes: accepted in about 0.7 seconds, still about 0.6 with one witness
killed, and a timeout at about 10.5 seconds with two stopped. The restarted witness kept its record.

*[Orange box]* One unavailable witness is tolerated, two are not: the intended boundary. These are local
timings, and the process runs are weaker evidence because their raw output was not kept.

## 18. Experiment 4 result: can a crash split a signing record? (50 s)

*[Grey question]* If a witness dies mid-signing, can it come back with a half-written memory? Its
remembered approval and the signed hash must commit together, so we removed the database transaction
on purpose and killed the process mid-signing.

*[Table]* The correct store passes 40 of 40 runs. The broken store was caught in only 29 of 40 with
timing-based kills. With pauses placed between the signing statements, it is caught 40 of 40 times, and
agent 2 reproduced that: 15 of 15.

*[Orange box]* Controlled interruption reliably exposes the defect. Process death only: no power-loss
claim.

## 19. Experiment 5 result: when does a different signature become legal? (50 s)

*[Grey question]* When may a witness replace an old approval with a different value? Too strict blocks
progress; too loose allows two live values. We compared a separate rule checker with the real store on
180 cases.

*[Table, first row]* With the correct rules they agree on all 180: 142 replacements allowed, 38
conflicts refused.
*[Other rows]* Then we broke seven checker rules on purpose, for example treating the exact expiry
instant as still valid, or never retiring an executed receipt. Every one is detected, between 4 and 20
disagreements.

*[Orange box]* The checker matches the store and catches these seven errors. It is store-level evidence;
what callers assert still needs separate checks.

## 20. Experiment 6 result: cost (40 s)

*[Grey question]* What does going from one attester to three approvals cost on chain?

*[Table and chart]* The same contract code under one and three signatures: **+11.0%** gas to accept a
checkpoint, **+5.5%** for a decision, **+3.7%** for an outcome.

*[Orange box]* Each extra signature adds about 6.8 thousand gas and 160 bytes. Peers reproduced every
row; this is not a fee or throughput estimate. *[Side note]* Governance actions cost 424 to 524 thousand
gas, and all contracts stay under the 24-kilobyte limit.

## 21. Security findings beyond the fault bound (50 s)

*[Grey line]* All three need at least two malicious witnesses, outside the one-fault bound.
- *[First card]* **Conflicting certificates are partly stopped by the contracts.** A second checkpoint
  or a second ALLOW is refused. But an ALLOW and a DENY for one request are both accepted, because a
  denial uses no nonce in our design, so two log entries alone do not prove a violation.
- *[Second card]* **A compromised quorum can certify fake credentials** for a requester who never asked,
  and the hospital contract grants. We did not show key release.
- *[Third card]* **Counters can be pushed to a permanent halt:** a checkpoint with a maximum counter
  makes every honest checkpoint stale, and only redeployment recovers.

None of this contradicts the one-fault claims, and none of it is an HMBC vulnerability.

## 22. What RQ2 shows (45 s)

*[Purple card]* The answer to RQ2:
- three of four approvals **and** witnesses that remember what they signed give agreement with at most
  one malicious witness; both parts are needed;
- one witness down still works, two stop it, as intended;
- controlled kills prove the crash test catches a split signing record;
- the replacement rules match the store and catch rule errors;
- the cost is 3.7 to 11 percent more gas;
- and beyond the bound, a compromised quorum can fake credentials or halt the deployment.

*[Green card]* Why it matters: there is no longer a single trusted witness, and we know where safety and
availability end. What stays trusted: the credential issuers, the key worker and the ledgers.

*[Gate line]* As with RQ1's verdict line: **gate F has not been run.** The integrated 32-case study is
still to run; until then these are model, isolated and local results.

## 23. Limitations and lessons (45 s)

*[Left]* Limits: correlated review; synthetic fixtures; a model is not the implementation; offline is
not integrated; the key worker, credential issuers and ledgers are still trusted; symbolic crypto. Even
when F passes, it won't prove consensus, safety with two Byzantine witnesses, liveness under any delay,
or power-loss durability.

*[Right]* Five lessons:
1. A random fault point can look green: put the fault where the bug lives.
2. Check your checks: a scan of a missing directory "passes".
3. Bind by value, not label: the weakened mutant's manifest names the normal profile; only the
   threshold read back on chain tells them apart.
4. Hash the whole artifact.
5. Keep signing rules and ledger rules apart.

## 24. Conclusion (40 s)

- **RQ1 is answered:** in the paper's flow, 20 of 32 rows depend on unspecified details; our repair
  closes each with a named check; gate E passed.
- **RQ2 has a partial answer:** with at most one faulty witness, three-of-four quorums overlap in an
  honest witness; the model, the sweep and isolated tests support it; one witness down still
  certifies, two don't; the cost is 3.7 to 11 percent more gas per signed path. What we **have not
  shown yet** is that RQ1's guarantees survive in the integrated system.
- **Next:** the freeze, the remaining runner stages, the 32 cases, and only then a gate F decision.

*[Banner]* Everything here is about our reconstruction of HMBC, not the authors' code.

## 25. Thank you (5 s)

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
- **"Why does the RQ1 repair still accept a decision just after a revocation?"**
  - The domain chain can't know about a revocation until a checkpoint arrives. The repair bounds that
    window (at most 30 s here); before the repair there was no bound.
- **"Is this a consensus protocol? Is Anvil Byzantine fault tolerant?"**
  - No to both. The witnesses authenticate decisions; the chains are assumed safe, and we say so.
- **"Why 3 of 4?"**
  - Two quorums of three out of four share at least two members, so at least one honest one when only
    one is faulty. The TLC model shows a quorum of two breaks agreement.
- **"Isn't the forged-credential grant a serious bug?"**
  - It needs three of the four witnesses compromised, which is outside the bound we claim. It shows
    what trusting the quorum costs if that trust fails. We recorded it as a security finding; we have
    not designed or tested a mitigation, and it is not a finding about HMBC.
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
| **Profile** | the paper's flow (two readings: paper-strict, paper-minimal), our RQ1 repair (internally repaired-e), the RQ2 quorum profile, or a mutant (one check removed) |
| **Gap / Fix 1, 2, 3** | Decision provenance / trust-list freshness / audit evidence: what the paper leaves open, and our repair for it |
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
