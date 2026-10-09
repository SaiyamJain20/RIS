"""Paper profiles through the adapter PROCESS (JSON lines over stdin/stdout), live ledger.

Until now the paper-mode worker (option (c), D35/A38) was exercised through the library and the repaired-e flow through the process. A runner drives the PROCESS in every
profile, so this closes the gap before an owner rehearsal or C-E1 does: user signing, the witness operations (repaired-e only, so WRONG_PROFILE here), a paper release bound
to the REGISTERED key, the cached retry, the wrong-user refusal, EXPIRED after the ~30 s paper grant lifetime, and the read-only worker log.

Roles: the test plays the runner/relay (PBC forward, DBC policyEnf, PBC reportOutcome) with the relay's TEST key; everything else comes from the adapter subprocess.
Nothing here is an E1 result.
"""
import json
import pathlib
import subprocess
import sys

import pytest

from hmbc_protocol import eip712, keys
from hmbc_protocol.relay import Relay
import ledger_setup as setup
from test_adapter_process_live import AdapterProcess, P1_POLICY, RECORD, setup_request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTCOME = "0x" + "ab" * 32


@pytest.mark.parametrize("fixture_name", ["world_paper", "world_paper_minimal"])
def test_paper_flow_through_the_adapter_process(request, fixture_name, tmp_path):
    led, ctx = request.getfixturevalue(fixture_name)
    state = tmp_path / "adapter-state"
    adp = AdapterProcess(state, led.deployment)
    try:
        req = adp.call("prepare_request", {"request": setup_request(led), "signingKeyRef": "keyref:user:alice"})
        assert req["ok"], req
        signed = {"request": req["result"]["request"], "requestDigest": req["result"]["requestDigest"], "signature": req["result"]["signature"]}
        res = Relay(led, "relay").forward(signed, ctx.bundle)
        assert res.code == "NONE", res.code
        led.dbc.send(setup.key("relay"), led.ACSC, "policyEnf", {"pbcRequestId": signed["requestDigest"], "gid": ctx.alice, "dataId": setup.DATA_P1, "action": "1"}, res.records)
        grant_id = "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
        assert led.dbc.call(led.KSSC, "getGrant", grant_id)[5] is True

        for op, inp in (("collect_checkpoint", {}), ("collect_decision", {"requestDigest": signed["requestDigest"]}), ("attest_grant", {"grantId": grant_id})):
            r = adp.call(op, inp)                                                                    # witness artifacts exist only in repaired-e
            assert r["ok"] is False and r["error"]["code"] == "WRONG_PROFILE", (op, r)

        assert adp.call("encrypt_record", {"record": RECORD, "policy": P1_POLICY, "keyEpoch": "0"})["ok"]
        rel = adp.call("release", {"grantId": grant_id})
        assert rel["ok"], rel
        assert rel["result"]["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:alice") != "0x" + "00" * 32      # the registered key, not the grant's native zero
        again = adp.call("release", {"grantId": grant_id})
        assert again["ok"] and again["result"] == rel["result"]                                                          # same cached response
        fin = adp.call("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:alice"})
        assert fin["ok"] and fin["result"]["decryptable"] is True
        assert adp.call("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:bob"})["error"]["code"] == "WRONG_SUBJECT"
        led.pbc.send(setup.key("relay"), led.PSC, "reportOutcome", signed["requestDigest"], grant_id, OUTCOME)         # the paper path, called by the configured relay
        assert led.pbc.call(led.PSC, "getRequest", signed["requestDigest"])["status"] == "2"

        log = subprocess.run([sys.executable, "-m", "hmbc_protocol.worker_log", "--state-dir", str(state)], cwd=ROOT,
                             env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=30)
        assert log.returncode == 0, log.stderr
        out = json.loads(log.stdout)
        assert out["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "2"}
        assert rel["result"]["responseEnvelope"]["token"] not in log.stdout                                              # the capability is redacted

        setup.advance(led, 40)                                                                                           # past the ~30 s paper grant lifetime
        expired = adp.call("release", {"grantId": grant_id})
        assert expired["ok"] is False and expired["error"]["code"] == "EXPIRED"
    finally:
        adp.close()
