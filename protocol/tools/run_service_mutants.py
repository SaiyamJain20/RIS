"""Mutation check of the witness service, StateCheckpoint, AccessDecision, GrantReceipt and GovernanceAction paths (agent 2, F task 2 slices 4a to 4d). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_witness_service.py tests/test_witness_service_decision.py and tests/test_witness_service_receipt.py and tests/test_witness_service_governance.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. witness_state.py is NOT mutated here (run_state_mutants.py does that).

Usage (repository root):   python3 -B -I protocol/tools/run_service_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
Exit 0 only when every mutant is detected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
SRC = open(os.path.join(PROTO, "hmbc_protocol", "witness_service.py")).read()

M = [
    ("V1 the psc is not compared with the deployment's", [(' or cp["psc"] != self._psc:', ":")]),
    ("V2 the source chain id is not compared", [('if cp["sourceChainId"] != self._pbc_id or cp["psc"] != self._psc:', 'if cp["psc"] != self._psc:')]),
    ("V3 the next sequence is current plus two", [('1 if current is None else int(current["sequence"]) + 1\n', '1 if current is None else int(current["sequence"]) + 2\n')]),
    ("V4 a gap in the sequence is accepted", [('if int(cp["sequence"]) != expected:', 'if int(cp["sequence"]) < expected:')]),
    ("V5 a block after the observed head is accepted when the read succeeds", [('if block is None or n > int(head["blockNumber"]):', "if block is None:")]),
    ("V6 the block hash is not compared", [('if block["hash"] != cp["sourceBlockHash"]:', "if False:")]),
    ("V7 a block equal to the DBC current block is refused", [('n < int(current["sourceBlockNumber"])', 'n <= int(current["sourceBlockNumber"])')]),
    ("V8 the DBC current block is not a lower bound", [('if current is not None and n < int(current["sourceBlockNumber"]):', "if False:")]),
    ("V9 keyEpoch is not checked", [('if cp["keyEpoch"] != "0":', "if False:")]),
    ("V10 the configured witnessSetVersion is not compared", [('if cp["witnessSetVersion"] != self._wsv or cp["witnessSetVersion"]', 'if cp["witnessSetVersion"]')]),
    ("V11 the witnessSetVersion read at the block is not compared", [(' or cp["witnessSetVersion"] != reads["witnessSetVersion"]:', ":")]),
    ("V12 the epochs at the proposal's block are not compared", [("            if cp[f] != reads[f]:", "            if False:")]),
    ("V13 the epochs at the witness's own head are not compared (no stale-view refusal)", [("            if cp[f] != head_reads[f]:", "            if False:")]),
    ("V14 the epochs are read at the head instead of at the proposal's block", [("        reads = view.reads_at(n)", '        reads = view.reads_at(int(head["blockNumber"]))')]),
    ("V15 the freshness read repeats the block read", [('head_reads = view.reads_at(int(head["blockNumber"]))', "head_reads = reads")]),
    ("V16 an expiry equal to the observation is accepted", [("        if e <= ts:\n            raise WitnessRefusal(\"EXPIRED\", None, \"expiresAt is not after the DBC", "        if e < ts:\n            raise WitnessRefusal(\"EXPIRED\", None, \"expiresAt is not after the DBC")]),
    ("V17 an expiry exactly at the window edge is refused", [("        if e > ts + self._max_ttl:", "        if e >= ts + self._max_ttl:")]),
    ("V18 the window has no upper bound", [("        if e > ts + self._max_ttl:", "        if False:")]),
    ("V19 the window observes the PBC instead of the DBC", [('ts = int(view.observe("dbc")["timestamp"])', 'ts = int(view.observe("pbc")["timestamp"])')]),
    ("V20 the store is told no expiry", [("expires_at=cp[\"expiresAt\"],", "expires_at=None,")]),
    ("V21 the store observes the PBC (checkpoint)", [('observe=lambda: self._view.observe("dbc"),\n                                overtaken=("overtaken-checkpoint"', 'observe=lambda: self._view.observe("pbc"),\n                                overtaken=("overtaken-checkpoint"')]),
    ("V22 the store gets another domain", [('domain=self._domain,', 'domain="0x" + "00" * 32,')]),
    ("V23 an unreadable ledger escapes as a raw exception", [("        except LedgerUnreachable as e:\n            raise _unreachable(e) from None\n        except ws.StoreError as e:", "        except ws.StoreError as e:")]),
    ("V24 the recorded value is dropped from a pinned refusal", [("raise WitnessRefusal(e.code, e.reason, e.message, e.recorded) from None", "raise WitnessRefusal(e.code, e.reason, e.message, None) from None")]),
    ("V25 the proposal's shape is not validated", [("return dict(wire.state_checkpoint(proposal))", "return dict(proposal)")]),
    ("V26 the proposer's sequence is current plus two", [('str(int(cur["sequence"]) + 1)', 'str(int(cur["sequence"]) + 2)')]),
    ("V27 the proposer's expiry is twice the ttl", [('str(int(dbc["timestamp"]) + ttl)', 'str(int(dbc["timestamp"]) + 2 * ttl)')]),
    ("V28 the overtaken evidence claims a far sequence", [('"0" if current is None else str(current["sequence"])', '"99"')]),
    ("V29 the maximum window default is 61 s", [("DEFAULT_MAX_TTL = 60", "DEFAULT_MAX_TTL = 61")]),
    ("V30 the proposer's default ttl is 31 s", [("DEFAULT_PROPOSER_TTL = 30", "DEFAULT_PROPOSER_TTL = 31")]),
    ("V31 the effect carries the sequence key instead of the source block hash", [('EFFECT = ("authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash")', 'EFFECT = ("authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockNumber")')]),
    ("V32 the conflict key is the block number instead of the sequence", [('key=cp["sequence"],', 'key=cp["sourceBlockNumber"],')]),
    ("V33 the proposer reads the epochs at block 0", [('reads = view.reads_at(int(head["blockNumber"]))\n    dbc = view.observe("dbc")', 'reads = view.reads_at(0)\n    dbc = view.observe("dbc")')]),
    ("V34 a non-positive max ttl is accepted", [("or max_checkpoint_ttl < 1:", "or False:")]),
    ("D1 an outcome already recorded (status 2) is not refused", [('    if rec["status"] == "2":', "    if False:")]),
    ("D2 a request the PSC has not forwarded is not refused", [('    if rec["status"] != "1":', "    if False:")]),
    ("D3 two forwarding logs are accepted", [("    if len(logs) != 1:\n        raise _refusal(\"WRONG_SUBJECT\", \"expected exactly one AccessForwarded", "    if len(logs) < 1:\n        raise _refusal(\"WRONG_SUBJECT\", \"expected exactly one AccessForwarded")]),
    ("D4 no forwarding log escapes as a raw exception", [("    if len(logs) != 1:\n        raise _refusal(\"WRONG_SUBJECT\", \"expected exactly one AccessForwarded", "    if len(logs) > 1:\n        raise _refusal(\"WRONG_SUBJECT\", \"expected exactly one AccessForwarded")]),
    ("D5 the forwarding transaction need not go to the PSC", [('call is None or call["to"] != psc or call["method"] != "requestAccess":', 'call is None or call["method"] != "requestAccess":')]),
    ("D6 the forwarding call need not be requestAccess", [('call is None or call["to"] != psc or call["method"] != "requestAccess":', 'call is None or call["to"] != psc:')]),
    ("D7 the recovered request need not hash to the digest", [("    if recomputed != digest:", "    if False:")]),
    ("D8 the PSC record is not compared with the request", [('    if tuple(request[k] for k in ("gid", "dataId", "destinationChainId", "kssc", "expiresAt")) != tuple(rec[k] for k in ("gid", "dataId", "destinationChainId", "kssc", "expiresAt")):', "    if False:")]),
    ("D9 a checkpoint expiring exactly now is fresh", [('dbc_now >= int(cp["expiresAt"]):', 'dbc_now > int(cp["expiresAt"]):')]),
    ("D10 a missing checkpoint escapes as a raw exception", [('    if cp is None or dbc_now >= int(cp["expiresAt"]):', '    if dbc_now >= int(cp["expiresAt"]):')]),
    ("D11 the checkpoint's block hash is not compared", [('block is None or block["hash"] != cp["sourceBlockHash"] or view.reads_at(src)["authEpoch"] != cp["authEpoch"]:', 'block is None or view.reads_at(src)["authEpoch"] != cp["authEpoch"]:')]),
    ("D12 the checkpoint's authEpoch is not compared with the block's", [('block is None or block["hash"] != cp["sourceBlockHash"] or view.reads_at(src)["authEpoch"] != cp["authEpoch"]:', 'block is None or block["hash"] != cp["sourceBlockHash"]:')]),
    ("D13 the checkpoint's witnessSetVersion is not compared", [('    if cp["witnessSetVersion"] != wsv:', "    if False:")]),
    ("D14 a request forwarded in the checkpoint's own block is refused", [('    if int(logs[0]["block"]) > src:', '    if int(logs[0]["block"]) >= src:')]),
    ("D15 a request forwarded after the checkpoint's block is accepted", [('    if int(logs[0]["block"]) > src:', "    if False:")]),
    ("D16 the request's authEpoch is not compared with the checkpoint's", [('if request["authEpoch"] != cp["authEpoch"] or request["policyVersion"] != cp["policyVersion"]:', 'if request["policyVersion"] != cp["policyVersion"]:')]),
    ("D17 the request's policyVersion is not compared", [('if request["authEpoch"] != cp["authEpoch"] or request["policyVersion"] != cp["policyVersion"]:', 'if request["authEpoch"] != cp["authEpoch"]:')]),
    ("D18 the request's keyEpoch is not compared", [('    if request["keyEpoch"] != cp["keyEpoch"]:', "    if False:")]),
    ("D19 the destination chain is not compared", [('if request["destinationChainId"] != dbc["chainId"] or request["kssc"] != dbc["contracts"]["KSSC"]:', 'if request["kssc"] != dbc["contracts"]["KSSC"]:')]),
    ("D20 the KSSC is not compared", [('if request["destinationChainId"] != dbc["chainId"] or request["kssc"] != dbc["contracts"]["KSSC"]:', 'if request["destinationChainId"] != dbc["chainId"]:')]),
    ("D21 a consumed nonce is not refused", [('view.nonce_consumed(request["gid"], request["nonce"]) is True:', 'view.nonce_consumed(request["gid"], request["nonce"]) is None:')]),
    ("D22 only the DBC clock decides request expiry", [('if max(dbc_now, pbc_now) >= int(request["expiresAt"]):', 'if dbc_now >= int(request["expiresAt"]):')]),
    ("D23 a request expiring exactly now is live", [('if max(dbc_now, pbc_now) >= int(request["expiresAt"]):', 'if max(dbc_now, pbc_now) > int(request["expiresAt"]):')]),
    ("D24 a credential valid until exactly now is not lapsed", [('int(r["validUntil"]) <= dbc_now', 'int(r["validUntil"]) < dbc_now')]),
    ("D25 the policy is evaluated even when the credentials failed", [('satisfied = code == "0" and view.policy_satisfied(request["dataId"], records) is True', 'satisfied = view.policy_satisfied(request["dataId"], records) is True')]),
    ("D26 the decision expiry is the later of request and checkpoint", [('str(min(int(request["expiresAt"]), int(cp["expiresAt"])))', 'str(max(int(request["expiresAt"]), int(cp["expiresAt"])))')]),
    ("D27 the decision expiry ignores the request's", [('str(min(int(request["expiresAt"]), int(cp["expiresAt"])))', 'str(int(cp["expiresAt"]))')]),
    ("D28 lapsed records are still attested", [('code, records = "REVOKED-BY-TIME", []', 'code, records = "REVOKED-BY-TIME", records')]),
    ("D29 the credentials are evaluated at the witness's own now", [('view.credentials(request["gid"], call["bundle"], block["timestamp"], src)', 'view.credentials(request["gid"], call["bundle"], str(dbc_now), src)')]),
    ("D30 the expiry is not compared with the proposal", [('DECISION_FIELDS = ("requestDigest", "result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash", "expiresAt")', 'DECISION_FIELDS = ("requestDigest", "result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash")')]),
    ("D31 the stateSequence is not compared with the proposal", [('DECISION_FIELDS = ("requestDigest", "result", "credentialDigest", "stateSequence",', 'DECISION_FIELDS = ("requestDigest", "result", "credentialDigest",')]),
    ("D32 the credentialDigest is not compared with the proposal", [('DECISION_FIELDS = ("requestDigest", "result", "credentialDigest",', 'DECISION_FIELDS = ("requestDigest", "result",')]),
    ("D33 the decision is recorded under the checkpoint domain", [("domain=self._decision_domain,", "domain=self._domain,")]),
    ("D34 the decision's key is the state sequence", [('key=own["requestDigest"], effect={k: own[k] for k in EFFECT_DECISION},', 'key=own["stateSequence"], effect={k: own[k] for k in EFFECT_DECISION},')]),
    ("D35 the overtaken evidence is always zero", [('overtaken=("overtaken-decision-sequence", own["stateSequence"])', 'overtaken=("overtaken-decision-sequence", "0")')]),
    ("D36 the decision effect lacks a field", [('EFFECT_DECISION = ("result", "credentialDigest",', 'EFFECT_DECISION = ("result", "result",')]),
    ("D37 the request digest's shape is not checked", [("        wire.hash32(digest)\n", "        str(digest)\n")]),
    ("D38 the decision proposal's shape is not checked", [("prop = dict(wire.access_decision(proposal))", "prop = dict(proposal)")]),
    ("D39 the proposer-side derivation does not map an unreadable view", [("    except LedgerUnreachable as e:\n        raise _unreachable(e) from None\n\n\ndef _derive_decision", "    except KeyError as e:\n        raise _unreachable(e) from None\n\n\ndef _derive_decision")]),
    ("D40 the PBC clock is not read", [('dbc_now, pbc_now = view.now("dbc"), view.now("pbc")', 'dbc_now, pbc_now = view.now("dbc"), view.now("dbc")')]),
    ("D41 the decision store observes the PBC", [('observe=lambda: self._view.observe("dbc"),\n                                overtaken=("overtaken-decision-sequence"', 'observe=lambda: self._view.observe("pbc"),\n                                overtaken=("overtaken-decision-sequence"')]),
    ("R1 a grant that is not allowed gives a receipt", [('    if not g["allowed"] or "0x" + eip712.grant_id(', '    if "0x" + eip712.grant_id(')]),
    ("R2 the grant id is not recomputed from the grant", [(' or "0x" + eip712.grant_id(bytes.fromhex(g["digest"][2:]), kssc, int(dbc["chainId"])).hex() != grant_id:', ":")]),
    ("R3 a GrantIssued log after the witness's head counts", [('[x for x in view.grant_issued_logs(grant_id) if int(x["block"]) <= int(head["blockNumber"])]', "list(view.grant_issued_logs(grant_id))")]),
    ("R4 no GrantIssued log escapes as a raw exception", [("    if not logs:\n", "    if False:\n")]),
    ("R5 two GrantIssued logs are accepted", [("    if len(logs) != 1:\n        raise _refusal(\"WRONG_SUBJECT\", \"expected exactly one GrantIssued", "    if len(logs) < 1:\n        raise _refusal(\"WRONG_SUBJECT\", \"expected exactly one GrantIssued")]),
    ("R6 the PSC record's status is not checked", [('    if rec["status"] != "1" or (rec["gid"], rec["dataId"]) != (g["gid"], g["dataId"]):', '    if (rec["gid"], rec["dataId"]) != (g["gid"], g["dataId"]):')]),
    ("R7 the PSC record's gid and dataId are not compared with the grant's", [('    if rec["status"] != "1" or (rec["gid"], rec["dataId"]) != (g["gid"], g["dataId"]):', '    if rec["status"] != "1":')]),
    ("R8 the receipt names the DBC head, not the GrantIssued block (E behaviour)", [('"dbcBlockNumber": str(int(logs[0]["block"])), "dbcBlockHash": logs[0]["hash"]}', '"dbcBlockNumber": head["blockNumber"], "dbcBlockHash": logs[0]["hash"]}')]),
    ("R9 the receipt's block hash is the head's", [('"dbcBlockHash": logs[0]["hash"]}', '"dbcBlockHash": head["blockHash"]}')]),
    ("R10 the receipt's witnessSetVersion is fixed to 1", [('"witnessSetVersion": wsv,\n               "dbcChainId"', '"witnessSetVersion": "1",\n               "dbcChainId"')]),
    ("R11 the receipt's DBC chain id is wrong", [('"dbcChainId": dbc["chainId"], "kssc": kssc,', '"dbcChainId": "1", "kssc": kssc,')]),
    ("R12 the receipt's grantExpiresAt is not the grant's", [('"grantExpiresAt": g["expiresAt"],', '"grantExpiresAt": g["keyEpoch"],')]),
    ("R13 the receipt's keyEpoch is fixed to 0", [('"keyEpoch": g["keyEpoch"],', '"keyEpoch": "0",')]),
    ("R14 the receipt's kssc is wrong", [('"dbcChainId": dbc["chainId"], "kssc": kssc,', '"dbcChainId": dbc["chainId"], "kssc": "0x" + "00" * 20,')]),
    ("R15 the last effect field is not compared with the proposal", [('RECEIPT_FIELDS = ("requestDigest",) + EFFECT_RECEIPT', 'RECEIPT_FIELDS = ("requestDigest",) + EFFECT_RECEIPT[:-1]')]),
    ("R16 the receipt is recorded under the grant id", [('key=own["requestDigest"], effect={k: own[k] for k in EFFECT_RECEIPT},', 'key=own["grantId"], effect={k: own[k] for k in EFFECT_RECEIPT},')]),
    ("R17 the store is given an expiry for a receipt", [("expires_at=None, digest=", 'expires_at=own["grantExpiresAt"], digest=')]),
    ("R18 the store observes the DBC for a receipt", [('signer=self._signer, observe=lambda: self._view.observe("pbc"))', 'signer=self._signer, observe=lambda: self._view.observe("dbc"))')]),
    ("R19 the receipt is recorded under the decision domain", [("domain=self._receipt_domain,", "domain=self._decision_domain,")]),
    ("R20 the grant id's shape is not checked", [("        wire.hash32(grant_id)\n", "        str(grant_id)\n")]),
    ("R21 the proposer-side receipt derivation does not map an unreadable view", [("    except LedgerUnreachable as e:\n        raise _unreachable(e) from None\n\n\ndef _derive_receipt", "    except KeyError as e:\n        raise _unreachable(e) from None\n\n\ndef _derive_receipt")]),
    ("R22 the receipt proposal's field set is not checked", [("if not isinstance(v, dict) or set(v) != set(RECEIPT_FIELDS):", "if not isinstance(v, dict):")]),
    ("R23 a zero grantExpiresAt is accepted", [('    if int(v["grantExpiresAt"]) == 0:', "    if False:")]),
    ("R24 the receipt digest uses the decision domain", [('"domain": messages.domain_for("GrantReceipt", receipt, deployment),', '"domain": messages.domain_for("AccessDecision", receipt, deployment),')]),
    ("R25 the proposal's shape is validated with the E validator", [("prop = dict(_receipt_shape(proposal))", "prop = dict(wire.grant_receipt(proposal))")]),
    ("D42 a decision value out of range escapes as a raw exception", [('    except wire.WireError:\n        raise _refusal("WRONG_SUBJECT", "the ledger state does not form a canonical AccessDecision (a value is out of range)") from None', '    except KeyError:\n        raise _refusal("WRONG_SUBJECT", "the ledger state does not form a canonical AccessDecision (a value is out of range)") from None')]),
    ("R26 a receipt value out of range escapes as a raw exception", [('    except wire.WireError:\n        raise _refusal("WRONG_SUBJECT", "the ledger state does not form a canonical GrantReceipt (a value is out of range)") from None', '    except KeyError:\n        raise _refusal("WRONG_SUBJECT", "the ledger state does not form a canonical GrantReceipt (a value is out of range)") from None')]),
    ("G1 a deployment without Governance is not refused", [("        if self._governance_sep is None:\n            raise _refusal(\"WRONG_PROFILE\"", "        if False:\n            raise _refusal(\"WRONG_PROFILE\"")]),
    ("G2 any action number is accepted", [('v["action"] not in ("1", "2", "3") or v["root"] == ZERO_ADDRESS or', 'v["root"] == ZERO_ADDRESS or')]),
    ("G3 a zero root is accepted", [(' or v["root"] == ZERO_ADDRESS or not isinstance(admins, list)', ' or not isinstance(admins, list)')]),
    ("G4 admins need not be a list", [(" or not isinstance(admins, list) or len(admins) > MAX_ADMINS:", " or len(admins) > MAX_ADMINS:")]),
    ("G5 nine admins are accepted", [("len(admins) > MAX_ADMINS:", "len(admins) > MAX_ADMINS + 1:")]),
    ("G6 duplicate admins are accepted", [("any(x >= y for x, y in zip(admins, admins[1:]))", "any(x > y for x, y in zip(admins, admins[1:]))")]),
    ("G7 a zero admin is accepted", [("any(a == ZERO_ADDRESS for a in admins) or ", "")]),
    ("G8 ADD with no admins is accepted", [('(v["action"] == "1" and not admins) or ', "")]),
    ("G9 REMOVE with admins is accepted", [(' or (v["action"] == "2" and admins):', ":")]),
    ("G10 a future governance nonce is accepted", [('if int(g["nonce"]) != current + 1:', 'if int(g["nonce"]) < current + 1:')]),
    ("G11 a past governance nonce is accepted", [('if int(g["nonce"]) != current + 1:', 'if int(g["nonce"]) > current + 1:')]),
    ("G12 the witnessSetVersion is not compared", [('        if g["witnessSetVersion"] != self._wsv:\n            raise WitnessRefusal("STALE_STATE", "WITNESS_SET_MISMATCH", "witnessSetVersion differs from this witness\'s own")', '        if False:\n            raise WitnessRefusal("STALE_STATE", "WITNESS_SET_MISMATCH", "witnessSetVersion differs from this witness\'s own")')]),
    ("G13 ADD of an existing authority is accepted", [("            if view.is_authority(root):", "            if False:")]),
    ("G14 ADD of a tombstoned root is accepted", [("            if view.removed_authority(root):", "            if False:")]),
    ("G15 REMOVE or SET of a non-authority is accepted", [("        elif not view.is_authority(root):", "        elif False:")]),
    ("G16 the local allow-list is ignored", [('if self._allow is None or (g["action"], root, tuple(g["admins"])) not in self._allow:', "if False:")]),
    ("G17 a missing allow-list escapes as a raw exception", [('if self._allow is None or (g["action"], root, tuple(g["admins"])) not in self._allow:', 'if (g["action"], root, tuple(g["admins"])) not in self._allow:')]),
    ("G18 the allow-list ignores the admins", [('(g["action"], root, tuple(g["admins"])) not in self._allow:', '(g["action"], root, ()) not in {(a, r, ()) for a, r, _ in self._allow}:')]),
    ("G19 the allow-list aliases the caller's list", [("frozenset((a, r, tuple(ad)) for a, r, ad in allowed_governance)", "allowed_governance")]),
    ("G20 an expiry equal to the observation is accepted", [("        if e <= ts:\n            raise _refusal(\"EXPIRED\", \"expiresAt is not after the PBC's", "        if e < ts:\n            raise _refusal(\"EXPIRED\", \"expiresAt is not after the PBC's")]),
    ("G21 an expiry exactly at the window edge is refused", [("        if e > ts + self._max_gov_ttl:", "        if e >= ts + self._max_gov_ttl:")]),
    ("G22 the governance window has no upper bound", [("        if e > ts + self._max_gov_ttl:", "        if False:")]),
    ("G23 the governance window observes the DBC", [('ts = int(view.observe("pbc")["timestamp"])\n        e = int(g["expiresAt"])', 'ts = int(view.observe("dbc")["timestamp"])\n        e = int(g["expiresAt"])')]),
    ("G24 the action is recorded under the checkpoint domain", [("domain=self._governance_sep,", "domain=self._domain,")]),
    ("G25 the action is recorded under its root, not its nonce", [('key=g["nonce"], effect={k: g[k] for k in EFFECT_GOV}', 'key=g["root"], effect={k: g[k] for k in EFFECT_GOV}')]),
    ("G26 the store observes the DBC for governance", [('observe=lambda: self._view.observe("pbc"), overtaken=("overtaken-governance"', 'observe=lambda: self._view.observe("dbc"), overtaken=("overtaken-governance"')]),
    ("G27 the overtaken evidence claims a future nonce", [('overtaken=("overtaken-governance", str(current))', 'overtaken=("overtaken-governance", str(current + 5))')]),
    ("G28 the effect lacks the admins", [('EFFECT_GOV = ("action", "root", "admins", "witnessSetVersion")', 'EFFECT_GOV = ("action", "root", "witnessSetVersion")')]),
    ("G29 the admins array is typed bytes32[]", [('{"name": "admins", "type": "address[]"}', '{"name": "admins", "type": "bytes32[]"}')]),
    ("G30 the governance domain name is wrong", [('"name": "HMBCGovernance"', '"name": "HMBCGovernanceX"')]),
    ("G31 the nonce's integer form is not checked", [('    wire.uint(v["nonce"], 64)\n', "")]),
    ("G32 the expiry's integer form is not checked", [('    wire.uint(v["expiresAt"], 64)\n', "")]),
    ("G33 the witnessSetVersion's integer form is not checked", [('    wire.uint(v["witnessSetVersion"], 64)\n', "")]),
    ("G34 the root's address form is not checked", [('    wire.address(v["root"])\n', "")]),
    ("G35 the governance window argument is not validated", [("or max_governance_ttl < 1:", "or False:")]),
]


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="service-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", os.path.join("tests", "fixtures"), os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py") and name != "witness_service.py":
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_witness_service.py"), os.path.join("tests", "test_witness_service_decision.py"), os.path.join("tests", "test_witness_service_receipt.py"), os.path.join("tests", "test_witness_service_governance.py"), os.path.join("tests", "fixtures", "agent3-v2-signing-governance-vectors.json"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json"), os.path.join("f0", "vectors", "d50_reference.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "witness_service.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_service.py", "tests/test_witness_service_decision.py", "tests/test_witness_service_receipt.py", "tests/test_witness_service_governance.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return "timeout", None
        m = re.search(r"(\d+) failed", r.stdout)
        if r.returncode == 0:
            return "pass", 0
        if r.returncode == 1 and m:
            return "fail", int(m.group(1))
        return "crash", None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    status, _ = run_in_copy(SRC)
    if status != "pass":
        print("CONTROL FAILED: the unmutated module does not pass its own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated module passes all tests")
    detected = 0
    for name, edits in M:
        text = SRC
        for old, new in edits:
            if text.count(old) != 1:
                print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
                return 2
            text = text.replace(old, new)
        if text == SRC:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(M)))
    return 0 if detected == len(M) else 1


if __name__ == "__main__":
    sys.exit(main())
