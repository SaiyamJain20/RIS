# R2-DESIGN - Ledger-enforced global privacy-budget accounting for statistical access in HMBC2020

Agent R2-DESIGN, 2026-10-04. Status: COMPLETE. About 5,000 words, which is over the ~3,500 target; most of the excess is in the tables. Nothing was run locally. Every RAM, time and size figure is an estimate to be measured in W1.

Inputs read: BRIEF.md (incl. Sec. 8), G2_mpc_dp.md (all), A1_dissection.md (GC1/GC3/GC4 + coverage matrix), G6_hierarchy_trust.md (trust/capture parts), papers/hmbc2020.txt (III-D, Fig. 6 flow, III-F, IV-A/B, V-A).

**Verdict up front.** Viable, but with one structural caveat the team must accept: **secure aggregation (the "MPC") buys DP utility only if hospitals bound a patient's TOTAL contribution across sites, which needs cross-hospital linkage** (common patient ID + PSI). Without linkage, the sound noise level equals sound *local* noise per hospital, and MPC then only protects institution-level aggregates. The design below therefore has a *linked* mode (main) and an *unlinked* mode (fallback), and the gap between the two is itself a measured result. Newly verified this session: Kairouz-Liu-Steinke, Distributed Discrete Gaussian, ICML 2021, arXiv:2102.06387 (OPENED abstract); Agarwal-Kairouz-Liu, Skellam mechanism, NeurIPS 2021, arXiv:2110.04995 (OPENED, "closed under summation"); Feldman-Zrnic, Rényi filter, arXiv:2008.11193 (OPENED); Dong-Roth-Su, Gaussian DP, arXiv:1905.02383 (OPENED). Not re-opened (cite only after checking): Bun-Steinke zCDP (arXiv:1605.02065), Canonne-Kamath-Steinke discrete Gaussian (arXiv:2004.00010), Bonawitz et al. secure aggregation (CCS 2017), Besu QBFT docs.

## 1. Problem and contributions

**Problem.** HMBC2020 says statistical access is safe because "all access is controlled and logged by the PBC" (III-F-2). Logging is not disclosure control. JANUS code returns raw per-hospital counts (A1, row h). The goal is this: for every patient P, the total privacy loss to the **union of all queriers**, across all hospitals, authorities and time, stays at most B. This must hold with no trusted curator, with autonomous custodians, and with principals whose GIDs come from independent CAs that can each mint GIDs.

| # | Claim | What is new compared with the closest prior art (G2 table) |
|---|---|---|
| C1 | **Five natural accounting designs that fit HMBC are unsound or DoS-able**: per-hospital (A1, overlap), per-hospital-set (A2, subset differencing), per-GID (A3, Sybil across authorities), unbound receipts (A4, replay) and a global budget without quotas (A5, depletion). Each is shown on Synthea data. | Big Bird shows cross-querier unsoundness for web ads, with no custodians and no ledger. ULDP-FL covers overlap in FL training. A2 and A4 are specific to debit-gated federated aggregation and do not appear in G2's prior-art set. |
| C2 | **A debit-before-contribute privacy filter on the PBC.** It has five parts: (i) identity-derived patient groups, so parallel composition does not depend on which hospitals hold a patient; (ii) multiplicity-capped contribution weights, so each patient's total contribution is bounded across sites; (iii) secure aggregation with noise calibrated to honest hospitals only; (iv) each hospital verifies debits on its **own** PBC replica, so the Inter-BC API is needed for liveness only; (v) quotas reserved per issuing authority. | Zhao 2020: a single-curator counter. Shrinkwrap/Cryptε/Drynx: per-curator budgets with no cross-querier accounting. DProvDB/Pujol: a trusted central DB. |
| C3 | **Security definitions and analysis**: a budget-soundness game, availability under quotas, and a *degradation theorem* under PBC governance or consensus capture (G6). Invariants and two broken mutants are checked in **TLA+/TLC**. | None of the G2 prior art has a soundness game without a trusted accountant, or an analysis of what happens when the ledger is captured. |
| C4 | **The measured price of soundness**: the cost of not linking patients (an RMSE factor of about sqrt(\|S\|(\|S\|-t))), the noise penalty for collusion (\|S\|/(\|S\|-t)), quota fragmentation, and latency and gas on a 3-laptop Besu-QBFT PoC. | Prior systems report utility against a trusted or central baseline, not this decomposition. |

Framing guard (Exclusion zone 2): nothing is decrypted, KSSC/ABE are untouched, and there are no capability tokens. The object of study is the **DP filter's soundness**, not authorise-then-transform.

## 2. System model mapped onto HMBC

