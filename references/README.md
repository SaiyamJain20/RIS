# Active sources

| Source | Use and limitation |
|---|---|
| [HMBC2020.pdf](HMBC2020.pdf), [searchable text](HMBC2020.txt) | Primary specification: Malamas, Kotzanikolaou, Dasaklis and Burmester, IEEE Access 8, 134393–134412, DOI [10.1109/ACCESS.2020.3011201](https://doi.org/10.1109/ACCESS.2020.3011201). The PDF controls when extraction omits rules/tables. |
| [Lewko–Waters 2011](LewkoWaters_2011_EUROCRYPT.pdf) | Decentralized ABE basis. Read construction and security model before selecting a cryptographic adapter. No claim of a new ABE scheme. |
| [Green–Hohenberger–Waters 2011](GreenHohenbergerWaters_2011_USENIX-Security.pdf) | Reference on outsourced transformations. Its security does not automatically apply to an arbitrary split of LW decryption. |

## HMBC passages to extract during E0

- III-C4 and PDF page 7: Rules 1/2, long-term and temporal attributes, intended emergency use.
- III-C5/C6 and III-D1/D2: independent authorities, signed trust lists, GID possession and registration.
- III-D3/D4, III-E1/E2, Figures 5/6, Tables 2/3: PSC/RSC/TMSC/LSC/ACSC/KSSC responsibilities, intended actuators and access flow.
- III-E2 remark: optional `System` attribute in every access policy.
- IV-C/D and V-B3: Solidity/Ganache/Python/Charm prototype descriptions and reported timings.
- V-A1/A4/A5: isolation, honest-majority/key assumptions, revocation and auditing claims.

The six contract roles are supported. Request signature formats, cross-chain authentication/finality, exact membership quorum and a complete epoch lifecycle are not fully specified. III-D4's complete-details logging and V-B3's hash-only description must be represented as alternatives rather than silently reconciled.

## Tool references consulted for this plan (2026-10-06)

- [Foundry repository](https://github.com/foundry-rs/foundry): Forge testing and Anvil local EVM tooling. Freeze exact releases in E0; none were installed by this planning task.
- [EIP-712](https://eips.ethereum.org/EIPS/eip-712): typed signed messages. Replay prevention still requires application state and nonces.
- [ProVerif](https://bblanche.gitlabpages.inria.fr/proverif/): protocol correspondence/secrecy analysis under an explicit symbolic model.
- [TLA+ tools](https://github.com/tlaplus/tlaplus): bounded TLC checks of the finite state models proposed for F/G; choose and hash a release during the relevant phase.
- [Charm documentation](https://jhuisi.github.io/charm/), [documented AW11 adapter](https://jhuisi.github.io/charm/charm/schemes/abenc/dabe_aw11.html): a candidate backend to inspect, not a verified match to HMBC's split decryption. G0 must establish that match or report the blocker.
- [Besu QBFT](https://docs.besu-eth.org/private-networks/how-to/configure/consensus/qbft): optional later consensus experiment. It is a PoA protocol and is not an identified implementation of HMBC's generic PoS description.

The older 345-identifier register and all unused papers remain in the archive. Their existence/metadata checks do not certify their claims. Novelty verification is still required for the final paper.
