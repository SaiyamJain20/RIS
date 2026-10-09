# C-E2 subject-substitution oracle preparation

The independent pre-release oracle is implemented; the public collector is not.
Fresh root verification: `.venv/bin/python -m pytest -q` exits 0, 670 tests in
108.45s (108.65s command wall time). Subject checks: 71 synthetic tests, exit 0.
No new integrated catalog comparison, service, release, result classification or
gate result. The 44 remaining comparisons and four BLOCKED paper crash
classifications are unchanged. E/RQ1 remains active; F/G remain locked.

`evaluation/oracles/subject.py` checks the first unfinished frozen E01 case:
alter only Alice's GID to Bob, retaining the original request reference and
verified records; repaired-e retains the original ALLOW certificate and
signature bytes as well. It requires the original logged FORWARDED request,
fresh grant/nonces, live observation time and complete decoded histories.
Paper observations must contain exactly one allowed Bob grant and access event,
the original credential digest, configured relay, canonical 30-second grant
TTL and zero native recipient. Only that grant/access/history delta is allowed.
Repaired observations must show WRONG_SUBJECT (3), no events and whole-state
rollback. Worker state must remain unchanged in this pre-release stage.

The oracle labels these **synthetic observations**, not live findings. Its
returned SPEC_GAP/REPAIR_SUPPORTED values test the expected classifier branches;
they do not change catalog status. Caller-verified signatures, transaction
calldata/sender/destination, public ABI decoding and historical block anchors are
explicit preconditions for the future collector. The oracle does not verify
cryptography, recipient routing, decryption or controls. `releaseTested=false`
prevents the pre-release check from being mistaken for an end-to-end result.

Expectations precede observation: frozen subject cases (copied here without
editing their originals), SPEC4/E01, D35/A38 and source-map S09/S12/S13/S20.
The configured-relay compromise violates the paper isolation assumption A01;
this is reconstruction/specification-gap stress, not an HMBC vulnerability.
Original authors' executable implementation remains unavailable. No JANUS,
actual ABE, Byzantine consensus, delivery or power-loss conclusion.

## Verification and provenance

Initial oracle RED: 67 failures for the missing module, exit 1; GREEN: 67, exit 0.
Supplemental bracket tests initially failed because the new `relay` argument
was missing from the function signature; this was not feature-sensitive RED.
The first corrected bracket run exposed only the action check because the
caller/clock fixtures also violated other joins. Strengthened coherent false
observations produced the intended RED: 3 failed, 1 passed; restored checks give
71 GREEN. These attempts and corrections are preserved in subject-* manifests
and stdout/stderr. No RED result is counted as live security evidence.

The root suite's 106 recorded source/paper/schema/fixture/lock inputs match
before and after exactly. Fresh author audit exits 0: 303 selected immutable
owner blobs and 15 frozen copies verify. Python 3.13.13, eth-account 0.14.0,
jsonschema 4.26.0, pytest 9.0.2 and Git 2.54.0; versions and hashes in audit.json,
verification.json and suite-source-before.json. Synthetic strings in unit
observations are not native transactions or authenticated messages. No tools
or dependencies were installed or changed. Review is by Agent 3, weaker than
independent review; extra agents are prohibited by the human instructions.

The audit helper had three failures: missing repository import path; a false
assumption that the entire remote ledger tree equalled the older selected pin;
and an attempt to compare frozen source copies with an absent local peer path.
Corrected audit verifies exact pinned blobs and frozen hashes and records remote
tree deltas instead of asserting equality. Ledger's newer owner tools/evidence
are not adopted. No owner source was edited. Failed outputs are retained;
the initial audit command's JSON filename was reused by the final audit summary,
so its command metadata remains in the tool transcript, not a separate manifest.
Other failed command manifests and all stderr/stdout remain here.

Read exact new reviews A1-0057 at
73e67141e8973f4de6accc01e24220b80ba60aee / SHA-256
938467c1bd51383666f99aa53bd43af2714e04e2aa3a48c3ffa8fea73cf0e7b8
and A2-0038 at 96ebe16097a551c1f59f4554869e8b735787c738 /
e02ca3d80e35022d047eaec066c9e30b9efafa2d323573d11e4504e5593a8c3a.
No discrepancy in their stated scopes; no report/gate ACK. Repaired replay's
3.44-second wall context margin is single-trial evidence, not direct worker
clock measurement or robustness. Prior expiry failure remains untouched.
Both provenance scans resolve 170 communication paths with no divergence.

Scheduled guard acquired exclusively; separate coordinator flock held before
fetch through publication. No stale recovery. No services/lease; A3-0044 is
already RELEASED. New runtime inventory bytes invalidate reuse of its old plan
for future execution: a complete revised plan and BOTH NEW exact ACKs must
precede services. Publication and finally cleanup are recorded in automation
memory and external run
`/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T064403Z`.
Preexisting untracked scheduled-run evidence stays unstaged. No peer mailbox,
archive, frozen v1, main, worktree or history rewrite.

## Next permitted collector work

1. Build a public collector for the three subject cases. Run fresh Alice/Bob/
   wrong-admin controls and bind their actual results to this recipe/profile.
   Use separate fresh stress deployments/state: paper's substituted grant
   occupies the original derived grantId, so feeding it into the existing
   legitimate Alice grant path would collide rather than demonstrate a control.
2. Verify original user request, PBC log/credential history, policy and repaired
   checkpoint/certificate before changing only GID. Retain unchanged original
   certificate/signatures; rewriting its digest is a different experiment.
   Submit from the configured relay, capture native calldata/receipt/error,
   block-anchored views and complete decoded histories, and invoke this oracle.
3. Complete the frozen recipient boundary separately: paper grant's native
   recipient is zero; response must route to RSC.recipientKeyHash(grant.gid),
   which is Bob's registered key. Capture read-only worker/native evidence and
   original grant expiry. Check symbolic Bob completion and Alice WRONG_SUBJECT
   with that response; keep capability bytes private. This is symbolic recipient
   binding, not evidence of actual ABE policy satisfaction or delivery. Do not
   fabricate an Alice-bound audit outcome for a Bob grant.
4. Preserve fresh positive/denial controls, TTLs, custody, frozen ABI/wire and
   selected owner pins. RED/GREEN the collector and publish a COMPLETE source/
   tool/config/fixture plan, explicit FREEZE and both NEW exact peer ACKs before
   starting any integration. This preparation has no execution FREEZE or ACK
   request; the collector and its exact recipe remain unfinished.

Then finish the other E01/E02/E03 schedules, live mutants/revocation windows,
RQ1 report and three same-report/source ACKs before any gate E claim.