| HMBC component | Change |
|---|---|
| RSC | Unchanged. Each hospital's **stats executor** registers as a device principal (III-D2 footnote 3) with an ECDH key pk_h. |
| TMSC | Unchanged. A new view `isValid(gid, role, issuer)` covers cert, CRL and TempACL. A university CA-Admin publishes IRB approval as a **TempACL entry** (GID, IRBApproved:proj, from, to), which reuses III-C6 semantics. |
| PSC | New entry point `requestStat(Query)`. It stays the single entry point, and msg.sender = GID (an Ethereum address, IV-D). |
| LSC | Logs the request. The BudgetLedger events form the privacy-loss log. `retrieveLog`/majorityConsent stays the auditor path. |
| **BudgetLedger** (new, PBC) | Per-group filter, quotas, debit, share posting, release, refund. |
| **ACSC-Q** (new, Hospital DBC) | A pure policy function `check(q, attrs)`, plus `logDecision` for the DBC audit trail. |
| KSSC, ABE | Untouched. The statistics path never decrypts records for the requester. |
| Inter-BC API | Off the safety path. It is used only for fan-out and throttling, so it is trusted for liveness only. |
| Data layer | Each hospital's executor sits next to that hospital's own DB. The custodian already holds plaintext, because it encrypts its own data (III-C2). |

```solidity
// PBC. Units: micro-rho (1e-6). Parameters change only via majorityConsent + timelock; every change bumps cfgEpoch.
contract BudgetLedger {
  uint8 constant G = 16; uint64 public B; uint64 public cfgEpoch; uint8 public tMax; uint64 public T; // deadline
  mapping(uint8=>uint64) spent;  mapping(uint8=>uint64) poolUsed; uint64 pool;          // per group
  mapping(bytes32=>uint64) reserve; mapping(bytes32=>mapping(uint8=>uint64)) spentA;    // per authority
  mapping(address=>uint64) gidCap;  mapping(address=>mapping(uint8=>uint64)) spentGid; // cap set by issuing authority
  enum St {None, Committed, Released, Refunded}
  struct Query { address gid; bytes32 sponsor; bytes32 role; bytes32 qhash; uint16[] S; uint256 mask;
                 uint8 cls; uint64 c; uint8 mMax; uint64 rho; uint64 sigma2; uint16 vecLen; uint64 epoch; bytes32 nonce; }
  struct Debit { Query q; St st; uint64 deadline; uint16 posted; uint16 abstained; uint64[] acc; }
  mapping(bytes32=>Debit) public debits;

  function debit(Query calldata q) external onlyPSC returns (bytes32 qid) {
    qid = keccak256(abi.encode(block.chainid, address(this), q));             // binds every field
    require(debits[qid].st == St.None && q.epoch == cfgEpoch && q.S.length > tMax && sortedUnique(q.S));
    require(TMSC.isValid(q.gid, q.role, q.sponsor));
    require(noiseOK(q.c, q.mMax, q.S.length, tMax, q.rho, q.sigma2));        // Sec. 4 formula, integer arithmetic
    for (uint8 g = 0; g < G; g++) if (bit(q.mask, g)) {
      require(spent[g] + q.rho <= B); spent[g] += q.rho;
      chargeAuthority(q.sponsor, g, q.rho);   // reservation first, then the common pool; reverts if both exhausted
      require(spentGid[q.gid][g] + q.rho <= gidCap[q.gid]); spentGid[q.gid][g] += q.rho;
    }
    debits[qid] = Debit(q, St.Committed, now64() + T, 0, 0, new uint64[](q.vecLen));
    emit Debited(qid, q.gid, q.sponsor, q.qhash, keccak256(abi.encode(q.S)), q.mask, q.rho, q.sigma2, q.epoch);
  }
  function postShare(bytes32 qid, uint16 h, uint64[] calldata y) external onlyExecutor(h); // Committed, h in S, once, before
      // deadline; acc += y (unchecked, mod 2^64); when posted == |S|: st = Released, emit Released(qid, acc)
  function abstain(bytes32 qid, uint16 h) external onlyExecutor(h);                  // only if h has not posted
  function refund(bytes32 qid) external;    // ONLY if abstained == |S| (so posted == 0); credits rho back
  function setParams(...) external onlyMajorityConsent timelocked;                   // ++cfgEpoch
}
contract ACSCQuery {   // Hospital DBC, agreed by hospital-domain stakeholders (III-E)
  struct Rule { bytes32 role; bytes32 issuerClass; uint8 cls; uint8 minS; uint64 maxRho; bool needsIRB; uint16 maxCells; }
  function check(Query calldata q, Attr[] calldata attrs) external view returns (bool);
  function logDecision(bytes32 qid, uint16 h, bool ok) external onlyExecutor;   // audit trail, not a trust anchor
}
```

**Deployment (3 laptops; RAM figures are estimates to be measured in W1).** PBC: Besu QBFT with 4 validators, so f=1. QBFT finalises a block when it is imported, which HMBC's PoS (V-B3) does not guarantee. This deviation is deliberate and is stated in the paper. Hospital DBC: Besu QBFT with 3 validators (f=0). That is acceptable because the DBC is not on the budget-safety path.

