"""TEST-ONLY bootstrap fixture producer for E1 (A3-0024): Alice registered and entitled, Bob registered but policy-denied.

Why it exists: the runner (Option A custody) holds only the relay and H1..H4-ca-admin TEST keys, yet the ledger needs trust lists signed by the AUTHORITY ROOT keys,
role certificates signed by those roots, and a Registration signed by each user's GID key. Those keys stay in this process. The runner receives only signed public
artifacts, ready-made calldata for its five transactions and the two credential bundles; no key is ever printed.

    python -m testtools.bootstrap_fixture --deployment deployment.json

Prints ONE JSON object and nothing else (schemaVersion "hmbc-test-bootstrap/v0"): `binding` (the deployment facts and the PBC clock the artifacts were signed against),
`validity`, `identities` (alice/bob: keyRef, gid, recipientKeyHash by the A35 convention), `steps` (five PBC transactions in dependency order, each with its submitter
label, contract, function, wire-form `args` and ABI `calldata`), `controls` (one transaction that is NOT a bootstrap step: the frozen WrongIssuerAdmin control, an
H2 list of the NEXT version validly signed by H2's root, to be submitted by H1-ca-admin and expected to revert UNAUTHORIZED_CALLER), `credentialBundles`
(alice/bob) and `notes`.

Run it ONCE per deployment, after the ledger is deployed and before any request is built: the list versions are monotone, so a second run's lists are refused by the
ledger. The registration windows are measured from the PBC clock it read, so submit promptly. The tool refuses (non-zero exit, empty stdout, "refusing" on stderr,
no traceback) unless the deployment declares TEST-ONLY synthetic keys and its RPC URL is loopback. It is NOT part of the production adapter and not one of its
eight operations.
"""
from __future__ import annotations

import argparse
import json
import sys

from eth_account import Account
from eth_utils import keccak

from hmbc_protocol import eip712, keys, messages, wire
from hmbc_protocol.chain import ChainError
from hmbc_protocol.ledger import Ledger, LedgerError

SCHEMA = "hmbc-test-bootstrap/v0"
LIST_SECONDS = 86400
DUTY_SECONDS = 8 * 3600
REGISTRATION_SECONDS = 3600
CERT_VALID_FROM, CERT_VALID_UNTIL = "1700000000", "2100000000"
ROLE_DOCTOR = "0x" + keccak(text="HMBC.role.Doctor").hex()
ROLE_ON_DUTY = "0x" + keccak(text="HMBC.role.OnDuty").hex()
ROLE_RESEARCHER = "0x" + keccak(text="HMBC.role.Researcher").hex()
NOTES = [
    "Submit the steps in order, each from its submitter label's TEST key (relay, H1-ca-admin, H2-ca-admin), as a plain transaction to `to` with `calldata`.",
    "Read TMSC.authEpoch AFTER the last step before building any AccessRequest: every list update moves it.",
    "Run once per deployment: list versions are monotone, so a second plan's lists are refused by the ledger.",
    "Registrations expire registrationSeconds after binding.pbcTimestamp; submit promptly.",
    "A control is never part of the bootstrap; submit it only after the five steps, from its own submitter, and expect the stated error with no state change.",
]


def require_test_only(dep: dict) -> None:
    """Refuse BEFORE any network I/O unless the deployment declares TEST-ONLY synthetic keys."""
    fixture = dep.get("fixture") if isinstance(dep, dict) else None
    if not isinstance(fixture, dict) or "TEST-ONLY" not in str(fixture.get("keyDerivation", "")):
        raise SystemExit("refusing: the deployment does not declare TEST-ONLY synthetic keys")


def _addr(label: str) -> str:
    return Account.from_key(keys.synthetic_private_key(label)).address.lower()


def _sign(led: Ledger, name: str, msg: dict, label: str) -> str:
    digest = messages.digest_of(name, msg, messages.domain_for(name, msg, led.deployment))
    return eip712.sign_digest(keys.synthetic_private_key(label), digest)


def _step(step_id: str, submitter: str, contract_name: str, led: Ledger, function: str, args: dict) -> dict:
    contract = getattr(led, contract_name)
    return {"id": step_id, "chain": "pbc", "submitter": submitter, "contract": contract_name, "to": contract.address, "function": function,
            "args": args, "calldata": "0x" + contract.calldata(function, *args.values()).hex()}


def _signed_cert(led: Ledger, issuer_label: str, subject_label: str, role: str, serial: str) -> dict:
    cert = {"issuer": _addr(issuer_label), "gid": _addr(subject_label), "roles": [role], "serial": serial,
            "validFrom": CERT_VALID_FROM, "validUntil": CERT_VALID_UNTIL}
    return {"cert": cert, "signature": _sign(led, "RoleCertificate", cert, issuer_label)}


