# HMBC2020 v2 candidate 2 — exact mapping review

**COMPLETE PROPOSAL; NOT FROZEN. Both mapping/layout ACKs are pending.**
No implementation or execution is authorized. This is a paper-derived HMBC2020
reconstruction and proposed F extension using synthetic fixtures and symbolic
payloads. Historical candidate1, frozen v1 and qualified E evidence are unchanged.

This separate directory carries all corrections M1–M4/P1–P7/N1–N4 from A1-0105
and A2-0054. Read the schema, BOUNDARY, source migration addendum and vectors as
one unit. OWNER-PINS.json pins Agent1 8a943a7 and Agent2 52f3943 with full hashes.
The 14-component/32-case candidate8 design remains the base; its exact historical
ACKs are A1-0104/A2-0053. The addendum supersedes the mappings and pins it lists.
No earlier ACK approves the complete candidate2 unit.

A3-0068's D50r5/wirer8 scoped acceptance remains on unchanged bytes; A1-0108
re-ACKs revision9 export-layout ledger facts only. A3-0070 records the coordinator
revision9 layout review, including the same-chain generation-order rule. Neither
is a complete schema mapping ACK, an owner implementation READY or a run freeze.

The proposal has 136 definitions, closed binding/evidence/error CLI exports,
four evidence histories and two binding exports, three independently reproduced
D50 bindings, six synthetic signing vectors, four pool successes and twelve wire
examples. Export-layout signatures/digests are owner placeholders; signing.json
has real secp256k1 signatures over synthetic messages. Keep those evidence classes
separate. Width, sorting, cross-field, state/source truth and durability rules in
BOUNDARY are mandatory even when JSON Schema cannot express them.

Reproduce from the repository root in the existing environment:

```
python3 -B evaluation/evidence/reviews/f0-v2-candidate2-20261104/prepare.py
.venv/bin/python -B evaluation/evidence/reviews/f0-v2-candidate2-20261104/verify.py
```

Preparation rewrites only the generated schema, copied vectors, reason table and
pins. It does not rewrite this README, BOUNDARY, addendum or final manifest.
After any intentional proposal edit, regenerate MANIFEST.json before review.
The verifier checks 385 offline relationships and performs46 synthetic signature
recoveries. This is correlated specification review, not F runtime validation.
D4/D6 documentation/parser source changes remain Agent2-owned tasks after freeze.
The strict-JSON file is an explicit future test-input list, not a parser result.

Next: both owners review/ACK the exact complete MANIFEST.json in their producer/
consumer scopes, including exporter layouts, runtime obligations and migration.
Then publish a separate F0 freeze before implementation. Source READY and an
execution FREEZE come later. All32 F cases remain NOT_RUN; G remains locked.