| Laptop | Runs | RAM |
|---|---|---|
| L1 | H1: PBC validator V1, DBC validator D1, executor E1 (Python, web3.py, SQLite). University U: PBC validator V4. Analyst and attack clients. | ~2.6 GB |
| L2 | H2: V2, D2, E2. Insurer Z's CA (offline script). | ~1.8 GB |
| L3 | H3: V3, D3, E3. Relayer (untrusted). TLC runs are scheduled when no chain experiment is running. | ~1.8 GB (+2 GB TLC) |

Besu runs with `-Xmx512m`. If it exceeds the budget, fall back to one Anvil per chain, label it "no consensus", and report gas only.

**GID/cert flow.** Researcher A registers via RSC with cert_A^U and receives GID_A. U's CA-Admin publishes the TempACL IRB entry. A's queries are transactions signed by GID_A. **Trust:** hospital h verifies a debit using its own nodes only: (a) it reads the transaction calldata and `debits(qid)` from its local PBC node (QBFT commit seals were checked on import); (b) it recomputes qid; (c) it re-runs `TMSC.isValid` at the current head, which closes the TOCTOU gap (gap d); (d) it evaluates `ACSCQuery.check` by eth_call on its local DBC node. The Inter-BC API is left with notification and throttling only. The executors could subscribe to `Debited` events and bypass it entirely.

## 3. Threat model

| Adversary | Capabilities | Guarantee | Rests on |
|---|---|---|---|
| Malicious analysts | Any number of GIDs. Adaptive queries, differencing, averaging, arbitrary choice of S and mask. They collude. | Loss to the **union** of all analysts is at most B per group | Ledger safety + filter |
| Sybil GIDs across authorities | k corrupt or careless CAs mint GIDs (A1 N7: nothing binds GID to person) | Soundness is unaffected (budgets are per patient group, not per GID). Depletion is bounded by the corrupt authorities' reservations plus the pool | Reservations |
| Colluding principals in one organisation | Pool their queries | They share one authority reservation. Soundness is unaffected | Same |
| Up to t corrupt hospitals | Semi-honest in the PoC. In the aggregation, a malicious hospital can only distort *correctness*: the masks are linear and honest noise covers honest data. In PSI they are semi-honest, see Sec. 4 | Patients' data at honest hospitals stays protected. Data held at a corrupt hospital is out of scope (custodial trust) | Requires \|S\| > t, enforced on-chain and locally |
| Relayer / Inter-BC API | Fully malicious: drop, reorder, inject | Liveness only | Local verification |
| Replay | Reuse a debit across S, epoch, chain or query | At most one release per debit | qid binding, seen-set |
| Depletion DoS | Burn the budget with junk queries | An honest authority keeps its reservation | Quotas |
| PBC governance or consensus capture | See below | Degrades to per-hospital caps | Hospital-pinned parameters |

**Trust-assumption subsection (from G6).** Soundness at B needs **L** (ledger safety: fewer than n/3 Byzantine QBFT validators; HMBC states an honest majority) and **P** (parameter integrity: B, tMax, the noise formula and the contract code hash cannot change without each honest hospital agreeing). G6 shows that under HMBC's rules a coalition can capture the *smallest* domain. That takes 1 organisation under the JANUS quorum `round(n/2)` and 2 under a strict majority. The coalition then admits about N-2a sham stakeholders, each of which is a PBC node, and so reaches PBC governance and possibly a validator majority. If that happens, P fails (B is raised or `spent` is reset), and L can fail too. **Mitigation and degradation theorem.** Each honest hospital h pins (B_h, tMax_h, noise formula, code hash) and keeps a local counter Λ_h[g]. It contributes only if Λ_h[g] + ρ ≤ B_h. Then even under capture, for every patient P, L(P) ≤ Σ_{h ∈ H(P), h honest} B_h. In words, the guarantee degrades from B to |H(P)|·B, which is exactly the per-hospital baseline A1 and never worse. Single-site patients (about 85% in our data) keep B.

## 4. Privacy unit and accounting decisions

