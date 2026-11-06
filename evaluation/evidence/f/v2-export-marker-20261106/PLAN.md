# C-F1 exporter framing and physical marker join

Execute the accepted F0/C-F1 plan; no shared contract revision. Internal API
`verify_export_snapshot(stdout, *, stderr, exit_code, kind, snapshot, manifest,
observations, expected_owner, compiled_max_admins=None)` composes the existing
anchored binding and declared signed-history checkers with exact captured marker
bytes. `kind` is BindingExport or WitnessEvidence. Caller supplies all context.

1. Write positive and refusal tests; retain genuine missing-module RED.
2. Enforce exit0/empty stderr/canonical one-line ASCII JSON with one LF. Parse
   marker bytes strictly (no duplicate keys or nonfinite JSON), with whitespace
   permitted because the marker's serialized encoding is not specified.
3. Compare physical marker's closed schema2/owner/digest to the verified export.
   For witness evidence require equality with its declared marker and run all
   signed-history checks. Return counts plus raw stdout/marker/logical hashes.
4. Test real synthetic locked SQLite snapshots and WAL-only logical changes;
   demonstrate that a matching marker does NOT prove row completeness.
5. Review, deliberate bypass controls, focused/root tests under complete source
   brackets; exact peer reads/pins; owned checkpoint and normal agent3 push.

Ruling: reuse binding_context_v2/witness_history_v2 rather than duplicate their
trust/context rules. The new composition checks framing and physical marker
binding only. A producer-specific row projection awaits reviewed full owner
READY and exact storage/path/locking choreography; no private schema is assumed.
Raw snapshots remain private. No store identity authentication, exporter-row
completeness, native fact, arrival/timing, persistence/power-loss or gate claim.

Ruling: execute inline and review own diff because the user forbids extra agents
and worktrees. Review is correlated. User already authorizes this accepted-plan
continuation and normal owned publication; no renewed design approval needed.
