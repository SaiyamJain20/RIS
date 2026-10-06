// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {ErrorCode, Rejected, HMBCHash, Registration, SignedRoleCertificate} from "./types/ProtocolTypes.sol";
import {SigLib} from "./lib/SigLib.sol";
import {Bootstrapped} from "./lib/Bootstrapped.sol";
import {LSC} from "./LSC.sol";
import {TMSC} from "./TMSC.sol";

/// Registration Smart Contract on the PBC (HMBC2020 III-D2, Table 2 userRegistration).
///
/// Reconstruction choices (recorded in A1 source review):
///  - GID is the user's Ethereum signing address (IV-D, Table 2 "unique Ethereum address").
///    III-D2's "RSC assigns GID and sends it encrypted with pkA_X" therefore reduces to binding
///    and uniqueness: one registration per address.
///  - The certificate subject key is the GID key, so the III-D2 "signed challenge with skA_X"
///    is the EIP-712 Registration signature by the GID. It binds the certificate digest and
///    the recipient encryption-key hash, so it cannot be replayed for another cert or key.
///  - Table 2 actuator "User/device" may submit through the user API (Fig. 7/8); authority comes
///    from the possession signature, so any submitter may carry it.
contract RSC is Bootstrapped {
    struct Registrant {
        bool registered;
        address issuer;
        bytes32 certDigest;
        bytes32 recipientKeyHash;
        uint64 registeredAt;
        uint256 logId;
    }

    uint256 public immutable pbcChainId;
    TMSC public immutable tmsc;
    LSC public immutable lsc;
    mapping(address => Registrant) internal _registrants;

    event Registered(
        address indexed gid, address indexed issuer, bytes32 certDigest, bytes32 recipientKeyHash, uint256 logId
    );

    constructor(uint256 pbcChainId_, TMSC tmsc_, LSC lsc_) {
        if (pbcChainId_ != block.chainid) revert Rejected(ErrorCode.WRONG_DESTINATION);
        pbcChainId = pbcChainId_;
        tmsc = tmsc_;
        lsc = lsc_;
    }

    function _checkWiring() internal view override {}

    function register(Registration calldata reg, bytes calldata possessionSignature, SignedRoleCertificate calldata cert)
        external
        whenSealed
        returns (uint256 logId)
    {
        if (reg.gid == address(0) || reg.recipientKeyHash == bytes32(0)) revert Rejected(ErrorCode.MALFORMED);
        if (_registrants[reg.gid].registered) revert Rejected(ErrorCode.ALREADY_REGISTERED);
        if (block.timestamp >= reg.expiresAt) revert Rejected(ErrorCode.EXPIRED);
        bytes32 digest = HMBCHash.registrationDigest(reg, pbcChainId, address(this));
        if (!SigLib.isValid(digest, possessionSignature, reg.gid)) revert Rejected(ErrorCode.BAD_SIGNATURE);
        if (cert.cert.gid != reg.gid) revert Rejected(ErrorCode.WRONG_SUBJECT);
        (ErrorCode code, bytes32 certDigest) = tmsc.validateCertificate(cert, uint64(block.timestamp));
        if (certDigest != reg.certDigest) revert Rejected(ErrorCode.WRONG_SUBJECT);
        if (code != ErrorCode.NONE) revert Rejected(code);

        Registrant storage entry = _registrants[reg.gid];
        entry.registered = true;
        entry.issuer = cert.cert.issuer;
        entry.certDigest = certDigest;
        entry.recipientKeyHash = reg.recipientKeyHash;
        entry.registeredAt = uint64(block.timestamp);
        logId = lsc.registrationLog(
            bytes32(uint256(uint160(reg.gid))),
            abi.encode(reg.gid, cert.cert.issuer, cert.cert.serial, certDigest, reg.recipientKeyHash)
        );
        entry.logId = logId;
        emit Registered(reg.gid, cert.cert.issuer, certDigest, reg.recipientKeyHash, logId);
    }

    function isRegistered(address gid) external view returns (bool) {
        return _registrants[gid].registered;
    }

    function recipientKeyHash(address gid) external view returns (bytes32) {
        return _registrants[gid].recipientKeyHash;
    }

    function registrant(address gid) external view returns (Registrant memory) {
        return _registrants[gid];
    }
}
