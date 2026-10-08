"""Authority-side fixture setup for live tests (the role agent 1's E2ESmoke `pbc-setup` plays): CRLs, temporal list, Alice's certificate and registration.

TEST SUPPORT ONLY. Authority root keys sign; CA admins and the relay submit. All keys are the TEST-ONLY synthetic fixture keys.
"""
from types import SimpleNamespace

from eth_utils import keccak

from hmbc_protocol import eip712, keys, messages

ROLE_DOCTOR = "0x" + keccak(text="HMBC.role.Doctor").hex()
ROLE_ON_DUTY = "0x" + keccak(text="HMBC.role.OnDuty").hex()
DATA_P1 = "0x" + keccak(text="HMBC.data.P1.MHR").hex()


def key(label: str) -> str:
    return keys.synthetic_private_key(label)


def addr(label: str) -> str:
    from eth_account import Account
    return Account.from_key(key(label)).address.lower()


def sign(name: str, msg: dict, dep: dict, label: str) -> str:
    digest = messages.digest_of(name, msg, messages.domain_for(name, msg, dep))
    return eip712.sign_digest(key(label), digest)


def fresh_now(led) -> int:
    """Mine one PBC block and return its timestamp. `get_block('latest')` alone is the LAST mined block, which is stale after idle time."""
    from support import rpc
    rpc(led.pbc.url, "evm_mine")
    return led.pbc.get_block()["timestamp"]


def setup_pbc(led, duty_seconds: int = 8 * 3600) -> SimpleNamespace:
    dep, t = led.deployment, fresh_now(led)
    h1, h2, alice = addr("H1-root"), addr("H2-root"), addr("alice")
    crl1 = {"authority": h1, "version": "1", "validUntil": str(t + 86400), "revokedSerials": []}
    crl2 = {"authority": h2, "version": "1", "validUntil": str(t + 86400), "revokedSerials": []}
    acl = {"authority": h1, "version": "1", "validUntil": str(t + 86400),
           "entries": [{"gid": alice, "role": ROLE_ON_DUTY, "validFrom": str(t - 60), "validUntil": str(t + duty_seconds)}]}
    led.pbc.send(key("H1-ca-admin"), led.TMSC, "updateRevocationList", crl1, sign("RevocationList", crl1, dep, "H1-root"))
    led.pbc.send(key("H1-ca-admin"), led.TMSC, "updateTemporalAcl", acl, sign("TemporalAcl", acl, dep, "H1-root"))
    led.pbc.send(key("H2-ca-admin"), led.TMSC, "updateRevocationList", crl2, sign("RevocationList", crl2, dep, "H2-root"))
    cert = {"issuer": h1, "gid": alice, "roles": [ROLE_DOCTOR], "serial": "101", "validFrom": "1700000000", "validUntil": "2100000000"}
    signed_cert = {"cert": cert, "signature": sign("RoleCertificate", cert, dep, "H1-root")}
    cert_digest = "0x" + messages.digest_of("RoleCertificate", cert, messages.domain_for("RoleCertificate", cert, dep)).hex()
    reg = {"gid": alice, "certDigest": cert_digest, "recipientKeyHash": keys.recipient_key_hash("keyref:user:alice"), "expiresAt": str(t + 600)}
    led.pbc.send(key("relay"), led.RSC, "register", reg, sign("Registration", reg, dep, "alice"), signed_cert)
    bundle = {"certificates": [signed_cert], "temporalClaims": [{"authority": h1, "role": ROLE_ON_DUTY}]}
    return SimpleNamespace(cert=signed_cert, bundle=bundle, h1=h1, h2=h2, alice=alice, acl=acl, crl1=crl1)


def make_request(led, ctx, client, nonce="1", ttl=30, **over):
    now = led.pbc.now()
    return client.build_request(data_id=DATA_P1, nonce=nonce, auth_epoch=led.pbc.call(led.TMSC, "authEpoch"), expires_at=str(now + ttl), **over)


def advance(led, seconds: int):
    """Move both chains forward in time (Anvil test nodes only) and mine one block on each."""
    from support import rpc
    for url in (led.pbc.url, led.dbc.url):
        rpc(url, "evm_increaseTime", [seconds])
        rpc(url, "evm_mine")
