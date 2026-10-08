"""User-side signing client (honest user). Never signs for another identity or against another deployment."""
from __future__ import annotations

from . import eip712, keys, messages, wire


class ClientError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class UserClient:
    def __init__(self, label: str, deployment: dict):
        self.ref = f"keyref:user:{label}"
        self._key, self.address = keys.resolve(self.ref, ("user",))
        self.recipient_key_hash = keys.recipient_key_hash(self.ref)
        self.deployment = deployment

    def build_request(self, *, data_id: str, nonce: str, auth_epoch: str, expires_at: str, key_epoch: str = "0", action: str = "1") -> dict:
        pbc, dbc, fx = self.deployment["chains"]["pbc"], self.deployment["chains"]["dbc"], self.deployment["fixture"]
        return {"sourceChainId": pbc["chainId"], "destinationChainId": dbc["chainId"], "psc": pbc["contracts"]["PSC"],
                "kssc": dbc["contracts"]["KSSC"], "gid": self.address, "dataId": data_id, "action": action,
                "policyVersion": fx["policyVersion"], "authEpoch": auth_epoch, "keyEpoch": key_epoch, "nonce": nonce,
                "expiresAt": expires_at, "recipientKeyHash": self.recipient_key_hash}

    def sign_request(self, request: dict) -> dict:
        try:
            req = messages.VALIDATE["AccessRequest"](request)
        except wire.WireError as e:
            raise ClientError("MALFORMED", str(e)) from None
        pbc, dbc, fx = self.deployment["chains"]["pbc"], self.deployment["chains"]["dbc"], self.deployment["fixture"]
        if req["gid"] != self.address:
            raise ClientError("WRONG_SUBJECT", "request.gid is not this user's address")
        if (req["sourceChainId"], req["psc"], req["destinationChainId"], req["kssc"]) != (
                pbc["chainId"], pbc["contracts"]["PSC"], dbc["chainId"], dbc["contracts"]["KSSC"]):
            raise ClientError("WRONG_DESTINATION", "request chains/contracts differ from the deployment manifest")
        if req["keyEpoch"] != fx["keyEpoch"] or req["policyVersion"] != fx["policyVersion"]:
            raise ClientError("WRONG_EPOCH", "request keyEpoch/policyVersion differ from the deployment's fixed values")
        digest = messages.digest_of("AccessRequest", req, messages.domain_for("AccessRequest", req, self.deployment))
        signature = eip712.sign_digest(self._key, digest)
        assert eip712.recover(digest, signature) == self.address
        return {"request": req, "requestDigest": "0x" + digest.hex(), "signature": signature, "signer": self.address}
