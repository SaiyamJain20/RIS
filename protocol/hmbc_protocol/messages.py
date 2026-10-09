"""EIP-712 type tables and typed-data builders for the signed service-facing messages.

Field order is the interface contract (interfaces/README.md v0, A1-0003, A1-0008 rev 2); tests compare every
built typed-data object with agent 1's producer vectors, so a reordered field cannot slip in.
"""
from __future__ import annotations

from . import eip712, wire

_T = lambda *pairs: [{"name": n, "type": t} for n, t in pairs]  # noqa: E731

TYPES = {
    "AccessRequest": _T(("sourceChainId", "uint256"), ("destinationChainId", "uint256"), ("psc", "address"),
                        ("kssc", "address"), ("gid", "address"), ("dataId", "bytes32"), ("action", "uint8"),
                        ("policyVersion", "uint64"), ("authEpoch", "uint64"), ("keyEpoch", "uint64"),
                        ("nonce", "uint256"), ("expiresAt", "uint64"), ("recipientKeyHash", "bytes32")),
    "AccessDecision": _T(("requestDigest", "bytes32"), ("result", "uint8"), ("credentialDigest", "bytes32"),
                         ("stateSequence", "uint64"), ("witnessSetVersion", "uint64"),
                         ("sourceBlockNumber", "uint256"), ("sourceBlockHash", "bytes32"), ("expiresAt", "uint64")),
    "StateCheckpoint": _T(("sequence", "uint64"), ("authEpoch", "uint64"), ("policyVersion", "uint64"),
                          ("keyEpoch", "uint64"), ("witnessSetVersion", "uint64"), ("sourceChainId", "uint256"),
                          ("psc", "address"), ("sourceBlockNumber", "uint256"), ("sourceBlockHash", "bytes32"),
                          ("expiresAt", "uint64")),
    "GrantReceipt": _T(("requestDigest", "bytes32"), ("grantId", "bytes32"), ("gid", "address"), ("dataId", "bytes32"),
                       ("keyEpoch", "uint64"), ("grantExpiresAt", "uint64"), ("witnessSetVersion", "uint64"),
                       ("dbcChainId", "uint256"), ("kssc", "address"), ("dbcBlockNumber", "uint256"),
                       ("dbcBlockHash", "bytes32")),
    "Registration": _T(("gid", "address"), ("certDigest", "bytes32"), ("recipientKeyHash", "bytes32"),
                       ("expiresAt", "uint64")),
    "RoleCertificate": _T(("issuer", "address"), ("gid", "address"), ("roles", "bytes32[]"), ("serial", "uint64"),
                          ("validFrom", "uint64"), ("validUntil", "uint64")),
    "RevocationList": _T(("authority", "address"), ("version", "uint64"), ("validUntil", "uint64"), ("revokedSerials", "uint64[]")),
    "TemporalAcl": _T(("authority", "address"), ("version", "uint64"), ("validUntil", "uint64"), ("entries", "TempAclEntry[]")),
}
NESTED = {"TemporalAcl": {"TempAclEntry": _T(("gid", "address"), ("role", "bytes32"), ("validFrom", "uint64"), ("validUntil", "uint64"))}}

VALIDATE = {"AccessRequest": wire.access_request, "AccessDecision": wire.access_decision,
            "StateCheckpoint": wire.state_checkpoint, "GrantReceipt": wire.grant_receipt,
            "Registration": wire.registration, "RoleCertificate": wire.role_certificate,
            "RevocationList": wire.revocation_list, "TemporalAcl": wire.temporal_acl}


def domain_for(name: str, message: dict, deployment: dict) -> dict:
    """Domain per interfaces v0 / A1-0008: the signer's chain and contract are never taken from the caller."""
    pbc, dbc = deployment["chains"]["pbc"], deployment["chains"]["dbc"]
    if name == "AccessRequest":
        return {"name": "HMBCRequest", "version": "1", "chainId": message["sourceChainId"], "verifyingContract": message["psc"]}
    if name == "AccessDecision":
        return {"name": "HMBCDecision", "version": "1", "chainId": dbc["chainId"], "verifyingContract": dbc["contracts"]["KSSC"]}
    if name == "StateCheckpoint":
        return {"name": "HMBCState", "version": "1", "chainId": dbc["chainId"], "verifyingContract": dbc["contracts"]["KSSC"]}
    if name == "GrantReceipt":
        return {"name": "HMBCReceipt", "version": "1", "chainId": pbc["chainId"], "verifyingContract": pbc["contracts"]["PSC"]}
    if name == "Registration":
        return {"name": "HMBCRegistration", "version": "1", "chainId": pbc["chainId"], "verifyingContract": pbc["contracts"]["RSC"]}
    if name == "RoleCertificate":
        return {"name": "HMBCCredential", "version": "1", "chainId": pbc["chainId"], "verifyingContract": pbc["contracts"]["TMSC"]}
    if name in ("RevocationList", "TemporalAcl"):
        return {"name": "HMBCTrust", "version": "1", "chainId": pbc["chainId"], "verifyingContract": pbc["contracts"]["TMSC"]}
    raise KeyError(name)


def typed_data(name: str, message: dict, domain: dict) -> dict:
    VALIDATE[name](message)
    return {"types": {"EIP712Domain": eip712.DOMAIN_TYPE, name: TYPES[name], **NESTED.get(name, {})}, "primaryType": name,
            "domain": domain, "message": message}


def digest_of(name: str, message: dict, domain: dict) -> bytes:
    return eip712.digest(typed_data(name, message, domain))