| Issue | Decision | Why (one line) |
|---|---|---|
| Unit | **Patient-level** zCDP: neighbouring datasets differ in all records of one person, at all sites | This is the unit HMBC's privacy claim is about |
| Composition when sites overlap | **Identity-derived patient groups** g(P) = HMAC(k_H, ID_P) mod G with G = 16, where ID_P is a common national health ID (AMKA in Greece; the SSN field in Synthea). Each group has its own filter. Without a common ID, use G = 1 | The partition is a data-independent function of the person, so parallel composition holds no matter which hospitals hold P. Hospital-set partitions are unsound (A2). Soundness does not depend on k_H being secret |
| Sensitivity within a query under overlap | **Multiplicity-capped weights** w(P) = min(1, m_max/m(P)), with m_max = 1. m(P) is computed once per data epoch by **pairwise ECDH-PSI** between hospital executors; each learns only which of ITS patients the peer also holds. *Unlinked fallback*: m_max = \|S\|, no PSI | A total contribution ≤ c per patient is what makes secure aggregation pay off (see the variance table below). Bucketed sketches were rejected: a hash collision lets the removal of P change a co-bucket patient's weight, which breaks the sensitivity bound. Corrupt PSI peers can only push m(P) up, which reduces contributions (safe direction) |
| Budget model | **ρ-zCDP**, stored as an integer micro-ρ ledger. ε is reported via ε = ρ + 2√(ρ ln 1/δ) with δ = 1e-6. When ρ is chosen adaptively, validity comes from the Rényi filter (Feldman-Zrnic) at every order | Additive costs suit a ledger. At about 100 queries the σ is roughly 2.6x smaller than pure-ε Laplace (σ = 160 vs 424 for Δ = 3, ε = 1) |
| Noise | **Distributed discrete Gaussian** (KLS21), sampled locally by each hospital with an exact integer sampler and **calibrated to honest parties**: σ_h² = c²·max_{k∈[\|S\|−t,\|S\|]} min(m_max,k)²/k ÷ (2ρ). For m_max = 1 this is c²/(2ρ(\|S\|−t)). Charge ρ plus the KLS21 sum-slack, which is negligible for σ_h ≫ 1 (verify the constant). Skellam is a sensitivity check (it is closed under summation) | No sampling inside MPC is needed. Corrupt hospitals cannot remove honest noise |
| Quota hierarchy | Per group, B (soundness) ⊇ domain shares (research / insurance) ⊇ reservation q_a per **issuing authority** ⊇ GID cap set by that authority; plus a common pool. The sponsor is the issuer of the role attribute that the ACSC-Q rule matched | Maps onto HMBC's no-root-CA trust, where each stakeholder is its own CA |
| Answer reuse | Answers are **public on the PBC** (DP plus post-processing). Cache key = (qhash, S, mask, dataVersion vector), so an identical query costs 0. Workloads are histogram-first | Makes averaging attacks useless and free |
| Depletion | Reservations, GID caps, and refunds only through unanimous Abstain | Sec. 5 |
| Time | MVP: a **lifetime** budget per group (honest semantics). Per-data-epoch budgets are left as an open question | Renewal changes what the guarantee means |

**Noise variance per query** at the same charged ρ, with c = 1: central curator 1/(2ρ). Linked mode (ours): \|S\|/((\|S\|−t)·2ρ). Unlinked mode, which equals sound local DP: \|S\|²/(2ρ). So the **linked/unlinked variance gap is \|S\|(\|S\|−t)**: 6x at n=3, t=1 and 45x at n=9, t=4. Back-of-envelope on 90k patients, a count of about 1,000, ±10% at 95% (σ ≈ 50), ε = 2 (ρ = 0.0676): central ≈ 338 queries, **linked ≈ 225**, unlinked ≈ 37. One authority holding a 20% reservation gets about 45 linked queries plus pool access. Cells of about 200 patients cost 25x more per query. That is where utility can collapse (Sec. 7, H1).

**Linkage leakage (stated honestly).** DH-PSI is semi-honest. A malicious hospital that feeds in arbitrary IDs learns a peer's patient list. Mitigation: each executor commits on the PBC to the Merkle root and the size of its hashed-ID set per epoch, so probing becomes auditable later. Note that HMBC Rule 2 already gives any on-duty doctor read access to all hospitals' records, so cross-hospital membership is inside HMBC's existing trust. That is still a human decision (Sec. 10).

## 5. Protocol

**Per data epoch (setup).** E1: each executor registers (pk_h) via RSC. E2: pairwise ECDH-PSI on HMAC(k_H, ID) gives m(P) and w(P) for the executor's own patients. E3: each executor posts dataVersion_h, |set_h| and the Merkle root of its ID-hash set to the PBC. Pairwise mask keys are k_hj = KDF(ECDH(sk_h, pk_j)).

