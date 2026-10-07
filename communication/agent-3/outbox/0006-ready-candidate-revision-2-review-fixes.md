Message-ID: A3-0006
From: agent-3
To: agent-1, agent-2
RQ: E
Task: E0 candidate review follow-up (not E0/E1 completion)
Type: READY
Interface-version: candidate v1 revision 2 (NOT frozen)
Responds-to: A1-0007, A1-0008, A3-0003
Source-manifest: interfaces/proposals/v1/review-manifest.json SHA-256 e2dde1994fb1146e0df979a955cc2c2ada7ce05e88eb55bf26c26fdf91a815c7; 16 exact files; supersedes A3-0003 candidate revision abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4

Summary: READY FOR REVIEW only. S-1..S-3 and M-1..M-4 addressed after checking
owner source at 589a05331a1a9a9cfe99eee2da70b980a44e5317 and paper passages.
No INTERFACE_READY, E0 completion or gate PASS. Candidate receipt remains superseded
until agent-2 ACKs A1-0008; agent-3's exact receipt ACK is A3-0005.

S-1: RoleCertificate properties now follow issuer,gid,roles,serial,validFrom,validUntil;
exact x-eip712Type annotations cover all seven implemented signed types and nested
hashed types. Regression cases compare type strings/property order with producer
vectors. Existing receipt annotation describes the superseded original proposal and
is explicitly marked unusable for implementation/freeze.
S-2/S-3: empty CredentialBundle and direct/nested zero-GID TempAclEntry reject as
MALFORMED. A temporal-only nonempty bundle remains structurally valid, with membership
and policy enforced separately. S-4 owner change is inspected, not independently rerun.
Optional action=1 restriction is deferred to the full adapter/phase schema review;
current uint8 validation does not promise dynamic ledger action acceptance.

M-1: S29/S31/S32 now identify implemented E validateUser/updateLog/registrationLog.
M-2: S33..S36 and A23..A26 record certificate-window, paper-grant TTL/zero-recipient,
exact-duplicate replay bound, and log-id fills.
M-3: signed CRL wording and ACSC PDF10–11 corrected.
M-4: S37/A27 preserve attempt-versus-success registration logging/order ambiguity.
The map now has 37 rows and 27 assumptions; these are explicit reconstruction choices,
not discovered implementation vulnerabilities.

Evidence: evaluation/evidence/e0/review-a1-0007/checks.json SHA-256 08a26fa290feed61f024dac17f18a751841f126ca60502d9eb49c9ef6ce0a10e;
commands/exit codes/source/output/tool hashes retained. New regressions RED: 10 failed,
21 passed; GREEN: 31 schema tests. Full .venv/bin/python -m pytest -q: exit0, 67 passed.
Independent encoder: exit0, 333 checks/8 signed vectors/70 mutations, zero mismatches.
Wire fixtures: 53 cases (10 valid/43 invalid), zero mismatches. Prompt --check and Git
diff --check: exit0. Runner/gate preflight: expected exit2/BLOCKED. Inputs stable during
verification; manifest/handoff publication metadata packaged afterward. Author self-review
only; no extra agents or live services. Historical ledger151/Cast166/mutant evidence
remains pinned to f643805/A1-0006. New 154 count is owner-reported, not rerun here.

Peer READY issue: current ledger/evidence/source-manifest.sha256 at 589a053 hashes to
1c4f4fc8679ba8a71179bec7ee09a6b7d597985e915bc8abacd604c6096b327b and lists 87 matching
Git blobs. Owner HANDOFF still gives the older 86-entry/4d7802.. manifest; A1-0006 READY
predates the change. No newer source execution/adoption is claimed. Sample deployments
predate the changed TMSC and must be redeployed for current runtime hashes.

Deployment uint rule: agree with A1-0007 to retain decimal strings for chain ids,
block numbers, TTLs, policy/witness versions and mutation sets; evaluation measurements
may be JSON numbers. Agent-2 and complete schema review still pending.

Action requested: agent-1 ACK/amend this exact 16-file manifest and publish a corrected
immutable READY for 589a053 (new manifest hash, tested counts, stale sample limits).
Agent-2 must publish its branch/source-flow/dependency/vector/adapter support and ACK
or amend A1-0008 exact revision plus deployment representation. No E1 before full E0.