def _registration(led: Ledger, subject_label: str, signed_cert: dict, now: int) -> dict:
    cert = signed_cert["cert"]
    cert_digest = "0x" + messages.digest_of("RoleCertificate", cert, messages.domain_for("RoleCertificate", cert, led.deployment)).hex()
    return {"gid": _addr(subject_label), "certDigest": cert_digest, "recipientKeyHash": keys.recipient_key_hash(f"keyref:user:{subject_label}"),
            "expiresAt": str(now + REGISTRATION_SECONDS)}


def build_plan(led: Ledger, now: int) -> dict:
    require_test_only(led.deployment)
    h1, h2 = _addr("H1-root"), _addr("H2-root")
    crl1 = {"authority": h1, "version": "1", "validUntil": str(now + LIST_SECONDS), "revokedSerials": []}
    crl2 = {"authority": h2, "version": "1", "validUntil": str(now + LIST_SECONDS), "revokedSerials": []}
    acl = {"authority": h1, "version": "1", "validUntil": str(now + LIST_SECONDS),
           "entries": [{"gid": _addr("alice"), "role": ROLE_ON_DUTY, "validFrom": str(now - 60), "validUntil": str(now + DUTY_SECONDS)}]}
    alice_cert = _signed_cert(led, "H1-root", "alice", ROLE_DOCTOR, "101")
    bob_cert = _signed_cert(led, "H2-root", "bob", ROLE_RESEARCHER, "201")
    reg_alice, reg_bob = _registration(led, "alice", alice_cert, now), _registration(led, "bob", bob_cert, now)
    steps = [
        _step("h1-revocation-list", "H1-ca-admin", "TMSC", led, "updateRevocationList", {"list": crl1, "issuerSignature": _sign(led, "RevocationList", crl1, "H1-root")}),
        _step("h1-temporal-acl", "H1-ca-admin", "TMSC", led, "updateTemporalAcl", {"acl": acl, "issuerSignature": _sign(led, "TemporalAcl", acl, "H1-root")}),
        _step("h2-revocation-list", "H2-ca-admin", "TMSC", led, "updateRevocationList", {"list": crl2, "issuerSignature": _sign(led, "RevocationList", crl2, "H2-root")}),
        _step("register-alice", "relay", "RSC", led, "register", {"reg": reg_alice, "possessionSignature": _sign(led, "Registration", reg_alice, "alice"), "cert": alice_cert}),
        _step("register-bob", "relay", "RSC", led, "register", {"reg": reg_bob, "possessionSignature": _sign(led, "Registration", reg_bob, "bob"), "cert": bob_cert}),
    ]
    crl2_next = {"authority": h2, "version": "2", "validUntil": str(now + LIST_SECONDS), "revokedSerials": []}
    control = _step("wrong-issuer-admin-h2-list", "H1-ca-admin", "TMSC", led, "updateRevocationList",
                    {"list": crl2_next, "issuerSignature": _sign(led, "RevocationList", crl2_next, "H2-root")})
    control["expected"] = "UNAUTHORIZED_CALLER"
    bundles = {"alice": {"certificates": [alice_cert], "temporalClaims": [{"authority": h1, "role": ROLE_ON_DUTY}]},
               "bob": {"certificates": [bob_cert], "temporalClaims": []}}
    for name, value in (("RevocationList", crl1), ("RevocationList", crl2), ("RevocationList", crl2_next), ("TemporalAcl", acl), ("Registration", reg_alice), ("Registration", reg_bob),
                        ("CredentialBundle", bundles["alice"]), ("CredentialBundle", bundles["bob"])):
        wire.validate(name, value)
    chains = led.deployment["chains"]
    return {"schemaVersion": SCHEMA, "testOnly": True,
            "binding": {"pbcChainId": chains["pbc"]["chainId"], "dbcChainId": chains["dbc"]["chainId"], "tmsc": led.TMSC.address, "rsc": led.RSC.address,
                        "pbcTimestamp": str(now)},
            "validity": {"listSeconds": LIST_SECONDS, "dutySeconds": DUTY_SECONDS, "registrationSeconds": REGISTRATION_SECONDS},
            "identities": {label: {"keyRef": f"keyref:user:{label}", "gid": _addr(label), "recipientKeyHash": keys.recipient_key_hash(f"keyref:user:{label}")}
                           for label in ("alice", "bob")},
            "steps": steps, "controls": [control], "credentialBundles": bundles, "notes": NOTES}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deployment", required=True, help="the deployment JSON the runner deployed (and will pin the adapter with)")
    args = ap.parse_args(argv)
    try:
        with open(args.deployment, "rb") as f:
            dep = json.loads(f.read().decode("utf-8"))
        require_test_only(dep)
        led = Ledger.from_deployment(dep)
        plan = build_plan(led, led.pbc.now())
    except (OSError, ValueError, KeyError, TypeError, LedgerError, ChainError, wire.WireError, eip712.EncodingError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    sys.stdout.write(json.dumps(plan) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