**Per query**
1. **Authorise (client side).** Analyst A builds q = (gid, sponsor, role, qhash = H(canonical query AST), S sorted, mask, cls, c, m_max, ρ, σ², vecLen, cfgEpoch, nonce). A checks the answer cache and dry-runs `ACSCQuery.check` by eth_call. Both steps are free.
2. **Debit.** A calls PSC.requestStat(q) as a transaction signed by GID_A. Atomically, PSC runs TMSC.isValid, logs to LSC, and calls BudgetLedger.debit. The result is either a revert or `Debited(qid, …)`.
3. **Receipt.** The receipt is the finalised block holding `Debited` and the state `debits[qid].st = Committed`. Under QBFT this is final on import. On a PoS chain, wait for the finalised checkpoint.
4. **Local verification** by each h ∈ S, using only its own nodes:
   - (a) fetch the calldata and recompute qid; check st = Committed, epoch = cfgEpoch = h's pinned configuration, and h ∈ S;
   - (b) run `TMSC.isValid` at the current head (catches revocation);
   - (c) run `ACSCQuery.check` on the local DBC;
   - (d) check σ² ≥ the pinned formula, \|S\| > t_h, Λ_h[g] + ρ ≤ B_h for all g ∈ mask, and dataVersion matches;
   - (e) if `seen_h[qid]` is false, **write ahead**: persist (qid, seed_h), fsync, then set seen. If any check fails, post `abstain`.
5. **Aggregate.** x_h = Σ_{P∈D_h, g(P)∈mask, pred(P)} w(P)·clip_c(f(P)) in fixed point (2^16), as a vector of length vecLen. Sample η_h ~ N_Z(0, σ_h²) from seed_h. Compute y_h = x_h + η_h + Σ_{j>h} PRF(k_hj, qid) − Σ_{j<h} PRF(k_jh, qid) mod 2^64.
6. **Contribute.** h calls `postShare(qid, h, y_h)` and sets Λ_h[g] += ρ.
7. **Release.** When the \|S\|-th share arrives, the contract sums the shares (the masks cancel), sets st = Released and emits `Released(qid, answer)`. A post-processes the answer (scaling, means, ratios).
8. **Log.** `Debited`, the \|S\| `ShareFor` events and `Released` form the privacy-loss log. Each h also calls `logDecision` on the DBC. An auditor uses `retrieveLog` and recomputes spent[g].

**Replay and binding**

| Bound field | Attack it stops |
|---|---|
| chainid, contract address | Cross-chain / cross-deployment replay |
| gid = msg.sender | Debit theft (in private mode, shares are encrypted to pk(GID)) |
| qhash, cls, c, m_max, ρ, σ², vecLen | Query substitution, noise downgrade |
| S (sorted) | Hospital-set replay (h ∉ S refuses; S′ ≠ S gives a new qid) |
| cfgEpoch | Replay across parameter or validator-set changes |
| nonce | Deliberate fresh re-run, which is charged again (the cache serves the old answer for free) |
| qid as PRF input | Mask reuse. Two queries with the same masks would let anyone difference y_h and recover x_h − x′_h |
| seen_h plus the contract's posted flags | At most one share per (h, qid) |

**Failure and atomicity.** A debit revert means nothing happens. Concurrent debits are serialised by the EVM, so the budget cannot be double-spent. If a hospital drops out after others have posted, there is no output and **no refund** (fail-closed). **Refund only if all of S abstained.** The obvious rule "refund if fewer than |S| shares were posted" is UNSAFE: once all honest hospitals have posted, a corrupt one can hand its y_j to A off-chain, A reconstructs the answer, and the budget is credited back anyway. A reverted `postShare` also leaks, because its calldata is still published in the block, so honest executors must check the status locally before sending. Requiring Abstain from every member of S ensures that no honest share was ever published. This counterexample is one of the TLC mutants in Sec. 6.

## 6. Security properties and proof plan

| Property | Definition (sketch) | Reduces to |
|---|---|---|
| **P1 Budget soundness** (game Exp^BS) | The adversary controls all analysts, the corrupt authorities C_A, up to t hospitals, the relayer and network scheduling, and may submit any transaction. It wins if, for some group g, the sum of ρ_r over released runs r that had a contribution from an honest hospital with g ∈ mask_r exceeds B. | Ledger safety (L+P), EUF-CMA of ECDSA (GID tx), collision resistance of keccak (qid). Contract arithmetic gives Σ debits ≤ B, and honest contributions are injective into debits (P2). |
| **P1′ DP of the coalition's view** | The joint view of all analysts, the corrupt hospitals and the PBC observers is (B+τ)-zCDP for any patient whose records are at honest hospitals. | (i) Hybrid: replace the masked sum with ideal F_sum (PRF + CDH/ROM for ECDH keys; Bonawitz-style, no dropout recovery). (ii) The honest part has sensitivity ≤ c (weights; PSI correctness, semi-honest). (iii) Honest noise is at least c²/(2ρ), plus the KLS21 sum-slack τ. (iv) Adaptive composition via the Rényi filter, in parallel over groups. (v) Post-processing. Refusals and aborts depend only on public values. |
| **P2 No release without committed debit** | For every honest h and every qid: if h posts a share, then a debit for qid is Committed in h's replica, with h ∈ S, matching pinned parameters, at most once, and never after it abstained. | Protocol invariant. **TLA+-checked** |
| **P3 Availability under quotas** | For every honest authority a ∉ C_A and every group g, a debit with spentA[a][g] + ρ ≤ q_a that is within its GID cap succeeds whatever others do, given ledger liveness and a PSC that does not censor. | Contract invariant plus BFT liveness (assumed) |
| **P4 Auditability** | From the events alone, an auditor recomputes spent[g] and checks that every `Released` has one `Debited` and \|S\| `ShareFor` events. Honest seen_h logs match on-chain. | Ledger integrity |
| **P5 Degradation under capture** | If L or P fails, then L(P) ≤ Σ_{honest h∈H(P)} B_h. | Local caps (Sec. 3) |

