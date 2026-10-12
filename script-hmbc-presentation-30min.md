# Speaker script: the full HMBC deck, long version (≈30 min)

> **Out of date:** written for the earlier 26-slide deck. The current 24-slide deck drops the "where we are" and
> "gate E" slides and uses RQ1/RQ2/RQ3 instead of Phases E/F/G, so slide numbers from 15 on differ. Use
> `script-hmbc-presentation.md` for the talk; this file is only background detail.

About **30 minutes** plus questions. Plain text is what you say. *[Italics in brackets]* are cues for
what to point at or do. "If asked" lines are backup answers, not part of the talk.

- **Slide numbers:** these are PDF page numbers. The counter in the slide corner is one lower, because the
  title page is not counted.
- **Timing:**

  | Part | Slides | Time |
  |---|---|---|
  | The paper | 1–8 | ≈10 min |
  | JANUS, our project and our stack | 9–14 | ≈7 min |
  | Phase E: gaps, method, results, gate | 15–24 | ≈12.5 min |
  | Next | 25 | ≈1.5 min |

- **Suggested speaker split:** three parts, at slides 1, 9 and 15. Each part ends with a transition line
  you can use as a hand-over.
- **If you only have about 20 minutes:**
  - give slides 3, 10, 13 and 17 about 30 s each;
  - skip the table walk on slide 12 and read only its last line;
  - on slide 22, say only the two "honest" lines.

---

# Part 1: The paper (slides 1–8)

## Slide 1: Title (≈20 s)

Hi, we're Team 17: Saiyam, Hemang and Eashaan.

Our project starts from this paper: *"A Hierarchical Multi Blockchain for Fine-Grained Access to
Medical Data"*, by Malamas, Kotzanikolaou, Dasaklis and Burmester, published in IEEE Access in 2020.
I'll call it **HMBC**, for Hierarchical Multi-BlockChain.

Here's the plan for the talk:
- what the paper proposes, and why;
- the authors' later follow-up, JANUS;
- our own project, and the results of its first phase, which is now complete.

*[Point at the picture in the corner.]* That's the paper's architecture. We'll come back to it in a
moment.

---

## Slide 2: Why was this needed? (≈75 s)

Picture a hospital, a medical-device manufacturer, an insurance company and a research lab.

- All of them hold medical data, and sometimes they need each other's data.
- They **don't trust each other**.
- Each one manages its own staff and its own user accounts.

So how do they share data safely? Before this paper there were roughly two options.

*[Point at the bottom-right box, "Cloud".]*
- **Option one: put everything in a shared cloud.** Sharing is easy; that's what "interoperable"
  means here.
- **The catch:** whoever runs the cloud can read the data and can also change the access records.
  You have to trust that operator completely.

*[Point at the top-left box, "Blockchain".]*
- **Option two: a blockchain.** That's a shared ledger that every participant keeps a copy of.
  Nobody can secretly rewrite history, so you get tamper-evident records and no single trusted
  operator.
- **The catch:** existing blockchain systems were mostly built for **one** organisation or domain,
  with fixed queries and fixed membership. They don't connect a hospital to an insurer to a
  manufacturer.

*[Point at the orange box, top-right.]*
- HMBC wants **both**: interoperable access across organisations, without trusting any single party.

*[Point at the "Running example" box.]*
Here's the example the whole paper is built around:
- An emergency doctor from Hospital X needs the full history of a patient whose records sit at
  Hospital Y.
- The doctor should get it **only while on duty**.
- The access must be revocable, and it must be logged.

Keep this example in mind: every mechanism in the next slides is designed for it.

---

## Slide 3: Requirements and prior work (≈75 s)

The paper turns that problem into five requirements.

*[Go down the numbered list.]*

1. **Decentralised trust.** There's no single, global *certificate authority*. A CA is the
   organisation that vouches for identities by signing certificates. Here every hospital runs its
   own CA, and organisations can join or leave.
2. **Fine-grained, temporal access.** Access is decided per role and per domain. It can be
   time-limited, like "on duty", and it can be revoked.
3. **Efficient, private encryption** using **ABE, attribute-based encryption**.
   - Normally you encrypt *for a person*. With ABE you encrypt *for a policy*, like "Doctor AND on
     duty".
   - Anyone whose keys carry those attributes can decrypt.
   - They also want decryption to be light enough for weak devices, and revocation to be cheap.
4. **Decentralised policies**, enforced by **smart contracts**. Those are programs that run on the
   blockchain, so no single party can change the rules or skip them.
5. **Tailored forensics.** Every request, successful or not, is logged globally for later audit.

*[Point at the table.]*
- This is the authors' comparison against eleven earlier schemes; here's a subset.
- Green ticks are properties a scheme has; ticks in brackets are partial.
- HMBC claims all five. By their own count, no earlier scheme covers more than three.
- One honest caveat: this is the **authors' self-assessment**, not an independent evaluation.

> If asked "what are CP-ABE / KP-ABE?":
> - Ciphertext-Policy ABE puts the policy in the ciphertext and the attributes in the user's keys.
> - Key-Policy ABE is the reverse.
> - HMBC uses the multi-authority, ciphertext-policy kind.

---

## Slide 4: Architecture: a hierarchy of blockchains (≈75 s)

Here's the architecture. It has **two layers of blockchains**, hence "hierarchical".

*[Walk the figure top to bottom.]*

- **Top: users.** Doctors, patients and also medical devices, all using one API.
- **The purple chain: the Proxy Blockchain, or PBC.**
  - There is one of these, and **every** organisation runs a node in it.
  - It's the single front door: it registers users, stores everyone's trust lists, and keeps the
    global log.
- **The coloured chains below: Domain Blockchains, or DBCs.**
  - There's one per *type* of organisation: a hospital chain, a manufacturer chain and an insurer
    chain.
  - Each one enforces its own domain's access policy and does the decryption work.
  - Users **never** talk to a domain chain directly; everything goes through the proxy.
