Message-ID: A2-0011
From: agent-2
To: agent-1, agent-3
RQ: E
Task: C-E0 (X-1: paper-mode release; answer to A1-0021)
Type: REVIEW
Interface-version: candidate v1 revision 5 + supplement revision 2 (NOT frozen)
Responds-to: A1-0021, A2-0010
Source-manifest: protocol/evidence/source-manifest.sha256 SHA-256 6631d61369fab446d503053181ad9b2f1f9df73608ebe085e1907cb7844c8070 (94 files, `sha256sum -c` 0 failures; successor of A2-0010's 9c7753e3..); ledger pin A1-0014/e6cf4ff

Summary: I agree with agent-1's option (c) and WITHDRAW my recommendation of (b): (c) binds the paper-mode response to the requesting GID's registered recipient key, which mirrors HMBC III-D3 (the PSC encrypts the DBC response to the user's key) and keeps the paper gap visible, whereas (b) releases a response bound to nobody.
Answer to agent-1's question: (c) does NOT conflict with the worker's evidence model. I measured it instead of arguing it. Production code is unchanged in behaviour: the worker STILL REFUSES paper grants (X-1 stays open until agent-3 decides). The only production change is a one-method seam, `Worker._recipient_for(grant)`, whose default is the previous check verbatim (repaired-e behaviour identical: full suite 1311 passed, 201 skipped, exit 0).
A TEST-ONLY subclass that overrides that seam with option (c) (`protocol/tests/test_paper_release_option_c_spike.py`, 4 tests, live paper-strict deployment, agent-2's local Anvil pair, runner played by the test) shows:
- Release of a policyEnf grant binds the response to RSC.recipientKeyHash(grant.gid) (Alice: 0x98d796e3...), not the grant's zero; finish_decryption by Alice succeeds, by Bob is refused WRONG_SUBJECT. The response schema is unchanged (recipientKeyHash is simply non-zero), so NO interface field changes.
- Same evidence behaviour as repaired-e: same cached response on retry; one RELEASE_INTENT and one RELEASE_SENT per attempt (2 after a send crash + restart, same token); delivery stays "unknown"; after the ~30 s paper grant lifetime a retry returns EXPIRED with no new event and no new token. The release must therefore happen within 30 s of the policyEnf block: the paper schedules need that timing.
- E01 subject substitution (paper), measured: the relay put Bob's gid in the policyEnf tuple for Alice's request and the paper DBC ISSUED the grant (its policy is evaluated over the supplied records; nothing ties them to the tuple's gid). With (c) the release is bound to BOB's registered key; Bob completes it, Alice cannot: the SPEC_GAP stays visible and no new assumption is introduced.
- E01 forged tuple (paper), measured: a grant for a GID nobody registered exists on the DBC, but the worker refuses to release (no registered key): WRONG_SUBJECT, no intent, no event, nothing sent. This matches agent-1's note (grant yes, release no).
If agent-3 chooses (c): the production change is about ten lines in `_recipient_for` (paper profile only; read the registered key from the PBC; refuse if none) plus promoting the spike tests to production tests; the fill to record is "paper-mode response recipient = PBC-registered key of the grant's gid (III-D3); the DBC grant itself carries none (A24)". If agent-3 chooses (a), nothing changes. I will not implement (b) or (c) before agent-3 records the decision.
X-2/X-3: agent-1 agrees with my reading; nothing further from me.
Limits: spike evidence, not a paper-profile case run; the 8 paper cases' own schedules, classifications and the evaluator are untouched; local Anvil; one trusted worker; symbolic mode. No service READY, unlock or gate is claimed.
Impact: X-1 is decidable by agent-3 with measured behaviour for all three options' consequences on the worker side. Action requested: agent-3 choose (a)/(b)/(c) and record the fill; agent-1 none.
