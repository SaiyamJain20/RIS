// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {TestBase} from "./utils/TestBase.sol";
import {
    Profile,
    ErrorCode,
    isRepaired,
    MUT_NO_RECEIPT_BINDING,
    MUT_NO_GOV_ACTION_BINDING,
    MUT_NO_GOV_NONCE,
    MUT_NO_POLICY_PIN,
    MUT_ALL
} from "../src/types/ProtocolTypes.sol";
import {LSC} from "../src/LSC.sol";
import {TMSC} from "../src/TMSC.sol";
import {RSC} from "../src/RSC.sol";
import {PSC} from "../src/PSC.sol";
import {KSSC} from "../src/KSSC.sol";
import {ACSC} from "../src/ACSC.sol";
import {FixtureConfig} from "../script/FixtureConfig.sol";

/// A-F1 slice 1 (design 2.2 section 1): the REPAIRED_F profile carrier, `isRepaired`, the bit 6-8
/// constants and the constructor mutation guards of TMSC, PSC, KSSC and ACSC. The witness-set
/// checks of PSC and KSSC are two of the section 1 profile gates and are exercised here directly;
/// the other gates are covered by the F reruns of the E suites.
contract ProfileFTest is TestBase {
    uint256 internal constant PBC = FixtureConfig.PBC_CHAIN_ID;
    uint256 internal constant DBC = FixtureConfig.DBC_CHAIN_ID;
    Profile[4] internal profiles = [Profile.PAPER_STRICT, Profile.PAPER_MINIMAL, Profile.REPAIRED_E, Profile.REPAIRED_F];

    function _witnesses() internal pure returns (address[] memory ws) {
        ws = new address[](4);
        ws[0] = vm.addr(FixtureConfig.key("witness-1"));
        ws[1] = vm.addr(FixtureConfig.key("witness-2"));
        ws[2] = vm.addr(FixtureConfig.key("witness-3"));
        ws[3] = vm.addr(FixtureConfig.key("witness-4"));
    }

    function _tmsc(Profile p, uint256 m) internal returns (TMSC) {
        vm.chainId(PBC);
        return new TMSC(p, m, LSC(address(0x1001)), new TMSC.AuthorityConfig[](0));
    }

    function _psc(Profile p, uint256 m, address[] memory ws, uint256 q) internal returns (PSC) {
        vm.chainId(PBC);
        return new PSC(
            PSC.Config(
                p, m, RSC(address(0x1002)), TMSC(address(0x1003)), LSC(address(0x1001)), address(0x1004), 1, 30, 2, ws, q
            )
        );
    }

    function _kssc(Profile p, uint256 m, address[] memory ws, uint256 q) internal returns (KSSC) {
        vm.chainId(DBC);
        return new KSSC(KSSC.Config(p, m, DBC, PBC, address(0x1005), 2, ws, q, 60));
    }

    function _acsc(Profile p, uint256 m) internal returns (ACSC) {
        vm.chainId(DBC);
        return new ACSC(p, m, DBC, PBC, address(0x1005), 1, 30);
    }

    /// Deploys all four mask holders with (p, m); with `want` != NONE each constructor must revert Rejected(want).
    function _allFour(Profile p, uint256 m, ErrorCode want) internal {
        if (want != ErrorCode.NONE) expectRejected(want);
        _tmsc(p, m);
        if (want != ErrorCode.NONE) expectRejected(want);
        _psc(p, m, _witnesses(), 3);
        if (want != ErrorCode.NONE) expectRejected(want);
        _kssc(p, m, _witnesses(), 3);
        if (want != ErrorCode.NONE) expectRejected(want);
        _acsc(p, m);
    }

    function test_AF1_ProfileEnumAppendsRepairedF() public pure {
        assertEq(uint256(Profile.PAPER_STRICT), 0, "PAPER_STRICT index");
        assertEq(uint256(Profile.PAPER_MINIMAL), 1, "PAPER_MINIMAL index");
        assertEq(uint256(Profile.REPAIRED_E), 2, "REPAIRED_E index");
        assertEq(uint256(Profile.REPAIRED_F), 3, "REPAIRED_F index");
    }

    function test_AF1_IsRepairedOnlyForTheRepairedProfiles() public pure {
        assertFalse(isRepaired(Profile.PAPER_STRICT), "paper-strict");
        assertFalse(isRepaired(Profile.PAPER_MINIMAL), "paper-minimal");
        assertTrue(isRepaired(Profile.REPAIRED_E), "repaired-e");
        assertTrue(isRepaired(Profile.REPAIRED_F), "repaired-f");
    }

    function test_AF1_MutationBitsSixToEightAndMask() public pure {
        assertEq(MUT_NO_RECEIPT_BINDING, 1 << 5, "bit 5 unchanged");
        assertEq(MUT_NO_GOV_ACTION_BINDING, 1 << 6, "bit 6");
        assertEq(MUT_NO_GOV_NONCE, 1 << 7, "bit 7");
        assertEq(MUT_NO_POLICY_PIN, 1 << 8, "bit 8");
        assertEq(MUT_ALL, 511, "MUT_ALL = (1 << 9) - 1");
    }

    function test_AF1_RepairedFAcceptsEveryBitUpToEight() public {
        for (uint256 b = 0; b <= 8; b++) {
            _allFour(Profile.REPAIRED_F, 1 << b, ErrorCode.NONE);
        }
        _allFour(Profile.REPAIRED_F, MUT_ALL, ErrorCode.NONE);
        _allFour(Profile.REPAIRED_F, 0, ErrorCode.NONE);
    }

    function test_AF1_RepairedERejectsTheFBits() public {
        for (uint256 b = 6; b <= 8; b++) {
            _allFour(Profile.REPAIRED_E, 1 << b, ErrorCode.MALFORMED);
        }
        // positive control: the E bits are unchanged for REPAIRED_E
        for (uint256 b = 0; b <= 5; b++) {
            _allFour(Profile.REPAIRED_E, 1 << b, ErrorCode.NONE);
        }
    }

    function test_AF1_PaperProfilesRejectAnyBit() public {
        _allFour(Profile.PAPER_STRICT, 1 << 0, ErrorCode.MALFORMED);
        _allFour(Profile.PAPER_STRICT, 1 << 6, ErrorCode.MALFORMED);
        _allFour(Profile.PAPER_MINIMAL, 1 << 0, ErrorCode.MALFORMED);
        _allFour(Profile.PAPER_MINIMAL, 1 << 8, ErrorCode.MALFORMED);
    }

    function test_AF1_BitNineRejectedInEveryProfile() public {
        for (uint256 i = 0; i < 4; i++) {
            _allFour(profiles[i], 1 << 9, ErrorCode.MALFORMED);
        }
    }

    /// PSC.sol:113 and KSSC.sol:105 gates: the witness-set checks apply under REPAIRED_F too.
    function test_AF1_RepairedFValidatesTheWitnessSet() public {
        address[] memory ws = _witnesses();
        expectRejected(ErrorCode.MALFORMED);
        _psc(Profile.REPAIRED_F, 0, ws, 0);
        expectRejected(ErrorCode.MALFORMED);
        _psc(Profile.REPAIRED_F, 0, ws, 5);
        expectRejected(ErrorCode.MALFORMED);
        _kssc(Profile.REPAIRED_F, 0, ws, 0);
        expectRejected(ErrorCode.MALFORMED);
        _kssc(Profile.REPAIRED_F, 0, ws, 5);
        address[] memory dup = _witnesses();
        dup[3] = dup[1];
        expectRejected(ErrorCode.DUPLICATE_SIGNER);
        _psc(Profile.REPAIRED_F, 0, dup, 3);
        expectRejected(ErrorCode.DUPLICATE_SIGNER);
        _kssc(Profile.REPAIRED_F, 0, dup, 3);
        address[] memory zero = _witnesses();
        zero[2] = address(0);
        expectRejected(ErrorCode.MALFORMED);
        _psc(Profile.REPAIRED_F, 0, zero, 3);
        expectRejected(ErrorCode.MALFORMED);
        _kssc(Profile.REPAIRED_F, 0, zero, 3);
        // positive control: q = 3 of 4 and q = 2 of 4 (the mutant-f-q2 configuration) deploy
        _psc(Profile.REPAIRED_F, 0, ws, 3);
        _kssc(Profile.REPAIRED_F, 0, ws, 3);
        _psc(Profile.REPAIRED_F, 0, ws, 2);
        _kssc(Profile.REPAIRED_F, 0, ws, 2);
    }
}