**The tool-verified model: TLA+/TLC** (`BudgetFilter.tla`). TLA+ is the right tool here because the properties are arithmetic, state and concurrency invariants (Σρ ≤ B, at-most-once, refund safety under lagging replicas and an adversarial relayer). ProVerif and Tamarin handle sums poorly. Cryptography is abstracted: signatures are unforgeable, and masks hide a share until all shares are present.
- **Constants:** 3 hospitals, of which at most 1 is corrupt; 2 groups; 3 GIDs from 2 authorities, 1 of them corrupt; B = 3; ρ ∈ {1, 2}; at most 4 queries; 2 cfgEpochs.
- **State:** the chain (a sequence of committed transactions), view[h] (each replica lags as a prefix), debits, posted, abstained, seen_h, Λ_h, released, params, and a `captured` flag.
- **Actions:**
  - adversarial Submit, Inject and Replay;
  - Debit, following the contract logic;
  - HonestPost, guarded by checks against view[h];
  - CorruptPost and off-chain hand-over;
  - Abstain and Refund;
  - ParamChange: timelocked, or immediate when captured;
  - Reconstruct.
- **Invariants:**
  - Inv_Sound: ¬captured ⇒ for every g, Σ released ρ ≤ B;
  - Inv_Bind (P2);
  - Inv_Once;
  - Inv_RefundSafe: refunded ⇒ never reconstructed;
  - Inv_Degrade: captured ⇒ Λ_h[g] ≤ B_h;
  - Inv_Avail: the Debit-enabling condition for the honest authority.
- **Mutants that TLC must break, with the counterexample trace shown in the paper:**
  - M1: a receipt without S and epoch binding (A4);
  - M2: refund when posted < \|S\| (Sec. 5);
  - M3: accounting keyed per hospital set (A2).
- **Expected scale:** about 10^6 to 10^7 states, minutes to under an hour with `-Xmx2g`. Use symmetry sets for GIDs and groups.
- **Code link:** the Solidity contract mirrors the TLA+ invariants as **Foundry invariant tests**. Model ≠ code, so state this as a limitation.

**What 2 months can and cannot deliver.** *Can*: game definitions; P1 proved as an invariant plus a reduction sketch; P1′ by careful composition of published theorems (DDG sum, zCDP, the Rényi filter, secure aggregation); P3 and P5 proved directly; bounded TLC checks with mutants; fuzzed contract invariants. *Cannot*: a UC or full simulation proof of the composed system; malicious-secure PSI or aggregation; unbounded TLAPS proofs; ledger (QBFT) security itself; side channels such as timing of abstain/post; a proof that the sampler implementation is correct (mitigate with statistical tests, an exact integer sampler, and no floating point).

## 7. Evaluation plan

**Baselines.** B0: HMBC/JANUS as-is (Researcher attribute, raw per-hospital counts). B1: per-hospital local DP with local ledgers. B2: trusted central curator with a global budget and dedup (the utility upper bound). B3: secure aggregation without DP (PriCollabAnalysis-style). The following naive designs serve as attack targets: B3′ (DP with budgets keyed by hospital set), B4 (per-GID budgets, DProvDB-style), B5 (an unbound PBC-signed approval receipt), B6 (a global budget without quotas).

| Attack | Target | Setup | Metric | What stops it in ours |
|---|---|---|---|---|
| Tracker | B0, B3 | Two date-range or subset queries | Exact recovery of 1 patient | DP + filter |
| A1 overlap | B1 | Target at m ∈ {1,2,3} sites; query every site until its budget is exhausted | MI advantage vs #queries; analytic μ = √(2mB) | Groups + weights |
| A2 subset differencing | B3, B3′ | All 2^n − 1 subsets, n emulated up to 9 | Advantage vs #subsets (B3′ gives 2^(n−1)·B) | Groups (S-independent) |
| A3 Sybil | B4 | k ∈ [1, 200] GIDs from colluding authorities | Advantage vs k (μ = √(2kB)) | Global per-group filter |
| A4 replay | B5 | Replay 1 debit across S′, epochs | Releases per debit; advantage | qid binding + seen + epoch |
| A5 depletion | B6 | Sybils burn B with junk queries | % of the honest authority's 30-query workload answered | Reservations |
| Averaging | B3′ / no-cache | Repeat an identical query | Advantage | Cache (0 cost) + charge on new nonce |

