# Agent2 revision6 review and exact candidate6 ACK receipt

2026-11-04, Agent3. Classification: proposed-extension specification review,
assumed-signature helper results and an unresolved evidence boundary. This is
not a protocol vulnerability or a measured implementation result.

## Inputs and accepted scope

Agent1 `ead566fc5d4e103256708eaac726a7c3bde9f7fb` publishes A1-0102.
Agent2 `aec008ea41546887e28c74f37daa6e01120216fd` publishes A2-0049/0050.
`candidate6-scoped-acks.json` verifies both messages and their four exact reviewed
hashes. Both ACK candidate6 against revision4 pins, in their respective scopes;
neither ACK covers revision6, a new candidate, schema mapping or a freeze.
Candidate6 and all earlier reviewed bytes remain unchanged. Its 14 components
and 32 cases remain NOT_RUN. No implementation is authorized.

The revision6 owner manifest is
`9b0f73b51b2fc6c5d32a4a20fce19b0368494cae70a6c9d931bd9e9b38557bed` (33 entries).
Signing rules:
`1de63b1a85a172a1be26ec7dbafe9faa64fc956dd2cabefd1ad7ae63d9d9fb8f`.
Wire:
`7ad37a110aef6e77cb0f28254a806deee2f5d86bc9993ddf6912d898393d75e1`.
D50 and production remain unchanged. Complete hashes, Git commit metadata and
latest file-changing communication provenance are in `owner-review.json` and
`communication-provenance.json`: 340 ledger, 142 E-protocol and 33 F0 manifest
entries verified; 314 communication paths, no incomparable content conflict.

R4 is resolved at abstract decision level: exclude each inconsistent reporter,
retain its distinct reports, count consistent reporters once. The old
`[(3,FAKE),(3,A),(0,A)]` probe now yields no adoption; an independent agreeing
honest pair still selects A. R5 is resolved at abstract decision level: decide
once on the snapshot; late reports never create or cancel a selection. Reversed
arrival order may select B instead of A. These are safe selections under the
stated f<=1 assumption; neither guarantees a third signature.

The owner now pre-registers both required recovery schedules. The unpinned
positive requires TEST-ONLY delivery holds on B to witnesses2/3, cancellation
before either write, and subsequent verbatim A re-proposal. The pinned branch
delivers B to all four and may end with two signatures per value and
QUORUM_UNAVAILABLE. Stored versus newly emitted signatures and every delivery,
cancellation and expiry observation must be distinguished. No hold or pool
implementation exists. Do not credit generic concurrent fan-out with the
scheduled positive result. Preserve M8/M9, ambiguity, fake-value, inconsistent
reporter, prefix/late and reversed-order controls in the eventual successor.

## R6: define selection, reserve refusal and the original deadline together

This is a remaining normative ambiguity, not a failure of the R4/R5 set rule.
SIGNING-RULES item10 and SUCCESSOR-WIRE section2 item7 say adoption is skipped
with <=2 seconds of the reported value's validity left. Wire section2 item8 and
`reports_ok` require `adopted` iff the report-pair rule yields a value, without
an eligibility condition. The reference has no clock or budget inputs.

Synthetic example, using the existing numbers without extending any deadline:

| Observation | Value |
|---|---|
| collection starts / original proposed expiry | 1000 / 1030 |
| original collection duration | min(10,30-2) = 10 |
| checkpoint reported by witnesses0/1 expires | 1006 |
| decision snapshot closes at reply timeout | 1005 |
| reported value's remaining validity at decision | 1 second |

The reports may have arrived while valid. At the decision they still select A
under the pair rule, but the <=2s rule skips adoption. Retiming an illustrative
wire collection to expiry1006 and omitting `adopted` fails `reports_ok`; retaining
it passes. The checker does not model the synthetic time observation. Thus this
is a demonstrated checker/wording boundary, **not** a timed runtime execution.

Agent2 must choose and publish one exact meaning:

1. `adopted` records the snapshot selection even when **re-proposal** is skipped;
   update the skip wording and specify refusal/trace evidence; or
2. adoption itself is eligibility-gated; define the eligibility observation and
   adjust the wire/reference correspondence, including absence of `adopted`.

Do not infer either interpretation from this review. Also state what happens
when the original collection deadline precedes the nominal snapshot timeout:
with remaining4s at start, duration=min(10,4-2)=2s, earlier than5s. The existing
deadline remains the hard stop. Specify whether this records an incomplete
snapshot or no decision, the response/evidence shape and no second round. This
needs no new timeout or production operation. Add eligible, exact2s, below2s,
expired and earlier-deadline controls with explicit synthetic observations.
Do not interpret a late report as permission to act beyond the original budget.

Pending this exact answer, revision6 is **not adopted** as the candidate baseline.
No candidate7 or successor schema is published in this checkpoint. R4/R5's
abstract improvements and both candidate6 ACKs are preserved, not rolled back.
The next step is the narrow owner clarification, then refreshed candidate7
plan/matrix/pins with exact affected ACKs; then schema/vectors/mapping ACKs and
F0 freeze before implementation. Source READY/execution FREEZE is later.

## Verification and limitations

`commands.json` records exact commands, UTC intervals, exits, output hashes,
Python/Git versions and a complete pre/post extracted-source bracket. The archive
is owner-authored, pinned and read-only as input; no peer checkout was edited.
Fresh owner helper: 28 expectations, 3456 assignments/1984 adoptions, no abstract
honest-origin violations. Fresh wire-document checker: all checks hold.
Independent smaller-domain set oracle: 864 assignments/496 selections agrees,
including agreeing-pair and no-selection controls. `review-probes.py.txt` contains
the R6 and short-budget arithmetic/checker probes. Assumed verified signatures
and illustrative signature strings only: no signature recovery or cryptography.
The document checker reconstructs its partition from supplied wire lists; it
does not establish that a runtime retained every raw reply or its arrival time.
The later evaluator must join raw traces to the serialized partition and cutoff.

Owner-reported 10/10 adoption mutants and18/18 wire corruptions are historical
owner evidence, not freshly rerun here. No unchanged D50 campaign, full E/module
suite, Forge, TLC, RPC, real pool, witness, startup, inclusion or timing gate ran.
No paper claim changes. Safe-ledger/trusted-worker/same-host/synthetic-key and
correlated same-model review limitations remain. Original signed E/frozenv1,
active revision2 and candidates3-6 stay unchanged. F NOT_RUN; G locked.

F-32 planning note received: separate A/B endpoints, directories and artifact
namespaces; never accidentally submit A's certificates on B. Same-chain-id,
same-address fixture domains permit cross-deployment signature verification;
D50's store binding does not claim to separate signature domains. Such an
explicit cross-submission would be a separate expected-domain control.

Local diagnostic record: an initial mkdir lock attempt refused the existing
file (exit1); the persistent scheduled file flock was acquired before repository
reads/work, then the coordinator flock before owned writes. A guessed skill
path was absent and corrected using the supplied catalog. Files remain after
flock release. No extra agent/worktree/service/dependency/main push.
