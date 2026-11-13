| contract.function | E median | F median | delta | E max | F max | E calls | F calls |
|---|---|---|---|---|---|---|---|
| ACSC.addPolicy | 184941 | 184883 | -58 | 184941 | 184883 | 170 | 317 |
| ACSC.consumeDecision | 81333 | 91582 | +10249 | 318932 | 339248 | 60 | 138 |
| ACSC.policy | 16905 | 16847 | -58 | 16905 | 16847 | 2 | 3 |
| ACSC.policyEnf | 233337 | 233408 | +71 | 233361 | 233432 | 33 | 36 |
| ACSC.seal | 30004 | 27970 | -2034 | 30004 | 30096 | 166 | 308 |
| KSSC.acceptState | 204031 | 204340 | +309 | 204031 | 229859 | 42 | 132 |
| KSSC.witnesses | 5009 | 8424 | +3415 | 5009 | 11840 | 60 | 138 |
| PSC.getRequest | 18512 | 18483 | -29 | 18512 | 18483 | 35 | 63 |
| PSC.reportAttestedOutcome | 43389 | 47710 | +4321 | 529718 | 549233 | 25 | 54 |
| PSC.reportOutcome | 27699 | 27640 | -59 | 301474 | 301570 | 19 | 23 |
| PSC.requestAccess | 588242 | 588671 | +429 | 594192 | 594653 | 109 | 184 |
| RSC.register | 411669 | 412436 | +767 | 412324 | 412508 | 117 | 200 |
| TMSC.checkCredentials | 28824 | 29030 | +206 | 30824 | 31138 | 65 | 123 |
| TMSC.getUserValidation | 29978 | 31271 | +1293 | 33043 | 33379 | 93 | 158 |
| TMSC.isRevoked | 5493 | 5449 | -44 | 5493 | 5449 | 9 | 18 |
| TMSC.removeCA | 702 | 658 | -44 | 702 | 658 | 3 | 4 |
| TMSC.revocationListState | 7627 | 7583 | -44 | 7627 | 7583 | 9 | 15 |
| TMSC.seal | 29930 | 30003 | +73 | 29930 | 32146 | 166 | 312 |
| TMSC.temporalAclState | 7626 | 7604 | -22 | 7626 | 7604 | 11 | 15 |
| TMSC.temporalWindow | 5769 | 5792 | +23 | 5769 | 5792 | 13 | 17 |
| TMSC.updateRevocationList | 399052 | 399122 | +70 | 433252 | 433286 | 249 | 423 |
| TMSC.updateTemporalAcl | 424438 | 424657 | +219 | 458845 | 458857 | 144 | 233 |
| TMSC.validateCertificate | 16552 | 17319 | +767 | 17171 | 17355 | 111 | 194 |
| TMSC.wire | 66706 | 66751 | +45 | 66706 | 66751 | 166 | 314 |

F-only functions (median gas, max, calls):
- ACSC.policyVersion: median 238, max 238, calls 55
- Governance.execute: median 58724, max 931093, calls 47
- Governance.governanceChainId: median 271, max 271, calls 1
- Governance.governanceNonce: median 2402, max 2402, calls 13
- Governance.maxGovernanceTtl: median 238, max 238, calls 1
- Governance.mutations: median 184, max 184, calls 1
- Governance.target: median 259, max 259, calls 1
- Governance.threshold: median 228, max 228, calls 1
- Governance.witnessSetVersion: median 215, max 215, calls 1
- Governance.witnesses: median 11917, max 11917, calls 1
- KSSC.hasCheckpoint: median 2372, max 2372, calls 7
- TMSC.authorities: median 11919, max 14196, calls 9
- TMSC.caAdmins: median 5220, max 21160, calls 20
- TMSC.deployer: median 326, max 326, calls 3
- TMSC.govAddAuthority: median 25245, max 27402, calls 3
- TMSC.govRemoveAuthority: median 25437, max 26516, calls 2
- TMSC.govSetCaAdmins: median 25963, max 27042, calls 2
- TMSC.governance: median 2465, max 2465, calls 2
- TMSC.isAuthority: median 2574, max 2574, calls 5
- TMSC.isCaAdmin: median 2747, max 2747, calls 4
- TMSC.publishCrlAs: median 47097, max 413067, calls 3
- TMSC.publishH3CrlAs: median 44800, max 44800, calls 1
- TMSC.removedAuthority: median 2618, max 2618, calls 7
- TMSC.wireGovernance: median 46251, max 46251, calls 112

(Deployment sizes intentionally omitted: use `forge build --sizes`; this parser mis-read them.)
