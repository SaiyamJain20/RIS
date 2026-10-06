// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {ErrorCode} from "../types/ProtocolTypes.sol";

/// Canonical secp256k1 recovery for 65-byte Ethereum signatures (r || s || v).
/// Rejects 64-byte compact (EIP-2098) encodings, v outside {27, 28}, high-s malleable
/// signatures and the zero address returned by ecrecover for invalid input.
library SigLib {
    uint256 internal constant HALF_ORDER = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;

    function tryRecover(bytes32 digest, bytes memory signature) internal pure returns (address signer) {
        if (signature.length != 65) return address(0);
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly ("memory-safe") {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (v != 27 && v != 28) return address(0);
        if (uint256(s) > HALF_ORDER || uint256(s) == 0 || uint256(r) == 0) return address(0);
        return ecrecover(digest, v, r, s);
    }

    /// True only if `signature` is a canonical signature of `digest` by the non-zero `expected`.
    function isValid(bytes32 digest, bytes memory signature, address expected) internal pure returns (bool) {
        address signer = tryRecover(digest, signature);
        return signer != address(0) && signer == expected;
    }
}

/// q-of-n verification over a fixed witness set. E uses q = 1 of 1; F uses q = 3 of 4.
/// Signatures must be sorted by strictly increasing recovered signer address.
library QuorumLib {
    function verify(bytes32 digest, bytes[] memory signatures, address[] memory witnesses, uint256 threshold)
        internal
        pure
        returns (ErrorCode)
    {
        if (threshold == 0 || threshold > witnesses.length) return ErrorCode.INSUFFICIENT_QUORUM;
        address previous = address(0);
        uint256 counted = 0;
        for (uint256 i = 0; i < signatures.length; i++) {
            address signer = SigLib.tryRecover(digest, signatures[i]);
            if (signer == address(0) || !_contains(witnesses, signer)) return ErrorCode.BAD_SIGNATURE;
            if (signer == previous) return ErrorCode.DUPLICATE_SIGNER;
            if (signer < previous) {
                // Unsorted input could hide a duplicate further back; reject rather than search.
                return _contains(_prefix(signatures, i, digest), signer)
                    ? ErrorCode.DUPLICATE_SIGNER
                    : ErrorCode.MALFORMED;
            }
            previous = signer;
            counted++;
        }
        return counted >= threshold ? ErrorCode.NONE : ErrorCode.INSUFFICIENT_QUORUM;
    }

    function _contains(address[] memory xs, address x) private pure returns (bool) {
        for (uint256 i = 0; i < xs.length; i++) {
            if (xs[i] == x) return true;
        }
        return false;
    }

    function _prefix(bytes[] memory signatures, uint256 n, bytes32 digest) private pure returns (address[] memory out) {
        out = new address[](n);
        for (uint256 i = 0; i < n; i++) {
            out[i] = SigLib.tryRecover(digest, signatures[i]);
        }
    }
}