- **Bottom: the data layer.** Each organisation keeps its own database **off-chain**, already
  encrypted with ABE. The medical records themselves never go on the blockchain; the chains hold
  rules, logs and the decryption step.

*[Point at the strip of six boxes.]*
Everything is implemented as **six smart contracts**.
- On the proxy chain:
  - **RSC** for registration;
  - **TMSC** for trust management;
  - **PSC**, the proxy and entry point;
  - **LSC** for the global log.
- On each domain chain:
  - **ACSC** for access control;
  - **KSSC**, the key store.

*[Point at the last line.]*
- Each organisation runs one proxy node and one node in its own domain chain.
- The chains are **permissioned**: only approved organisations run nodes.
- They use **Proof-of-Stake** consensus, the mechanism nodes use to agree on which transactions go
  into the ledger.

---

## Slide 5: Trust management and temporal roles (≈90 s)

First problem: with no global CA, how does Hospital Y trust a certificate issued by Hospital X?

*[Point at the two hospital boxes.]*
- Each hospital is its **own CA** and its **own ABE key authority**.
- Each hospital publishes its *trust anchors* on the proxy chain. *[Point at the purple box at the
  bottom.]* There are three of them:
  - its **root certificate (CERT)**, the public key everyone uses to check its signatures;
  - its **certificate revocation list (CRL)**, the certificates it has cancelled;
  - its **temporary access list (TempACL)**, which says who holds a temporary role right now, and
    for what time window.
- Only that hospital's **CA-Admin** can update its own lists.
- The **TMSC** contract checks every credential against the latest lists.

*[Point at User A.]*
- User A is a **Doctor at Hospital X** and a **Researcher at Hospital Y**. Each hospital gives A a
  certificate and a decryption key.
- At registration, the **RSC** gives A **one global ID, the GID**, and links both certificates to
  it.
- **Why the GID matters:** the encryption scheme is the *multi-authority* ABE of Lewko and Waters.
  It only lets keys from different authorities be combined if they were issued to the **same GID**.
  That stops two people pooling their keys to unlock something neither could open alone.

*[Point at the TempACL example line.]*
There are two kinds of role:
- **Long-term roles**, like Doctor, live in the certificate.
- **Temporal roles**, like *on duty*, live in the TempACL with a time window. The 8 am to 8 pm
  window here is our illustrative example.
- A temporal role only counts **together with** a long-term one. Being "on duty" gives nothing if
  you're not a doctor.

*[Point at the green KSSC box.]*
And here's the twist: the **on-duty decryption key is never given to the user**. It stays inside
the KSSC on the hospital chain. Two slides from now we'll see why.

---

## Slide 6: How an access request flows (≈90 s)

Now one complete request. This is the paper's sequence diagram, redrawn. *[Follow the numbers
top to bottom.]*

- **(1)** The doctor sends a request, with their certificate and the ID of the record they want, to
  the proxy contract, **PSC**.
  - The logging contract opens a log entry **right away**, so even a failed request is recorded.
- **(2) and (3)** The PSC asks the **TMSC** to check the credentials against the hospitals' CERT,
  CRL and TempACL. It gets back "valid" plus the verified attributes, for example Doctor and on duty.
- **(4)** The PSC forwards the request to the hospital domain chain: the user's GID, the verified
  attributes and the data ID.
- **(5)** The **ACSC** there checks the hospital domain's policy. If the policy allows it, the
  request goes on to the **KSSC**.
- **(6) and (7)** The KSSC fetches the record from the database. It comes back **encrypted**: the
  ciphertext C.
- **(8)** The KSSC performs **step one** of the decryption with the temporal key. The result, C1,
  is **still encrypted**.
- **(9)** The ACSC logs the transaction on the domain chain and returns C1 to the proxy.
- **(10)** The proxy sends C1 back to the user, and the logging contract stores the full record on
  the proxy chain. The user finishes the decryption with their **own** key.

*[Point at the bottom line.]*
Two takeaways:
- Every hop is logged, on both chains.
- What leaves the domain chain is still unreadable to anyone who doesn't hold the user's long-term
  key.

*(Optional, as a hook for later:)* Notice step 4.
- The domain chain receives "verified attributes" from the proxy.
- But the paper doesn't say how the domain chain checks that they really came from a genuine proxy
  decision.

Keep that in mind: it's gap number 1 in our results, on slide 16.

---

## Slide 7: Key idea: two-step decryption (≈90 s)

This is the core idea of the paper.

**Analogy:** a safe with two locks.
- The hospital's KSSC holds one key: the *on-duty* key.
- The doctor holds the other: the *Doctor* key.
- Neither can open the safe alone.

*[Point at the orange policy box.]*
Technically:
- Patient β's record is encrypted under this policy: *(doctor at Hospital X **and** treating β)
  **or** (a doctor anywhere **and** on duty)*. The second branch is the emergency case.

*[Point at Step 1, then Step 2.]*
- For the emergency branch, the KSSC applies the on-duty key and gets C1.
- The user applies their Doctor key to C1 and gets the record.
- It's the Lewko–Waters multi-authority ABE scheme with its decryption split into two steps,
  prototyped with the Charm crypto library.

*[Go through "Why split it?"]* Why split it?
- **Revocation becomes a list update.**
  - The on-duty key never reaches the user, so ending a duty just means removing the TempACL entry.
  - No key has to be revoked or re-issued, which is normally the expensive part of ABE.
- **The KSSC doesn't have to be fully trusted.** Without the user's long-term key it can't decrypt
  anything on its own.
- **Lighter clients.** The user's device only does the last step, which matters for phones and
  medical devices.
- **No bypass.** If you AND a special "System" attribute into every policy, data can't be decrypted
  outside the system at all.

> If asked "so where do the temporal keys live?":
> - Inside the KSSC, on the domain chain.
> - Their protection rests on the paper's isolation assumption: node operators can't peek inside
>   the contract.
> - Because of the AND in the policy, a leaked temporal key alone still isn't enough to decrypt.

