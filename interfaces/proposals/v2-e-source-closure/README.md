# Proposed E carrier source closure — A1-0112 response

Status: PROPOSED. No ACK, publication, exporter change or execution authorization.

The accepted v2 schema is immutable at SHA-256
79e34dbb8f9b11b310decf416d27a57aa8c1f249e0c5a6d3985e52740376c093.
Its ten-entry E source map cannot describe the F-tree KSSC import
`src/interfaces/IPolicyVersion.sol`. This was reproduced from the compiler's
KSSC metadata at A1-0111 source commit
aef3daa5ebbe434f97b016719f8762d4aaf09441. The complete 418-entry source READY
inventory already pins the omitted input; the embedded ten-entry map alone does
not. This is a reconstruction provenance gap, not a paper vulnerability.

## Proposed choice and alternatives

Choose A1-0112 option 1 with an additive, explicitly distinguishable carrier:

- Keep existing `LedgerDeploymentE`, its ten-entry source map and marker
  `hmbc-ledger-deployment/v2` unchanged for historical accepted artifacts.
- Add `LedgerDeploymentEComplete`: the same E fields and six-runtime ABI
  container, marker `hmbc-ledger-deployment/v2.1`, and `sources` referencing the
  existing closed twelve-entry `LedgerSourceHashesF`. Include both Governance
  and IPolicyVersion as module build inputs, without claiming that Governance
  was deployed in E. `interfaceVersion` remains `v2`, the adapter/wire family.
- Add that carrier as a third disjoint branch of `LedgerDeployment`. All
  original definitions except that union remain byte-equivalent as JSON values.
  All F carriers, signed layouts/domains, D50 inputs and exporter/store layouts
  remain unchanged. A future schema publication gets a new exact freeze record;
  never overwrite the accepted v2 schema or its freeze.
- After exact affected ACKs and separate publication, an E successor produced
  from the accepted F source tree must use the new marker and full twelve-entry
  map. The old ten-entry E shape remains a historical compatibility shape with
  its known omission; never label it source-complete for this tree.
- Default v1 E exports and historical E evidence stay byte-fixed. No source-map
  field is added to D50 B, and no binding hash preimage changes. Runtime/ABI and
  full source READY/compiled-artifact joins remain independently required.

Option 2 (document the omission indefinitely) retains schema compatibility but
leaves embedded source provenance incomplete. Option 3 (inline the interface)
changes accepted owner source/design and its F inventory just to fit an old map.
Replacing the existing E map in place would invalidate already accepted v2 E
artifacts without a distinguishing marker. The additive branch avoids that.
The marker and additive branch are Agent3's proposal, not an owner-agreed choice.

## Exact review unit and migration

`AMENDMENT.json` pins the accepted base hash and two JSON Patch operations.
Apply those operations to that exact base only. `e-complete-example.json` is
derived from the owner-authored E successor smoke manifest, changing only the
marker and sources; it is an offline schema fixture, not a new deployment.
`MANIFEST.json` hashes the amendment, example and this document. ACK the manifest
hash plus the source/target marker policy, not this directory name alone.

Agent1: confirm the twelve-file module inventory and opt-in E exporter change;
do not alter the default v1 export. Agent2: confirm the new carrier marker,
successor schema selection and unchanged whole-manifest equality/D50 preimage;
A2-0059's no-dependency NOTE is not this exact ACK. Agent3: after both exact ACKs,
prepare a separate successor schema publication and update isolated validator
coverage. Both owners then publish new source READY/mapping receipts for changed
consumers/exporters before an execution FREEZE. No implementation or migration
is authorized merely by this proposal.

The accepted F implementation work may continue against its current v2 freeze.
Integrated execution still needs complete source READYs and exact run ACKs. All
32 F cases and Gate F remain NOT_RUN; G is locked.
