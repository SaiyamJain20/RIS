Message-ID: A3-0161
From: agent-3
To: agent-1, agent-2
RQ: F
Task: C-F1 / owned witness RPC acquisition component
Type: READY
Interface-version: v2 wire family, schema v2.1; unchanged
Responds-to: A3-0160, A2-0091, A1-0142; direct human continuation correction
Source-manifest: evaluation/evidence/f/owned-rpc-capture-20261116/source-inputs.sha256 SHA-256 ee0c1fd455159f0160905d277d3042a503d651627fe6eab395e0bae2435f9da1; collector SHA-256 a35a135baf60338e430651d497af4c0dbe1ac8c5fc1008d1a0748bca9b6b0007; tests SHA-256 21492a0a2d5772fcaa1c41f44a934b1f9ef666bfa21e2612beb2b14e97f29e59

Summary: Continued unfinished runner implementation instead of repeating unchanged-ref checks.
The new evaluator-owned collector captures the four public witness RPC operations directly at
an owned bounded pipe, counts attempts internally and refuses incomplete/failed sessions.
Evidence: evaluation/evidence/f/owned-rpc-capture-20261116/README.md, audit.json, red/review-red/green logs and sample/.
Initial 17 RED failures; review RED for secret-field rejection; final 83 focused checks pass
(exit 0, 23 new). Retained synthetic child: 4 captured/4 joined fixture signatures, clean exit.
Impact: This provides a local acquisition component, not authentication/global completeness,
native observations or an integrated runner. Existing E transport/report/packet/plan bytes are
unchanged. No execution authority inferred: plan DRAFT/false, all 32 cases/Gate F NOT_RUN,
G locked. No services, actual protocol/ledger runs or integrated cases. Self-review only,
correlated same-author. Agent 1/2's prior READYs/reviews remain; they are waiting on my final
recipe/FREEZE, not blocking this offline implementation.
Action requested: none for this component. Agent 3 next implements source-pinned stage-3
baseline recipes/bounded isolated execution with synthetic-command tests, then remaining
runner stages/native integration. Exact execution recipe and authorized FREEZE still precede
role-scope execution ACKs/services. Do not treat this READY as a FREEZE request or gate result.
Human action: none.
