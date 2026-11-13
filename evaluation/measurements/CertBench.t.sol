// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
// MEASUREMENT HARNESS by agent 3 (scratch copy of ledger 85c59f5; not part of the ledger module).
import {HMBCFixture} from "./utils/Fixture.sol";
import {GrantReceipt, RESULT_ALLOW, Profile, HMBCHash, AccessRequest, CredentialRecord, StateCheckpoint, AccessDecision, DecisionCertificate} from "../src/types/ProtocolTypes.sol";

abstract contract BenchBase is HMBCFixture {
    event Measure(string name, uint256 sigs, uint256 gas, uint256 calldataBytes);

    function pickPks(uint256 n) internal view returns (uint256[] memory xs) {
        xs = new uint256[](n);
        for (uint256 i = 0; i < n; i++) xs[i] = witnessPks[i];
    }

    function sigsFor(uint256 n, bytes32 d) internal view returns (bytes[] memory) {
        if (n == 1 && !isRepairedF()) return witnessSigs(witnessPk, d);
        return sortedSigs(pickPks(n), d);
    }

    function isRepairedF() internal pure returns (bool) { return profile() == Profile.REPAIRED_F; }

    function benchCheckpoint(uint256 n) internal {
        StateCheckpoint memory cp = checkpointNow();
        bytes[] memory s = sigsFor(n, HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc)));
        uint256 cd = abi.encodeCall(kssc.acceptState, (cp, s)).length;
        uint256 g = gasleft();
        kssc.acceptState(cp, s);
        g -= gasleft();
        emit Measure("acceptState", n, g, cd);
    }

    function benchDecision(uint256 n) internal {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp = checkpointNow();
        kssc.acceptState(cp, sigsFor(isRepairedF() ? 3 : 1, HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc))));
        AccessDecision memory d = decisionFor(r, 1, recs, cp);
        DecisionCertificate memory c;
        c.decision = d;
        c.signatures = sigsFor(n, HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
        uint256 cd = abi.encodeCall(acsc.consumeDecision, (r, c, recs)).length;
        vm.prank(relay);
        uint256 g = gasleft();
        acsc.consumeDecision(r, c, recs);
        g -= gasleft();
        emit Measure("consumeDecision", n, g, cd);
    }
    function benchReceipt(uint256 n) internal {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 d, CredentialRecord[] memory recs) = aliceForwarded(1);
        bytes32 grantId = deliver(r, recs, d, RESULT_ALLOW);
        GrantReceipt memory g = receiptFor(grantId);
        bytes[] memory s = sigsFor(n, HMBCHash.grantReceiptDigest(g, PBC_CHAIN_ID, address(psc)));
        bytes32 outcome = keccak256("synthetic-outcome");
        uint256 cd = abi.encodeCall(psc.reportAttestedOutcome, (d, outcome, g, s)).length;
        vm.prank(relay);
        uint256 gs = gasleft();
        psc.reportAttestedOutcome(d, outcome, g, s);
        gs -= gasleft();
        emit Measure("reportAttestedOutcome", n, gs, cd);
    }
}

contract BenchE is BenchBase {
    function profile() internal pure override returns (Profile) { return Profile.REPAIRED_E; }
    function test_E_checkpoint_1() public { benchCheckpoint(1); }
    function test_E_decision_1() public { benchDecision(1); }
    function test_E_receipt_1() public { benchReceipt(1); }
}

contract BenchF is BenchBase {
    function profile() internal pure override returns (Profile) { return Profile.REPAIRED_F; }
    function test_F_checkpoint_3() public { benchCheckpoint(3); }
    function test_F_checkpoint_4() public { benchCheckpoint(4); }
    function test_F_decision_3() public { benchDecision(3); }
    function test_F_decision_4() public { benchDecision(4); }
    function test_F_receipt_3() public { benchReceipt(3); }
    function test_F_receipt_4() public { benchReceipt(4); }
}