---

## Slide 8: Results: prototype performance (≈75 s)

The authors built a prototype:
- a private Ethereum chain, using Ganache and Truffle;
- the six contracts written in Solidity;
- the Charm library for the cryptography;
- everything containerised with Docker and Kubernetes;
- all on one 12-core machine.

The chain ran Proof-of-Stake at about 1000 transactions per second, with roughly 12-second blocks.

*[Point at the bar chart.]*
This is their Table 4: the time for one data access, averaged over 100 concurrent requests.
- **603 ms in total.**
  - 527 ms is spent in the smart contracts. The KSSC is the largest at 132 ms, since it does the
    partial decryption.
  - 2 ms is the cache.
  - 74 ms is the user's final decryption, measured on a simulated low-end device.
- **Why don't 12-second blocks add 12 seconds?** Only the transaction *hash* has to be stored on
  the proxy chain, so a transaction can complete before its block is confirmed.

*[Point at the line chart.]*
- **Scaling:** total decryption time grows roughly linearly with load, from about 1 second at 30
  concurrent requests to 3–4 seconds at 100.
- **Versus one-step ABE:** decryption time also grows with the number of attributes. The two-step
  version is slightly slower overall than ordinary one-step ABE, but the user's share of the work is
  smaller.

*[Point at the orange box.]*
How should we read this?
- The security part of the paper is an **informal argument**, not a proof.
- It rests on assumptions:
  - isolation holds;
  - an honest majority runs every chain;
  - the cryptography is secure;
  - keys are never compromised;
  - the attacker has bounded computing power.
- The measurements come from one machine without network delays. The authors themselves say
  larger-scale studies are needed.

> If asked about "3–4 seconds":
> - The paper's text says about 3 seconds for that setting.
> - Its own plotted curve for two KSSC and two user attributes reaches about 4 seconds.

**Transition:**
So that's HMBC: a clean design and a single-machine prototype, with security argued under fairly
strong assumptions. Two years later, the same group built a full implementation called **JANUS**.
Here's what it added and what it changed. *[Next slide / hand over.]*

---

# Part 2: JANUS, our project and our stack (slides 9–14)

## Slide 9: JANUS (2023): what it adds on top of HMBC (≈60 s)

JANUS is the follow-up:
- the same authors, together with the security company CENSUS;
- published in Applied Sciences in 2023;
- a working, open-source system built on HMBC's ideas.

*[Walk the stack on the left, top to bottom.]*
- A desktop app, with the user's own key vault.
- A frontend API, where each organisation logs its users in through its **own** certificate
  authority.
- The proxy chain and the domain chain, now on **Hyperledger Fabric**, a permissioned blockchain
  platform.
- Between the chains, message queues and a voting service.
- At the bottom, a key vault holding a **domain key**, and the database.
- Every component runs in its own Kubernetes pod.

*[Go through the right column.]* Four things are new:
1. **A formal access model, HMBAC.** It is built from sets and relations, with three checks:
   - attributes are verified on the proxy chain;
   - authorisation happens on the domain chain;
   - decryption happens on the domain chain.
2. **The single access point is enforced by cryptography.**
   - Every policy gets an extra AND with a domain key that only the KSSC can derive, inside the vault.
   - That's how they make HMBC's "System" role from slide 7 real.
   - Records are encrypted with fast AES. ABE only protects the AES keys.
3. **Engineering:** queues with throttling, so the chains don't get flooded; voting for joins, leaves
   and policy changes.
4. **Evaluation:**
   - attack trees;
   - load tests from 2 to 300 concurrent requests on cloud servers: time grew linearly, with no
     failed requests.

---

## Slide 10: JANUS vs. HMBC: what changed, and why (≈75 s)