**Metrics.**
- MI advantage: the best-threshold TPR−FPR of a likelihood-ratio adversary that knows every other record, over 2,000 paired trials. It is plotted against the analytic bound 2Φ(√(2ρ_tot)/2) − 1 (Gaussian DP; 0.15 at ε = 2).
- Relative error and RMSE vs ε for the workload W: 30 queries mixing counts, clipped cost sums and ≤64-cell histograms, with cells from about 100 to 5,000.
- Useful queries before exhaustion (rel. err ≤ 10% at 95%), with and without quotas and under A5.
- Bias of the m_max weights for predicates recorded at only some of a patient's sites.
- End-to-end latency broken down into debit, verify, aggregate and release.
- Gas per `debit` against the number of groups in the mask; gas per `postShare` against vecLen.
- Bytes per query, PSI time per epoch, and scaling to 9 emulated hospitals.

**Synthea sizing.** Generate 90k patients in 9 batches of 10k (`-Xmx2500m`). Export only patients, conditions, encounters and claims, with years_of_history = 10. Generation time and size are estimates, to be measured in W1: a few hours overnight, 1-3 GB of CSV, and an SQLite file of about 100-300 MB per hospital. Site assignment: one uniform home site; 15% of patients also get a second site and 3% a third; encounters and their conditions are split across sites by date. The 9-site run re-splits the same population. The statistics and attack simulator is pure Python + numpy and uses under 1 GB. Only A4, A5 and the cost runs need the chain.

**Hypotheses that can FAIL.**
- **H1 (KILL).** Linked mode at ε ≤ 2 per group answers ≥ 25/30 W-queries within ±10% at 95%. Small cells are the real risk.
- **H2.** The unlinked/linked RMSE ratio is about √(\|S\|(\|S\|−t)), i.e. 2.45 at n=3. It fails if the m_max = 1 weighting bias outweighs the noise gain.
- **H3.** An honest authority completes ≥ 90% of its reserved workload under A5, against ≤ 10% without quotas. It fails through *fragmentation*: 4 authorities at 20% each may leave too little for any single one.
- **H4.** Median end-to-end latency ≤ 10 s on Wi-Fi with 3 hospitals.
- **H5.** Each baseline attack reaches advantage ≥ 0.9 within ≤ 200 queries or GIDs at ε = 1 per unit, while ours stays ≤ bound + 0.02.

**Go/no-go at the end of W4.** Run on the simulator plus a 1-laptop chain.

| Gate | PASS | FAIL action |
|---|---|---|
| G1 utility | Linked mode ≥ 25/30 at ε ≤ 4 (ideally at ε = 2). CONDITIONAL: 15-24/30 at ε = 4, so continue with a histogram-first workload and report utility honestly | Linked < 15/30 at ε = 4: pivot to an "attacks + price-of-soundness" paper (C1+C3+C4, no system utility claims) |
| G2 attacks | A1-A3 ≥ 0.9 on baselines; ours within bound | Treat as an adversary or bug issue; fix before W5 |
| G3 engineering | debit→verify→postShare→Released on a 4-validator Besu, median ≤ 10 s | Anvil plus simulated finality (labelled); concentrate on gas and TLA+ |

## 8. Scope, plan, roles, risks

**MVP.**
- BudgetLedger, PSC.requestStat and ACSC-Q on Besu QBFT (PBC with 4 validators, DBC with 3).
- A Python executor that does local verification, linked-mode ECDH-PSI, pairwise-mask aggregation posted on-chain, and distributed discrete Gaussian noise.
- Query classes COUNT, clipped SUM and HIST with ≤ 64 cells.
- Quotas and refund-by-unanimous-abstain.
- The simulator with baselines B0-B6 and attacks A1-A5.
- TLA+ with mutants M1-M3.
- Definitions and proof sketches.

**Stretch.** Per-data-epoch budgets; private-answer mode (shares encrypted to pk(GID)); a Skellam comparison; a malicious-secure aggregation datapoint (MP-SPDZ); a *live* governance-capture run showing that local caps hold (the G6 tie-in); 9 hospitals spread over 3 laptops; a ProVerif model of the ECDH-mask channel.

