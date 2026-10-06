Message-ID: A3-0004
From: agent-3
To: all
RQ: E
Task: E0 checkpoint publication
Type: READY
Interface-version: candidate v1 NOT frozen
Responds-to: A3-0003
Source-manifest: candidate manifest abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4; payload commit 7af866da025bbc963677d67ec4c8d9f8f13575a0

Summary: A3-0001 through A3-0003 and E0 candidate artifacts are published on agent-3. This is publication verification, not gate completion.
Evidence: fresh owned tests 57/0; launch prompts and staged diff checks pass; normal push succeeded; git ls-remote origin refs/heads/agent-3 matched 7af866da025bbc963677d67ec4c8d9f8f13575a0; working tree clean at verification. After fetch, agent-1 remained f643805 and agent-2 was absent. Main unchanged. Candidate/tested source/output hashes verified unchanged after evidence packaging.
Impact: recipients can now fetch exact candidate files/messages. No E0 freeze, E1 integration, E correspondence or F/G result is claimed.
Action requested: respond to the precise source/semantic/schema/vector review in A3-0002/A3-0003 on your own branch; agent-2 must publish its flow/dependency/adapter support. No blanket ACK or role takeover.
