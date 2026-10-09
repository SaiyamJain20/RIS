"""ABI layer: wire-form (decimal strings, lowercase hex, dict structs) <-> calldata/outputs, checked against Foundry's cast."""
import json
import pathlib
import subprocess

import pytest

from hmbc_protocol import abi
from support import foundry

ABI_DIR = pathlib.Path(__file__).resolve().parents[1] / "abi"
CAST = foundry("cast")
needs_cast = pytest.mark.skipif(CAST is None, reason="Foundry cast not installed")


def load(name):
    return abi.Contract(json.loads((ABI_DIR / f"{name}.json").read_text()))


def cast(*args):
    return subprocess.run([CAST, *args], check=True, capture_output=True, text=True).stdout.strip()


H = lambda n: "0x" + format(n, "064x")  # noqa: E731
A = lambda n: "0x" + format(n, "040x")  # noqa: E731
REQ = {"sourceChainId": "18545", "destinationChainId": "28545", "psc": A(1), "kssc": A(2), "gid": A(3), "dataId": H(4),
       "action": "1", "policyVersion": "1", "authEpoch": "3", "keyEpoch": "0", "nonce": "7", "expiresAt": "1800000030",
       "recipientKeyHash": H(5)}
CERT = {"cert": {"issuer": A(6), "gid": A(3), "roles": [H(8), H(9)], "serial": "101", "validFrom": "1700000000", "validUntil": "2100000000"},
        "signature": "0x" + "ab" * 65}
BUNDLE = {"certificates": [CERT], "temporalClaims": [{"authority": A(6), "role": H(10)}]}


@needs_cast
def test_selector_equals_cast_sig():
    psc = load("PSC")
    sig = psc.signature("requestAccess")
    assert sig.startswith("requestAccess(") and "(uint256,uint256,address,address,address,bytes32,uint8,uint64,uint64,uint64,uint256,uint64,bytes32)" in sig
    assert psc.selector("requestAccess").hex() == cast("sig", sig)[2:]


@needs_cast
def test_requestaccess_calldata_equals_cast_calldata():
    psc = load("PSC")
    ours = psc.calldata("requestAccess", REQ, "0x" + "cd" * 65, BUNDLE)
    req_t = "(" + ",".join(REQ[k] for k in REQ) + ")"
    cert_t = f"(({CERT['cert']['issuer']},{CERT['cert']['gid']},[{','.join(CERT['cert']['roles'])}],101,1700000000,2100000000),{CERT['signature']})"
    bundle_t = f"([{cert_t}],[({A(6)},{H(10)})])"
    theirs = cast("calldata", psc.signature("requestAccess"), req_t, "0x" + "cd" * 65, bundle_t)
    assert "0x" + ours.hex() == theirs


@needs_cast
def test_decode_struct_output_from_cast_encoding():
    psc = load("PSC")
    rec_sig = "f()(uint8,address,bytes32,uint256,address,bytes32,uint64,uint64,uint256,uint256)"
    enc = cast("abi-encode", "f((uint8,address,bytes32,uint256,address,bytes32,uint64,uint64,uint256,uint256))",
               f"(1,{A(3)},{H(4)},28545,{A(2)},{H(9)},1800000000,1800000030,5,0)")
    got = psc.decode_output("getRequest", bytes.fromhex(enc[2:]))
    assert got == {"status": "1", "gid": A(3), "dataId": H(4), "destinationChainId": "28545", "kssc": A(2),
                   "credentialDigest": H(9), "decidedAt": "1800000000", "expiresAt": "1800000030", "requestLogId": "5", "outcomeLogId": "0"}


def test_unknown_function_and_bad_wire_values_rejected():
    psc = load("PSC")
    with pytest.raises(abi.AbiError):
        psc.calldata("noSuchFunction")
    for bad in ({**REQ, "nonce": 7}, {**REQ, "gid": "0x" + "AB" * 20}, {**REQ, "extra": "1"}, {k: v for k, v in REQ.items() if k != "nonce"},
                {**REQ, "dataId": H(4) + "\n"}):
        with pytest.raises(abi.AbiError):
            psc.calldata("requestAccess", bad, "0x" + "cd" * 65, BUNDLE)


def test_decode_output_rejects_truncated_data():
    with pytest.raises(abi.AbiError):
        load("KSSC").decode_output("getGrant", b"\x00" * 31)


@needs_cast
def test_decode_access_forwarded_log_matches_cast_encoding():
    psc = load("PSC")
    rec_t = "(address,bytes32,uint8,uint64,uint64,uint64)"
    # CredentialRecord = (issuer, role, kind, serial, anchorVersion, validUntil)
    data = cast("abi-encode", f"f(uint256,address,bytes32,{rec_t}[],uint64,uint256)", "28545", A(2), H(9),
                f"[({A(6)},{H(8)},1,101,1,2100000000),({A(6)},{H(10)},2,0,1,1800028800)]", "1800000030", "5")
    topic0 = cast("keccak", psc.event_signature("AccessForwarded"))
    log = {"topics": [topic0, H(4), "0x" + "00" * 12 + A(3)[2:], H(7)], "data": data}
    name, got = psc.decode_log(log)
    assert name == "AccessForwarded"
    assert got["requestDigest"] == H(4) and got["gid"] == A(3) and got["dataId"] == H(7)
    assert got["destinationChainId"] == "28545" and got["kssc"] == A(2) and got["credentialDigest"] == H(9)
    assert got["verifiedAttributes"][1] == {"issuer": A(6), "role": H(10), "kind": "2", "serial": "0", "anchorVersion": "1", "validUntil": "1800028800"}
    assert got["expiresAt"] == "1800000030" and got["requestLogId"] == "5"


def test_decode_log_rejects_unknown_topic_and_malformed_logs():
    psc = load("PSC")
    with pytest.raises(abi.AbiError):
        psc.decode_log({"topics": [H(1)], "data": "0x"})
    with pytest.raises(abi.AbiError):
        psc.decode_log({"topics": [], "data": "0x"})


def test_decode_input_roundtrips_the_wire_form_exactly():
    psc = load("PSC")
    data = psc.calldata("requestAccess", REQ, "0x" + "cd" * 65, BUNDLE)
    assert psc.decode_input(data) == ("requestAccess", [REQ, "0x" + "cd" * 65, BUNDLE])


def test_decode_input_rejects_unknown_selector_and_truncated_data():
    psc = load("PSC")
    data = psc.calldata("requestAccess", REQ, "0x" + "cd" * 65, BUNDLE)
    with pytest.raises(abi.AbiError):
        psc.decode_input(b"\xde\xad\xbe\xef" + data[4:])
    with pytest.raises(abi.AbiError):
        psc.decode_input(data[:-1])
    with pytest.raises(abi.AbiError):
        psc.decode_input(b"\x01\x02")
