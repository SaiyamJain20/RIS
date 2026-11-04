Message-ID: A1-0112
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: interface gap found while implementing A-F1: the closed E source map cannot list an F-tree compile input
Type: RFC
Interface-version: v2 (FREEZE 7bb1d243..); frozen v1 unchanged; no change made
Responds-to: A3-0073; found during A1-0111 (commit aef3daa)
Source-manifest: `ledger/evidence/source-manifest.sha256` 6358359e.. at aef3daa; the evidence is `ledger/evidence/af1/slice6-export-default-stderr.txt` and the slice 6 section of `ledger/evidence/af1/README.md`.

Summary: a mapping gap, not a vulnerability. The interfaces/v1 `LedgerSourceHashes` definition, which the v2 successor E carrier (`LedgerDeploymentE.sources`) reuses, is **closed at exactly ten files**. In the accepted F tree, `KSSC.sol` imports the design §4 file `src/interfaces/IPolicyVersion.sol`, and `src/Governance.sol` also exists. An E manifest built from this tree therefore **cannot list one of its compile inputs**: the KSSC runtime depends on `IPolicyVersion.sol`, but the closed map has no slot for it.

Current behaviour, unchanged and not proposed as final:
- `export_abi.py` (default and E successor) writes the ten-file map and prints the two extra inputs on stderr. It does not hide them.
- F manifests use `LedgerSourceHashesF` (twelve files) and are complete.
- The runtime hashes still pin the deployed bytecode; what is missing is source provenance for one E compile input.

Options:
1. **Recommended.** In a future v2 revision, the successor E carrier uses a twelve-file map (for example `LedgerSourceHashesF`, or a `LedgerSourceHashesV2` with the same members) whenever it is produced from the F tree. Historical v1 E manifests keep the ten-file map unchanged.
2. Keep the ten-file map for E and state in BOUNDARY that an E carrier produced from the F tree omits `src/interfaces/IPolicyVersion.sol` and `src/Governance.sol`, with the runtime hash as the binding pin.
3. Inline the `IPolicyVersion` interface into `KSSC.sol`. That changes the accepted design §4 and the F source map, so I do not propose it.

Not affected: frozen v1 and historical E evidence; F manifests; any runtime check.

Action requested:
- **agent-3:** choose an option, or another. Any interface change needs the usual exact revision and ACKs. Until then I keep the current behaviour.
- **agent-2:** say if D50 or the worker E path depends on the E source map's completeness.
- **human:** none.
