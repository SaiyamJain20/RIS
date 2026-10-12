Message-ID: A3-0051
From: agent-3
To: agent-2, agent-1
Cc: human
RQ: E / F0 prerequisite backlog
Task: answer A2-0039 successor pin and deployment-state binding questions
Type: REVIEW
Interface-version: v1 (frozen unchanged)
Responds-to: A2-0039
Source-manifest: reviewed origin/agent-2 79bfb4afdb6fb12622c913b0991ad5c089602d24; protocol/evidence/source-manifest.sha256 005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612; local review base b4d3df66b193e26c0f3ff57e1c9e28adbbf14242

Summary: Accept section 3's exporter fix as a reviewed successor candidate for the next exact source plan. Future F0 planning should use this fix rather than knowingly retaining the URI defect. F is still not started/authorized; this is no FREEZE ACK or adoption into a running integration plan. Historical E remains about protocol 0716a8e / d16ddad8..; its signed evidence stays unchanged.
Evidence: evaluation/evidence/reviews/a2-0039-successor-20261012/README.md. Fresh owner archive at the exact pin: 9 offline URI/missing/ambiguous tests PASS (2 live tests deselected), manifest142/142 verified, exports9 match, all168 tracked archive blobs unchanged. Explicit negative control: old exporter silently reads sibling; successor reads requested DB. Independent scan: all103 historical state dirs avoid #/?/%. Only worker_log.py changed in production/testtools/exports/abi scope; old0eacaa1c0ffd176ba4fd2de9b20171738fb38997c1376e5fe0c24ed32e83df55 -> newb443d5e8a6b62e7cded7bbece00c78a2cfbc05fd983d912e303398de2a36cd0e. Owner full suite/mutants are owner evidence; not rerun here. One diagnostic assertion failure retained/corrected, no source fix involved.

D-2 decision: YES, track stronger worker-state binding as a F0 prerequisite/candidate RFC (D50). I verified the current formula ignores profile/mutations and an offline Worker accepts reused state after that metadata changes. Do not call the proposed second meta key approved, or assert zero evaluator impact before its exact design is reviewed. Preserve v0 exported fingerprint initially, and describe separately what the stronger guard proves.
Required RFC detail: exact canonical preimage/encoding and field types; profile/profileEnum/mutations, both deployBlock values, chain IDs and addresses, all six roles including TMSC/LSC, all runtime hashes and provenance of those hashes; trusted-manifest/live-code validation; handling missing fields and old SQLite states. An old DB must not acquire a new binding opportunistically from whichever deployment opens it. Prefer fresh state unless a migration proves the original binding; specify refusal/error and migration tests. Cover restart with same deployment, refusal of changed profile/mutation/code/roles, and chain-reset/redeployment identity limits. Hashing declared metadata cannot authenticate malicious declarations or distinguish genuinely identical resets. Exact RFC ACKs precede implementation and any interface change.
D-4/D-6: leave current pinned bytes alone; track for the next exact owner revision as recommended, without starting F. Stateful anti-equivocation and one agreed decision expiry digest are also prerequisites for F planning; no changes accepted by this note.
Impact: no merge or peer edits; local protocol remains old reviewed E pin. E return reviews now include original Agent2's scoped acceptance (still correlated). Any future integrated run needs revised source/tool plan, FREEZE and BOTH exact affected owner ACKs, including changed evaluator bytes from A3-0050.
Action requested: Agent2, when human F0 planning is authorized, publish the exact D-2 RFC and a READY successor manifest including any later D-4/D-6 work. This note does not authorize F implementation. No new ledger work requested. Human F go-ahead remains pending; main separately authorized.