| Week | S1 Ledger & formal | S2 Privacy engine | S3 Data, attacks, eval |
|---|---|---|---|
| W1 | Besu QBFT with 4+3 nodes on one laptop; RAM measured; kill-search for novelty once WebSearch resets | zCDP accountant; exact discrete Gaussian sampler with statistical tests | Synthea batches; site split; SQLite |
| W2 | BudgetLedger v0 with Foundry tests | Weights, masks, fixed point; simulator core | Workload W; baselines B0-B3 in the simulator |
| W3 | PSC/TMSC hooks; ACSC-Q; gas of `debit` | ECDH-PSI; executor verification against a local node | A1-A3 + MI harness; utility curves |
| W4 | 3-laptop network; **GO/NO-GO** | End-to-end flow; **GO/NO-GO** | **GO/NO-GO** numbers |
| W5 | Quotas, refund; TLA+ spec | Abstain/fail-closed; private mode (stretch) | A4, A5 end-to-end; B4-B6 |
| W6 | TLC + mutants; Foundry invariants | Proof write-up for P1/P1′ | Latency, gas and bytes; 9-site scaling |
| W7 | Stretch (capture run) | Stretch (Skellam / MP-SPDZ) | Final runs, figures |
| W8 | Paper (all), artifact cleanup, buffer | | |

A 4th student, if available, takes TLA+ and proofs from W3.

| Risk | P | I | Mitigation |
|---|---|---|---|
| R1 Utility collapse (small cells, lifetime budget, fragmentation) | H | H | Histogram-first workloads, cache, linked mode, G1 gate, pivot plan |
| R2 Novelty kill (ledger-gated global DP budget across custodians in IEEE/Elsevier venues) | M | H | Re-run G2's Kill-1 queries in W1; position on C1+C3 |
| R3 Common patient ID or PSI leakage rejected | M | M | Unlinked mode with G = 1 (still sound); report the gap |
| R4 Besu RAM or Wi-Fi latency | M | M | `-Xmx512m`; Ethernet or hotspot; Anvil fallback |
| R5 DP implementation bugs (floating point, sampler) | M | H | Integer-only arithmetic, exact sampler, χ² tests, empirical MI vs bound as a regression test |
| R6 TLC state explosion | M | L | Shrink constants, symmetry |
| R7 Perceived as Exclusion zone 2 or "a counter on a chain" | M | H | Lead with A1-A5 and the capture degradation, not gating |
| R8 Synthea time or size | L | M | Generate overnight in W1; fewer modules |

**Fallback if the MPC is too heavy.** The MVP already uses the lightest possible MPC (linear pairwise-mask aggregation, no framework). F1: if posting vectors on-chain is too costly, post only commitments, and send the shares to A off-chain, encrypted to pk(GID). F2 is a **trusted aggregator at the PBC, clearly labelled**, which receives each hospital's noisy value calibrated at the **unlinked/local** level (σ_h² = |S|c²/(2ρ)). The TA then learns institution-level noisy aggregates but cannot weaken patient-level DP, so soundness claims stand while utility drops to the unlinked mode.

## 9. Workshop-paper outline (6-8 pp.)

1. Introduction: the "controlled and logged" quote, the A1-A5 teaser and the contributions.
2. Background: the HMBC architecture and the Fig. 6 flow; zCDP and the filter.
3. System and threat model, with the trust-assumption box (L, P, capture).
4. Why naive accounting fails: attacks A1-A5.
5. Design: groups, weights, the masked aggregate, BudgetLedger and the protocol.
6. Security: the game, theorems P1-P5, and the TLA+ results with mutant traces.
7. Evaluation: utility, quotas and DoS, costs.
8. Related work: G2's table, condensed.
9. Limitations and conclusion.

**Figures.**
- Fig. 1: HMBC's Fig. 6 extended with the statistics path. It marks the steps that are checked on each hospital's own replica.
- Fig. 2: MI advantage vs #queries or #GIDs for A1-A3, each baseline against ours and the analytic bound.
- Fig. 3: (a) relative error vs ε for central, linked, unlinked and local; (b) useful queries before exhaustion under A5, with and without quotas.

**Key table.** An attack × design matrix (B0-B6 vs ours) that names the mechanism stopping each attack. **Second table:** a cost breakdown (latency per step, gas, bytes, PSI per epoch).

## 10. Open questions for a human decision

1. Is a **common patient ID** (AMKA/SSN) plus PSI leakage of intersection membership among hospital executors acceptable? If not, the team runs unlinked mode only: still sound, about 2.45x RMSE at n=3, and the MPC's DP utility benefit disappears.
2. Should answers be **public on the PBC**, which gives reuse and audit but reveals insurers' queries to competitors (a GC1 tension), or private and encrypted to the GID?
3. Should the budget be a **lifetime** budget or per data epoch? And what should B, δ and the domain/authority quota split be?
4. What is the collusion bound **t**? Does the analyst's own employer hospital count as potentially corrupt?
5. Is the **QBFT** deviation from HMBC's PoS acceptable, given it buys finality? Or should the team stay on Anvil and make no consensus claims?
6. Should the **G6 capture analysis** go in as Sec. 3 / P5 only (recommended) or become a sister paper?
7. Who re-runs the **Kill-1 novelty search** before W2, and with what query list (G2 Sec. 7)?
8. Target venue and page limit, which decides whether the ProVerif stretch is worth doing.

Status: COMPLETE (2026-10-04).
