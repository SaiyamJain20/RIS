# work/ - our implementation workspace

Empty scaffold, prepared for the default direction (**E+F+G: executed analysis + formal models + repairs**, plan Section 9.2).
If the team picks **D** or **A** instead, keep the same folders and rename the contents (see plan Sections 9.1 and 7).

| Folder | Intended contents |
|---|---|
| `harness/` | Mock-stub tests for the JANUS chaincodes (mocha + sinon stubs of `ctx.stub` / `ClientIdentity`; pure-JS dev dependencies only), Vault-policy tests on a stock dev container, SQLite fixture for the statistics endpoint |
| `reimpl/` | Solidity/Hardhat re-implementation of the six HMBC2020 contracts (TMSC, RSC, PSC, LSC, ACSC, KSSC) + relay, for the design-level attacks |
| `models/` | Formal models with counterexamples: ProVerif/Tamarin (registration, three-party access flow), TLA+ (log completeness, governance, Byzantine fault model) |
| `experiments/` | Simulations and measurements: governance-capture Monte Carlo, queueing for revocation/flooding, key-lifecycle experiments, differencing on synthetic counts; data-generation scripts |
| `repairs/` | Hardening prototypes (authenticated cross-layer calls, strict-majority quorum, epoch-tagged domain attribute, log-before-grant) and their before/after tests |
| `paper/` | Draft, figures, bibliography |
| `notes/` | Weekly log, meeting notes, decisions |

Rules: keep resident memory under about 3.5 GB; one heavy job at a time; no building the libpbc plugin or the full Fabric/Kubernetes stack on a laptop;
synthetic data only; read the plan's Section 9.2 gate: **by the end of week 2, at least 3 HIGH findings must reproduce at mock-stub level.**
