"""Whole legitimate flow through the real adapter PROCESS (JSON lines over stdin/stdout) against the live ledger.

Roles (Option A, accepted into candidate revision 5, A3-0012): the test plays the runner/relay with raw ledger transactions; EVERY honest-party
signature (user, witness checkpoint, witness decision, witness receipt) and every worker action comes from the adapter subprocess, which was started the way a
runner must start it: private state dir + the deployment PINNED out of band. Responses are validated with the revision-5 response rules and the transcript is recorded
(HMBC_WRITE_EVIDENCE=1) as evidence. It is NOT an E1 integration run: E0 is not accepted, the ledger is a local Anvil pair, and the runner role is played by this test.
"""
import json
import os
import pathlib
import subprocess
import sys

from eth_utils import keccak

from hmbc_protocol import eip712, wire
from hmbc_protocol.relay import Relay
import ledger_setup as setup

ROOT = pathlib.Path(__file__).resolve().parents[1]
P1_POLICY = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
RECORD = {"dataId": setup.DATA_P1, "owner": setup.addr("H2-root"), "payloadDigest": "0x" + keccak(text="synthetic payload P1").hex()}


class AdapterProcess:
    def __init__(self, state_dir, dep):
        self.dep, self.transcript = dep, []
        dep_file = pathlib.Path(str(state_dir) + ".deployment.json")
        dep_file.write_text(json.dumps(dep))
        self.p = subprocess.Popen([sys.executable, "-m", "hmbc_protocol.adapter", "--state-dir", str(state_dir), "--deployment", str(dep_file)], cwd=ROOT,
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
        # 2. the (honest) relay submits it to the PBC; 3. the adapter's witness signs a checkpoint, which the runner submits to the DBC
        assert Relay(led, "relay").forward(signed, ctx.bundle).code == "NONE"
        relay = Relay(led, "relay")
        cp = adp.call("collect_checkpoint", {})
        assert cp["ok"], cp
        relay.accept_state({"checkpoint": cp["result"]["checkpoint"], "signatures": cp["result"]["signatures"]})
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
        # 7. the adapter's witness attests the grant; the runner reports the attested outcome on the PBC
        att = adp.call("attest_grant", {"grantId": grant_id})
        assert att["ok"], att
        relay.report_outcome(signed["requestDigest"], "0x" + "ab" * 32, {"receipt": att["result"]["receipt"], "signatures": att["result"]["signatures"]})
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