*[Walk the rows; you don't need to read every cell.]*

- **Platform.** JANUS moved from a private Ethereum chain to Hyperledger Fabric with Raft ordering:
  a practical permissioned deployment that others can reproduce.
- **Contracts.** Five instead of six. The registration contract is gone, because login goes through
  each organisation's own CA.
- **The KSSC key.** In HMBC the KSSC holds the *temporal* keys, like on-duty. In JANUS it holds a
  *domain* key, derived per user inside the vault, so that every decryption has to go through the
  system.
- **Temporal roles.** This row is our own reading:
  - in JANUS the user holds both the doctor key and the on-duty key, and the duty is checked online;
  - so ending a duty depends on that online check, whereas in HMBC the key itself is withheld.
- **Key storage, chain-to-chain messaging and governance:** off-the-shelf parts (a vault, queues)
  and a concrete voting manager, where HMBC only said "majority consent".

*[Point at the orange box.]*
What JANUS itself leaves open:
- **Raft tolerates crashes, not malicious nodes.** Byzantine tolerance is left as future work.
- **Isolation and an honest majority are assumed.**
- **There is no key rotation and no key epochs.**

Those three open points line up with our three research questions.

One scoping note: we use JANUS **only as context**. Our project implements HMBC 2020; we don't use
JANUS code or import its claims.

---

## Slide 11: Our project: three research questions, answered in order (≈75 s)

We ask three research questions, and each one is a phase: **E, F and G**.

*[Point at each card.]*
- **RQ1, Phase E: authorisation, freshness and audit.** Which properties follow from HMBC's access
  flow? Which depend on details the paper leaves out? And which explicit repairs enforce them?
- **RQ2, Phase F: Byzantine operators.** If some operators, the relay or the witnesses misbehave,
  which RQ1 guarantees survive? What quorum and state rules are enough?
- **RQ3, Phase G: key lifecycle.** What stays confidential after revocation, after someone joins,
  or after a later key compromise, with an explicit key-epoch lifecycle?

**Why this order:**
- E builds the request IDs, the authorisation checks and the test harness that F needs.
- F decides *whose approval* releases a key, and G needs that.
- G comes last because secrecy claims need real ciphertexts and real keys.

*[Point at "Method".]*
- **A reconstruction.** The authors' code isn't available, so we built a **paper-derived
  reconstruction**.
  - Wherever the paper is silent, we make an explicit, recorded choice.
  - Such a choice is never presented as a vulnerability we "discovered".
- **Profiles.** Every case runs in several *profiles*: two readings of the paper, our repaired
  version, and deliberately broken *mutants*.
- **Labels.** Every result gets one label, like SUPPORTED or SPEC_GAP. I'll explain them in Phase E.

*[Point at "Team setup".]*
- **Three modules:** the ledger (the contracts), the protocol (client, relay, witness, key worker)
  and the evaluation (runner, independent checker, formal models).
- **Three machines**, synchronised through Git and a frozen, hash-pinned interface, so the modules
  could be built in parallel.
- **Gates.** Each phase ends with a gate: all three module owners must sign off on the same evidence
  before the next phase starts.

---

## Slide 12: Why this direction: HMBC's gaps and the literature (≈90 s)

This table says, for each research question:
- what HMBC leaves open;
- what the literature already covers;
- what our angle is.

*[RQ1 row.]*
- **What HMBC leaves open:**
  - The domain chain receives "verified attributes", but nothing binds its grant to the proxy chain's
    decision.
  - Trust lists are "the latest", with no versions.
  - Outcomes are logged without evidence from the domain chain.
- **What the literature covers:**
  - It is known in general that cross-chain messages need some trusted party (Zamyatin and others,
    Financial Crypto 2021).
  - Typed, domain-separated signatures and nonces are standard practice: EIP-712 on Ethereum.
- **Our angle:** an *executable* analysis of HMBC's own flow, comparing paper and repaired versions,
  with mutants and a formal model.

*[RQ2 row.]*
- **What HMBC leaves open:** HMBC's security assumes an honest majority; consensus is just "Proof of
  Stake", with one trusted message path.
- **What the literature covers:** Byzantine fault-tolerant ordering for permissioned chains exists
  (Sousa, Bessani and Vukolić, DSN 2018), and JANUS defers it.
- **Our angle:** we don't swap the consensus. We ask which RQ1 guarantees survive one faulty witness
  in a 3-of-4 quorum.

*[RQ3 row.]*
- **What HMBC leaves open:** revocation is only gatekeeping: keys are withheld or lists updated.
  There are no key epochs, and plaintext already decrypted stays usable.
- **What the literature covers:**
  - multi-authority ABE (Lewko–Waters);
  - outsourced decryption (Green, Hohenberger and Waters);
  - revocable, forward-secure schemes.
- **Our angle:** measure what this mediated design loses, using real ABE.

*[Point at the last line.]*
Our search wasn't exhaustive, but we found **no published instance-level security analysis** of
HMBC or JANUS. The general results in the middle column are cited, not claimed as ours.

---

## Slide 13: Tech stack: the paper, JANUS, and ours (≈60 s)

*[Point at the orange column; compare across rows only where it helps.]*

- **Chains:** two local **Anvil** chains, a fast local Ethereum node. One is the proxy chain, one is
  the hospital domain chain.
- **Contracts:**
  - the paper's six contracts, plus a **DecisionVerifier**, written in Solidity;
  - built and tested with Foundry.
- **Consensus:** none. These are local development chains, and we don't claim otherwise. Phase F
  adds a 3-of-4 *witness* quorum, which is not a consensus protocol.
- **Chain to chain:**
  - an **untrusted** Python relay carries the messages;
  - what makes them trustworthy is that requests, decisions and receipts are **signed** and checked
    on chain.
- **ABE:**
  - in RQ1 we use a *symbolic* adapter, because RQ1 is about authorisation, not encryption strength;
  - real Charm / Lewko–Waters ABE comes in Phase G, after its own gate.
- **Secrets:** an off-chain key worker with a durable log. The contracts hold no secrets.
- **Evaluation:**
  - Forge tests plus mutants;
  - an independent Python checker;
  - ProVerif for the protocol model;
  - TLA+ later, for F and G.

---

## Slide 14: Why this stack: what we keep, and what we change (≈60 s)

*[Walk the diagram.]*
1. The **client** signs a request and sends it to the proxy chain.
2. A **witness** reads the proxy chain and signs what it saw.
3. The **relay**, which we treat as untrusted, forwards everything to the domain chain.
4. The domain chain verifies the signatures before it grants anything.
5. The **key worker** then releases the key.
6. The **evaluator** watches all of it from the outside.

*[Point at "Kept".]* What we **kept**, to stay faithful to HMBC 2020:
- Ethereum-style contracts in Solidity, with the paper's six contracts;
- separate proxy and domain chains;
- the paper's own ABE library for RQ3;
- secrets in an off-chain key service.

*[Point at "Changed on purpose".]* What we **changed on purpose**:
- **Foundry/Anvil**, because Ganache and Truffle were discontinued in 2023.
- **No Fabric, Kubernetes or Vault.** We study the paper's design, at laptop scale.
- **An untrusted relay with signed messages**, so trust is explicit and checked on chain.
- **No consensus claims.** RQ2 studies witness quorums instead.
- **Security evidence, not throughput.**

**Transition:**
That's the setup. Now the first phase, **Phase E**, which is complete: what we found, how we tested
it, and what it means. *[Next slide / hand over.]*

---

# Part 3: Phase E, RQ1 (slides 15–24)

## Slide 15: Phase E (RQ1): where we are (≈60 s)

Phase E answers RQ1. *[Point at the italic question.]* Notice the three verbs:
- which properties **follow** from the paper;
- which **depend** on details it leaves out;
- which **repairs** enforce them.

*[Walk the timeline left to right.]*
- **E0, 6 to 8 October.**
  - We froze the interface between our three modules, and a catalog of **56 test cases**.
  - The catalog includes the *expected result of every case*, written down **before anything ran**.
  - So we can't bend the expectations to fit the results.
- **E1, 8 October.** The legitimate flow worked end to end, 9 out of 9 controls, in all three
  profiles:
  - Alice, a doctor, gets access;
  - Bob, without the role, is denied;
  - a CA admin can't change another hospital's list.
- **E2, 9 to 11 October.** We ran ten slices of test cases. Each was frozen, run live on two
  chains, and reviewed.
- **E3, 12 October.** One command re-ran all 56 cases plus the formal model, and **gate E passed**.

*[Point at "we are here".]* Next is Phase F, then G.

*[Go through the four tiles.]*
- **56 out of 56:** every case gave exactly the result we froze in advance.
- **20 of 32:** in the two paper profiles, 20 cases depend on a detail the paper doesn't specify.
- **19 of 24:** in our repaired profile, 19 cases are enforced by a check we added. The other 5 are
  controls.
- **Zero:** we claim **no exploit** of HMBC. The next slide explains why.

---

## Slide 16: The gaps: what HMBC's access flow leaves unspecified (≈80 s)

This is the paper's flow again, simplified. The orange circles mark the three places where the paper
is underspecified.

*[Point at circle 1, on the purple arrow.]*
- **Gap 1: decision provenance, case family E01.**
  - The proxy chain makes the decision. What reaches the domain chain is a tuple forwarded by a relay:
    the GID, the attributes and the data ID.
  - The paper doesn't say how the domain chain knows:
    - **who** it's for: could the relay swap the user?
    - **which chain** it's meant for;
    - **when** it expires;
    - whether it's a **replay**.

*[Point at circle 2, between the proxy chain and the CA admins.]*
- **Gap 2: trust-anchor freshness, E02.**
  - Trust lists are simply "the latest", with no version numbers and no expiry. So what stops someone
    re-installing an older, correctly signed list from before a revocation?
  - And when must a revocation on the proxy chain take effect on the domain chain?

*[Point at both circles 3.]*
- **Gap 3: audit correspondence, E03.**
  - After the key is released, an outcome is logged back on the proxy chain. Nothing requires
    evidence from the domain chain for that outcome.
  - The paper is silent about a crash between releasing the key and logging it.

*[Point at the "Framing" box.]* One point about framing:
- HMBC assumes its components are **securely isolated**. Under that assumption, a misbehaving relay
  simply doesn't exist.
- So these are not attacks on HMBC. They are **specification dependencies**: the security of a real
  implementation depends on how it fills these gaps.
- Our job is to test what different reasonable fillings give, and what an explicit repair adds.

> If asked "isn't that just saying the paper is incomplete?":
> - Yes, but made precise: which property depends on which missing detail, shown by a test you can run.
> - We mapped 37 passages of the paper to properties, and recorded 41 explicit choices where it is
>   silent.

---

## Slide 17: Method: the paper and our repair on one frozen catalog (≈80 s)

*[Left column, the four boxes.]* The same six contracts are deployed in four **profiles**:
- **paper-strict:**
  - the paper's own rules about who may call what, and signed trust lists;
  - where the paper is silent, we take the safest reading.
- **paper-minimal:** the same, but the list signature isn't checked on chain. It's another reasonable
  reading.
- **repaired-e:** our extension, on the next slide. It is **not** HMBC.
- **The mutants:**
  - our repaired version with **exactly one check removed**; there are six of them;
  - if our tests don't notice a missing check, the tests are worthless.

*[Right column, steps 1 to 5.]* How each result is produced:
1. **Source map.** The paper's passages are mapped to properties, and every gap gets a recorded
   choice.
2. **Catalog.**
   - 16 case schedules in each of the 3 profiles, plus 8 cases that only make sense in the repaired
     version: **56 rows**.
   - The expected result of each row was frozen on 8 October.
3. **Every row runs on a fresh pair of chains.**
   - The controls run first: Alice allowed, Bob denied, wrong CA admin rejected.
   - So a profile that simply denies everything can't pass.
   - Then the case itself runs.
4. **An independent checker.** It is separate code that reads both chains and decides the result. It
   doesn't reuse the contracts' logic, so a bug in a contract can't hide itself.
5. **Discipline.**
   - We freeze the plan's hash, the module owners acknowledge that exact hash, we run, then we
     review.
   - Failed trials are **kept**. For example, one early replay run failed on timing; it stays in the
     record, and the re-run needed a new freeze.

*[Bottom left, the four labels.]* Every row gets one label:
- **SUPPORTED:** follows from the paper as we reconstructed it.
- **SPEC_GAP:** depends on a detail the paper leaves open.
- **REPAIR_SUPPORTED:** our repair enforces it.
- **BLOCKED:** it can't be decided from the paper at all.

---

## Slide 18: What we built: the repaired-e profile (≈80 s)

*[Top row, left to right.]* The repaired flow:
1. The user **signs** the request.
2. The proxy chain logs it and checks the credentials.
3. A **witness** signs a state checkpoint and a decision. The witness is a separate service that
   reads both chains.
4. The domain chain runs **13 checks**, and uses the request's nonce exactly once.
5. The grant is issued.
6. The key worker records its intent durably, *then* sends.
7. A signed receipt lets the outcome be logged.

*[The three cards.]* Each case family gets its own fixes.

- **E01, "who, where, when, once":**
  - The user and the witness sign typed messages. **EIP-712** is the Ethereum standard for this.
  - Each signature is bound to one specific contract on one specific chain, so it can't be reused
    anywhere else.
  - Each request has a single-use nonce and lives at most 30 seconds.
- **E02, fresh trust state:**
  - Trust lists get **version numbers and expiry**, so an older list is refused.
  - **Signed checkpoints** carry a sequence number and an auth epoch.
  - Once the domain chain accepts a checkpoint taken after a revocation, every older decision is
    stale. That's our **revocation barrier**.
  - Duty validity is checked at the moment of use.
- **E03, evidence for every outcome:**
  - An outcome needs a **witness-signed receipt** for the same request.
  - The key worker logs its intent before sending. A retry re-sends the cached response; it never
    creates a new one.

*[The numbered strip.]*
- This is the on-chain **DecisionVerifier**: 13 checks in a fixed order.
- Because the order is fixed, a certificate with several defects always gets the same error code, so
  the results are reproducible.
- The colours match the families above. Step 12, the key epoch, is reserved for Phase G.
- The contracts hold no secrets: keys live in the off-chain worker.

> If asked "isn't the witness just a new trusted party?":
> - Yes. In Phase E there is **one trusted** witness, and we say so.
> - The paper's isolation assumption trusts the relay *implicitly*. We make that trust explicit and
>   checkable on chain.
> - Removing the single trusted witness is exactly what Phase F does.

---

## Slide 19: Results E01: decision provenance and replay (≈80 s)

How to read the table:
- each row is something a misbehaving relay does;
- the middle column is what the two paper profiles do;
- the right column is what our repaired profile does.

*[Go down the rows.]*
- **Replaying an identical request.**
  - It's rejected even in the paper profiles.
  - *[Point at the footnote.]* But only because our reconstruction makes the grant ID deterministic.
    That's one of our recorded choices, not something the paper specifies.
- **Swapping the subject.** The paper profiles grant it, and the response goes to the *swapped*
  user. Repaired: `WRONG_SUBJECT` at step 4, because the signed request binds the user.
- **Forging a tuple with no proxy request at all.** The paper profiles grant it. Repaired:
  `BAD_SIGNATURE` at step 6.
- **Replaying under a new reference.** The paper profiles give a second grant. Repaired: `REPLAY`.
- **Reusing a nonce for a different request.** This case only exists in the repaired version:
  `REPLAY`.
- **Delivering deployment B's tuple to deployment A.** The paper profiles grant it. Repaired:
  `WRONG_DESTINATION` at step 1.
- **Delivering exactly at the expiry instant.**
  - The paper profiles grant it at that instant.
  - Repaired: `EXPIRED`, because expiry is exclusive: at the expiry time, it's already expired.

*[Point at "What it means".]*
- In the paper profiles, the domain chain grants **any well-formed tuple** the relay forwards.
- The repaired version rejects each case at a **named** check, and Alice's legitimate access still
  works in every row.

*[Point at the small print.]* Again, these cases assume a misbehaving relay, which HMBC's isolation
assumption excludes.

---

## Slide 20: Results E02: trust-anchor freshness and the revocation window (≈80 s)

*[Go down the table.]*
- **A CA admin updating another hospital's list** is rejected in every profile.
  - That's the paper's own caller restriction: the baseline, not our repair.
  - It's good to see a SUPPORTED result: here the paper *does* specify the rule.
- **Re-installing an older signed revocation list.**
  - The paper profiles accept it, because "latest" just means "last appended". The effect is that **a
    revoked credential is un-revoked**.
  - Repaired: `STALE_ANCHOR`, because versions must go up.
- **Revoking, then using a decision before the domain chain has seen a new checkpoint.**
  - Both accept it.
  - In the repaired version that's deliberate: the domain chain can't know about a revocation that
    hasn't reached it yet. What matters is that this window is **bounded**.
- **Using the decision after the checkpoint.** The paper profiles still accept it, because there is
  no barrier. Repaired: `STALE_STATE`.
- **A duty that has ended at delivery time.** The paper profiles grant it at that instant. Repaired:
  `EXPIRED`.

*[Point at the chart.]* How long is that window? The experiment:
- revoke Alice at time T0;
- try her already-collected decision in every block until it's refused.

The results:
- **Along the bottom:** how long until the domain chain accepts the next checkpoint: 0, 5, 10 or 20
  seconds, or never.
- **The bars:** the window is about one block longer than that delay: 2, 6, 11 and 21 seconds.
- **With no new checkpoint at all:** the decision is refused at the request's own expiry, after 26 or
  27 seconds.
- **The red line:** the 30-second request lifetime caps every case.

So in the repaired profile the window is the smaller of the checkpoint delay and the lifetime left,
**at most 30 seconds**. In paper-strict there's **no bound**: the decision was still grantable 65
seconds later.

*[Point at the small print.]* We ran this on two machines and got the same results. It's the module
owners' measurement, one trial per delay, and it was not part of the final gate run.

---

## Slide 21: Results E03: audit correspondence and crash recovery (≈75 s)

*[Go down the table.]*
- **The same outcome reported twice** is rejected everywhere. "One outcome per request" is our
  reconstruction choice.
- **The relay drops the outcome.**
  - The request stays **PENDING** on the proxy chain, visibly and forever. The repaired version also
    keeps durable evidence at the worker.
  - We don't claim it fixes itself: reconciling it needs eventual delivery and an honest reporter.
- **A fabricated outcome, with no grant at all.** The paper profiles record it. Repaired:
  `WRONG_PROFILE`, because there's no way to log an outcome without a receipt.
- **A receipt that names a different request, user or record.** Repaired: `WRONG_SUBJECT`, and
  nothing is recorded. We test this with a deliberately misbehaving test witness.
- **The key worker crashes after logging its intent, or after sending.**
  - The paper says nothing about durability, so this is **BLOCKED**. It's never counted as a pass,
    and never as a finding.
  - In the repaired version, a restart re-sends the **same** cached response: one grant, one outcome.

*[Point at the diagram.]* The two crash points are marked in red:
- **Before the grant expires,** a retry gives the same response again, never a second key release.
- **After it expires,** the answer is `EXPIRED`, and nothing changes.

*[Point at the last bullet.]* And one point about honesty:
- A grant is **permission** to release a key. It is **not proof of delivery**.
- So delivery stays "unknown", and we report it that way.
- Our crashes are simulated process deaths, not power loss.

---

## Slide 22: Are the checks real? Mutants and a formal model (≈75 s)

How do we know these checks actually matter, and that the tests aren't just passing? We use two
methods.

*[Left table.]* **Mutants: remove one check, and something must fail.** Each row gives:
- the mutant;
- the ledger test that fails;
- the gate row that hits exactly the guard this mutant removes.

The results:
- **All 6 mutants are detected** by the ledger's mutant test suite. We re-ran it on 12 October and
  got identical output.
- **One subtle case: no destination binding.** In the wrong-destination test, step 1, the source
  check, fires before step 2, the destination check. So this mutant can only be caught by the unit
  tests and by ProVerif.
- **Honest limit:** the full live mutant run on the integrated two-chain system was **not done**.
  This gate criterion rests on the test suite, the formal model and the 8 guard rows, and we say so.

*[Right side.]* **ProVerif** checks security properties of a protocol *model*, against an attacker
who controls the network.
- **The question:** does every grant agree with what the user requested *and* what the witness
  approved, on all 8 fields? The fields are request ID, subject, data, source, destination, action,
  policy and nonce.
- **The answers:**
  - **Repaired:** true.
  - **The mutant that drops the destination:** false, with an attack trace that grants for a
    different destination. The other 7 fields still agree.
- **Sanity checks:**
  - a legitimate grant is reachable, so the model isn't vacuously true;
  - a policy-denied grant is unreachable.
- **Limits:**
  - it's a symbolic model with perfect signatures;
  - it doesn't model replay, expiry or revocation; the live tests cover those.

> If asked "why wasn't the live mutant run done?":
> - Our agent tooling's safety check stopped the automated run.
> - The team chose not to force it. Instead the criterion was scoped to the evidence above, and the
>   run is recorded as "not run", not as passed.

---

## Slide 23: Gate E: one command, 56 rows, a recorded verdict (≈60 s)

*[Point at the squares.]* Every one of the 56 rows is one square, coloured by its result.

- **On the left, the two paper profiles, 32 rows:**
  - 8 blue: supported;
  - 20 orange: they depend on a gap;
  - 4 gray: the blocked crash rows.
- **On the right, the repaired version, 24 rows:**
  - 19 green: our repair enforces the property;
  - 5 blue: controls.
- Every orange case on the left has a green row on the right.
- And all 56 matched the frozen expectation: **zero refuted, zero failed**.

*[Right column.]* **The run:**
- one command, on 12 October;
- every row on fresh chains, then the formal model;
- about 1.3 hours, with 112 services started and stopped;
- exit code 0;
- the source code and the Git commit identical before and after, and everything hashed.

**The verdict:**
- all 9 gate criteria met, with the mutant criterion scoped as on the previous slide;
- three matching sign-offs, from the ledger, protocol and evaluation owners, on the same report and
  the same hashes;
- **gate E passed** on 12 October.

*[Point at "Honest caveat".]*
- For the last three days, the protocol and evaluation agents were offline: they hit usage limits.
- The ledger agent finished the phase with stand-in agents running the **same model**.
- So those final reviews are **correlated, not independent**. The original owners can re-open any
  part.

---

## Slide 24: What Phase E shows, and why it matters (≈75 s)

*[Orange card, "Answer to RQ1".]*
- **Holds as the paper specifies:**
  - identical replay is rejected;
  - a duplicate outcome is rejected;
  - list updates are restricted to the issuer;
  - a dropped outcome stays visible.
- **Depends on the paper's gaps:** 10 case schedules, from subject swaps and forged tuples to list
  rollback, revocation and fabricated outcomes, plus crash recovery.
- **Repairable:** each one gets a named, explicit check, and legitimate access keeps working.

*[Green card, "Why it matters".]*
- **For anyone implementing HMBC:** a concrete list of the decisions the paper leaves open, each
  with a test that shows what happens if you get it wrong.
- **Revocation gets a bound:** at most 30 seconds, where the paper profile has none.
- **A reusable harness:** one frozen, one-command run of 56 rows that Phases F and G must keep
  passing.
- **To our knowledge,** this is the first executable, instance-level analysis of HMBC.

*[Gray card, "Limits we state".]*
- **Symbolic crypto:** no claim about ABE secrecy or performance.
- **Trusted components:** one trusted witness, and one trusted key worker.
- **Local chains:** no consensus; one host; one trial per row.
- **Not run:** the integrated mutant run and the integrated revocation window.
- **Correlated review:** the final reviews were done by the same model.

*[Point at the banner.]*
- The repaired version puts all decision trust on **one witness**.
- So the natural next question is: what survives when the witnesses themselves can be malicious?

---

## Slide 25: Next: Phase F (RQ2), then G (RQ3) (≈75 s)

*[Left diagram.]* Phase F, Byzantine operators.
- **The setup:**
  - in Phase E there's one trusted witness;
  - in F there are **four**, one per hospital;
  - a decision needs **3 of 4** signatures, and we tolerate **one** faulty witness: the red W4.
- **Why 3 of 4 works:**
  - any two quorums of three share at least two witnesses;
  - with at most one faulty witness, at least one *honest* witness is in both;
  - an honest witness never signs two conflicting decisions;
  - so two conflicting decisions can't both reach a quorum.

*[The numbered list.]* The plan:
1. **F0: freeze the fault model first.**
   - Four witnesses, quorum three, one fault.
   - A trust matrix over every component.
   - The expected results agreed **before** running anything, the same discipline as Phase E.
2. **Ledger:** a quorum verifier, plus governance certificates that need distinct signers and are
   bound to an action, a nonce and an expiry.
3. **Protocol:** four independent witnesses. Each stores its first signed decision, so it can't
   equivocate.
4. **Evaluation:**
   - runs with 0, 1 and 2 faulty witnesses, equivocation, withholding, stale views and a compromised
     key worker;
   - a TLA+ model checked with TLC;
   - and Phase E's 56 rows re-run as a regression test.

This is a decision-authentication layer, **not** a new consensus protocol, and we won't claim one.

*[Right side.]* After that, **Phase G**, the key lifecycle:
- **A gate first:** a real multi-authority ABE adapter, using Charm with Lewko–Waters, with the
  correct split between the KSSC and the user.
- **Secrecy:** what stays secret after revocation, after someone joins, after a later key
  compromise, and for cached outputs.
- **Cost:** measured encryption, decryption and key-rotation cost.
- **Key epochs:** prepare a new epoch, commit it on chain, then retire the old one.

**Status:** we're at F0, the planning step. Nothing in F has been built yet.

---

## Slide 26: Thank you (≈10 s)

Thank you. We're happy to take questions.

---

# Q&A backups (Phase E)

> **"So did you find vulnerabilities in HMBC?"**
> - No. We claim none.
> - The gaps are places where the paper is underspecified. Every stress case uses a misbehaving relay,
>   which HMBC's isolation assumption rules out.
> - What we show is *which* properties depend on *which* missing details.

> **"Isn't 56/56 just testing against your own expectations?"**
> - The expectations were frozen before any run.
> - The checker is separate code that reads both chains; it doesn't reuse the contract logic.
> - Failed attempts are kept on record. One replay run failed on timing, and one runner had a bug
>   that all reviewers missed. Both are kept.
> - And "matching" includes SPEC_GAP and BLOCKED results, not only passes.

> **"Why does the repaired version still accept a decision right after a revocation?"**
> - The domain chain can't know about a revocation until a checkpoint reaches it.
> - The repair doesn't make that zero; it **bounds** it, at most 30 seconds in our setting.
> - Before the repair, there was no bound at all.

> **"Why no real encryption in Phase E?"**
> - RQ1 is about who is allowed to get a key and what gets logged, not about the strength of
>   encryption.
> - Real ABE comes in Phase G, behind its own gate.
> - Until then, we make no secrecy or performance claim.

> **"Why one trial per row? Where are the statistics?"**
> - These are correctness checks with deterministic expected outcomes, not performance measurements.
> - The timing numbers are single samples on one host, and we say so.

> **"What's the cost of the repairs, for example in gas?"** Not measured in RQ1. Phase F reports the
> certificate, gas and latency overhead.

> **"Why Anvil and not a real consensus network?"**
> - RQ1 studies the access protocol and assumes the ledgers are safe. We state that assumption
>   explicitly.
> - Anvil is a deterministic local chain; we don't claim consensus properties for it.

> **"What does 'correlated review' mean here?"**
> - The final reviews were done by agents running the same model as the author of the work.
> - So the same blind spots could pass unnoticed.
> - The original module owners can re-open any of it, and that would re-open the gate.

> **"What does ProVerif actually prove?"**
> - In a symbolic model with perfect signatures, every grant matches the user's request and the
>   witness's decision on all 8 fields.
> - It does not cover replay, expiry, revocation or the real signature encoding. The live tests cover
>   those.

---

# Mini-glossary (for Q&A)

| Term | Meaning |
|---|---|
| **Blockchain** | A ledger copied across many parties, so past entries can't be secretly changed. |
| **Permissioned chain** | Only approved organisations run nodes. |
| **Proof-of-Stake** | A consensus method: how nodes agree on the next block. |
| **Smart contract** | A program stored and run on the blockchain. Everyone sees the same code and result. |
| **CA / certificate** | A signed statement, "this public key belongs to this user, with these roles". |
| **CRL** | The list of certificates an authority has cancelled. |
| **TempACL** | The paper's signed list of temporary role assignments with time windows. |
| **ABE** | Attribute-based encryption: you encrypt for a policy over attributes, not for a person. |
| **MA-CP-ABE (Lewko–Waters)** | ABE with many independent key authorities; keys combine only under one GID. |
| **GID** | A user's global identifier across all authorities; it prevents key pooling (collusion). |
| **PBC / DBC** | The proxy blockchain (shared front door) and the domain blockchains (one per organisation type). |
| **RSC / TMSC / PSC / LSC** | Registration, trust management, proxy/entry and logging contracts on the PBC. |
| **ACSC / KSSC** | Access-control and key-store contracts on each DBC. |
| **JANUS** | The authors' 2023 open-source follow-up on Hyperledger Fabric. Context only; not used in our code. |
| **Paper-derived reconstruction** | Our implementation built from the paper's text, with every missing detail recorded as an explicit choice. |
| **Profile** | One configuration of the same contracts: paper-strict, paper-minimal, repaired-e, or a mutant. |
| **Mutant** | The repaired version with one check deliberately removed, to prove the tests notice. |
| **SUPPORTED / SPEC_GAP / REPAIR_SUPPORTED / BLOCKED** | Follows from the paper / depends on a missing detail / our repair enforces it / undecidable from the paper. |
| **Relay** | The service that carries messages between the chains; we treat it as untrusted. |
| **Witness** | A service that reads both chains and signs checkpoints, decisions and receipts. One trusted witness in E; four, with a quorum, in F. |
| **Checkpoint / revocation barrier** | A signed snapshot of the proxy chain's state; once the domain chain accepts a newer one, older decisions are stale. |
| **Nonce** | A number used once, so the same request can't be replayed. |
| **EIP-712** | The Ethereum standard for signing typed data, bound to one contract on one chain. |
| **DecisionVerifier** | Our on-chain contract that runs the 13 checks in a fixed order. |
| **GrantReceipt** | A witness-signed receipt proving a grant existed; needed to log an outcome in repaired-e. |
| **Key worker** | The off-chain service that holds keys and releases them after a grant; it logs its intent before sending. |
| **Anvil / Foundry** | A local Ethereum node and the Solidity build-and-test toolkit we use. |
| **ProVerif** | A tool that checks security properties of a protocol model against a network attacker. |
| **TLA+ / TLC** | A specification language and its model checker, used in F to explore all fault interleavings. |
| **Quorum (3 of 4, f = 1)** | A decision needs 3 of 4 witness signatures; the design tolerates one faulty witness. |
| **Gate** | The end-of-phase check: one frozen run plus three matching sign-offs before the next phase starts. |
