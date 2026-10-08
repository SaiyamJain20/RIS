"""Whole legitimate flow through the real adapter PROCESS (JSON lines over stdin/stdout) against the live ledger.

Roles: the test plays the runner/relay with raw ledger transactions (Option A of A2-0008); every honest-party signature and every worker
action comes from the adapter subprocess. Responses are validated with the revision-4 response rules and the transcript is recorded
(HMBC_WRITE_EVIDENCE=1) as evidence; it is NOT an E1 integration run (E0 is not accepted; two operations the flow needs, checkpoint and receipt
signing, are not in the six-operation interface yet - A2-0008 - so those two steps use the in-process witness).
"""
import json
import os
import pathlib
import subprocess
import sys

from eth_utils import keccak

from hmbc_protocol import eip712, wire
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness
import ledger_setup as setup

ROOT = pathlib.Path(__file__).resolve().parents[1]
P1_POLICY = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
RECORD = {"dataId": setup.DATA_P1, "owner": setup.addr("H2-root"), "payloadDigest": "0x" + keccak(text="synthetic payload P1").hex()}


class AdapterProcess:
    def __init__(self, state_dir, dep):
        self.dep, self.transcript = dep, []
        self.p = subprocess.Popen([sys.executable, "-m", "hmbc_protocol.adapter", "--state-dir", str(state_dir)], cwd=ROOT,
                                  env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)

    def call(self, op, inp):
        req = {"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": self.dep}
        self.p.stdin.write(json.dumps(req) + "\n")
        self.p.stdin.flush()
        resp = json.loads(self.p.stdout.readline())
        wire.adapter_request(req)
        wire.adapter_response(resp, op)
        self.transcript.append({"operation": op, "input": inp, "response": resp})
        return resp

    def close(self):
        self.p.stdin.close()
        err = self.p.stderr.read()
        self.p.wait(timeout=20)
        assert self.p.returncode == 0 and err == "", err


def test_legitimate_flow_through_the_adapter_process(world, tmp_path):
    led, ctx = world
    adp = AdapterProcess(tmp_path / "adapter-state", led.deployment)
    try:
        # 1. user signs the request inside the adapter (prepare_request)
        req = adp.call("prepare_request", {"request": setup_request(led), "signingKeyRef": "keyref:user:alice"})
        assert req["ok"], req
        signed = {"request": req["result"]["request"], "requestDigest": req["result"]["requestDigest"], "signature": req["result"]["signature"]}
        # 2. the (honest) relay submits it to the PBC; 3. witness checkpoint (in-process: no operation yet) accepted by the DBC
        assert Relay(led, "relay").forward(signed, ctx.bundle).code == "NONE"
        witness, relay = Witness(led), Relay(led, "relay")
        relay.accept_state(witness.checkpoint())
        # 4. decision from the adapter's witness; 5. relay consumes it on the DBC
        dec = adp.call("collect_decision", {"requestDigest": signed["requestDigest"]})
        assert dec["ok"], dec
        grant_id = relay.deliver(signed, {"decision": dec["result"]["decision"], "signatures": dec["result"]["signatures"],
                                          "credentialRecords": dec["result"]["credentialRecords"]})
        assert grant_id is not None
        # 6. worker: register the record, release against the committed grant, user completes
        assert adp.call("encrypt_record", {"record": RECORD, "policy": P1_POLICY, "keyEpoch": "0"})["ok"]
        rel = adp.call("release", {"grantId": grant_id})
        assert rel["ok"], rel
        fin = adp.call("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:alice"})
        assert fin["ok"] and fin["result"]["decryptable"] is True
        # 7. receipt (in-process witness) and attested outcome on the PBC
        relay.report_outcome(signed["requestDigest"], "0x" + "ab" * 32, witness.attest_grant(grant_id))
        assert led.pbc.call(led.PSC, "getRequest", signed["requestDigest"])["status"] == "2"
        # negative controls through the same process: another user's key cannot complete; a forged token cannot complete
        assert adp.call("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:bob"})["error"]["code"] == "WRONG_SUBJECT"
        forged = {**rel["result"], "responseEnvelope": {**rel["result"]["responseEnvelope"], "token": "0x" + "ee" * 32}}
        assert adp.call("finish_decryption", {"response": forged, "userKeyRef": "keyref:user:alice"})["error"]["code"] == "WRONG_SUBJECT"
    finally:
        adp.close()
    blob = json.dumps(adp.transcript)
    from hmbc_protocol import keys
    for label in ("alice", "bob", "witness-1", "relay"):
        assert keys.synthetic_private_key(label)[2:] not in blob
    if os.environ.get("HMBC_WRITE_EVIDENCE") == "1":
        out = ROOT / "evidence" / "live-adapter-flow.json"
        out.write_text(json.dumps({"note": "Live run against agent-1 ledger 33a7a5d on a local Anvil pair; ports/addresses/tokens/timestamps vary per run. "
                                           "Not an E1 integration run. Deployment manifest omitted from each request for size.",
                                   "steps": [{"operation": t["operation"], "input": t["input"], "response": t["response"]} for t in adp.transcript]}, indent=1) + "\n")


def setup_request(led):
    from hmbc_protocol.client import UserClient
    client = UserClient("alice", led.deployment)
    return setup.make_request(led, None, client)
