// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Vm, VM_ADDRESS} from "../test/utils/Vm.sol";
import {Profile, LogDetailMode} from "../src/types/ProtocolTypes.sol";
import {LSC} from "../src/LSC.sol";
import {TMSC} from "../src/TMSC.sol";
import {RSC} from "../src/RSC.sol";
import {PSC} from "../src/PSC.sol";
import {KSSC} from "../src/KSSC.sol";
import {ACSC} from "../src/ACSC.sol";
import {FixtureConfig} from "./FixtureConfig.sol";

/// Staged two-chain deployment of the six HMBC roles with the synthetic E fixture.
/// The PBC needs the DBC's KSSC address and the DBC needs the PBC's PSC address, so:
///   STAGE=pbc       on the PBC: deploy LSC, TMSC, RSC, PSC; wire LSC/TMSC (not sealed)
///   STAGE=dbc       on the DBC: deploy KSSC, ACSC with PSC=<addr>; policy; seal both
///   STAGE=finalize  on the PBC: PSC.configureDestination(DBC, KSSC=<addr>); seal LSC/TMSC/RSC/PSC
/// Use tools/deploy_local.sh, which runs the stages and writes the deployment manifest.
/// Env: STAGE, PROFILE (0 strict, 1 minimal, 2 repaired-e), LOG_MODE (0 hash-only, 1 complete),
/// DEPLOYER_PK, PBC_CHAIN_ID, DBC_CHAIN_ID, OUT_DIR (under exports/), and per stage PSC / LSC, TMSC,
/// RSC, KSSC addresses. Synthetic actors (authorities, CA-Admins, relay, witness) come from
/// FixtureConfig labels; CA-Admins and the relay are funded so they can send transactions.
contract Deploy {
    Vm internal constant vm = Vm(VM_ADDRESS);
    uint256 internal constant FUNDING = 100 ether;

    function run() external {
        bytes32 stage = keccak256(bytes(vm.envString("STAGE")));
        if (stage == keccak256("pbc")) _pbc();
        else if (stage == keccak256("dbc")) _dbc();
        else if (stage == keccak256("finalize")) _finalize();
        else revert("STAGE must be pbc, dbc or finalize");
    }

    function _profile() internal view returns (Profile) {
        uint256 p = vm.envUint("PROFILE");
        require(p <= uint256(Profile.REPAIRED_E), "PROFILE");
        return Profile(p);
    }

    function _actor(string memory label) internal pure returns (address) {
        return vm.addr(FixtureConfig.key(label));
    }

    function _pbc() internal {
        uint256 pbcChainId = vm.envUint("PBC_CHAIN_ID");
        require(block.chainid == pbcChainId, "connected to the wrong chain for STAGE=pbc");
        uint256 mode = vm.envUint("LOG_MODE");
        require(mode <= 1, "LOG_MODE");
        Profile p = _profile();

        TMSC.AuthorityConfig[] memory cfg = new TMSC.AuthorityConfig[](4);
        string[4] memory names = ["H1", "H2", "H3", "H4"];
        for (uint256 i = 0; i < 4; i++) {
            address[] memory admins = new address[](1);
            admins[0] = _actor(string.concat(names[i], "-ca-admin"));
            cfg[i] = TMSC.AuthorityConfig(_actor(string.concat(names[i], "-root")), admins);
        }

        vm.startBroadcast(vm.envUint("DEPLOYER_PK"));
        LSC lsc = new LSC(LogDetailMode(mode));
        TMSC tmsc = new TMSC(p, vm.envOr("MUTATIONS", uint256(0)), lsc, cfg);
        RSC rsc = new RSC(pbcChainId, tmsc, lsc);
        address[] memory ws = new address[](1);
        ws[0] = _actor("witness-1");
        PSC psc = new PSC(
            PSC.Config(
                p,
                vm.envOr("MUTATIONS", uint256(0)),
                rsc,
                tmsc,
                lsc,
                _actor("relay"),
                FixtureConfig.POLICY_VERSION,
                FixtureConfig.REQUEST_TTL,
                FixtureConfig.WITNESS_SET_VERSION,
                ws,
                1
            )
        );
        lsc.wire(address(rsc), address(tmsc), address(psc));
        tmsc.wire(address(psc), address(rsc));
        for (uint256 i = 0; i < 4; i++) {
            payable(cfg[i].admins[0]).transfer(FUNDING);
        }
        payable(_actor("relay")).transfer(FUNDING);
        vm.stopBroadcast();

        string memory actors = "";
        for (uint256 i = 0; i < 4; i++) {
            actors = string.concat(
                actors, i == 0 ? "" : ",", '{"id":"', names[i], '","root":"', vm.toString(cfg[i].authority),
                '","caAdmins":["', vm.toString(cfg[i].admins[0]), '"]}'
            );
        }
        string memory json = string.concat(
            '{"lsc":"', vm.toString(address(lsc)), '","tmsc":"', vm.toString(address(tmsc)), '","rsc":"',
            vm.toString(address(rsc)), '","psc":"', vm.toString(address(psc)), '","blockNumber":"',
            vm.toString(block.number), '","relay":"', vm.toString(_actor("relay")), '","authorities":[', actors, "]}"
        );
        vm.writeFile(string.concat(vm.envString("OUT_DIR"), "/pbc-stage.json"), json);
    }

    function _dbc() internal {
        uint256 pbcChainId = vm.envUint("PBC_CHAIN_ID");
        uint256 dbcChainId = vm.envUint("DBC_CHAIN_ID");
        require(block.chainid == dbcChainId, "connected to the wrong chain for STAGE=dbc");
        Profile p = _profile();
        address psc = vm.envAddress("PSC");
        address[] memory ws = new address[](1);
        ws[0] = _actor("witness-1");

        vm.startBroadcast(vm.envUint("DEPLOYER_PK"));
        uint256 mutations = vm.envOr("MUTATIONS", uint256(0));
        KSSC kssc = new KSSC(
            KSSC.Config(
                p,
                mutations,
                dbcChainId,
                pbcChainId,
                psc,
                FixtureConfig.WITNESS_SET_VERSION,
                ws,
                1,
                FixtureConfig.CHECKPOINT_TTL
            )
        );
        ACSC acsc =
            new ACSC(p, mutations, dbcChainId, pbcChainId, psc, FixtureConfig.POLICY_VERSION, FixtureConfig.GRANT_TTL);
        kssc.wire(address(acsc));
        acsc.wire(kssc, _actor("relay"));
        uint256 policyId = acsc.addPolicy(FixtureConfig.emergencyPolicy());
        acsc.registerData(FixtureConfig.DATA_P1, _actor("H2-root"), policyId);
        kssc.seal();
        acsc.seal();
        payable(_actor("relay")).transfer(FUNDING);
        vm.stopBroadcast();

        string memory json = string.concat(
            '{"kssc":"', vm.toString(address(kssc)), '","acsc":"', vm.toString(address(acsc)), '","blockNumber":"',
            vm.toString(block.number), '","witnesses":["', vm.toString(ws[0]), '"],"dataOwner":"',
            vm.toString(_actor("H2-root")), '"}'
        );
        vm.writeFile(string.concat(vm.envString("OUT_DIR"), "/dbc-stage.json"), json);
    }

    function _finalize() internal {
        require(block.chainid == vm.envUint("PBC_CHAIN_ID"), "connected to the wrong chain for STAGE=finalize");
        vm.startBroadcast(vm.envUint("DEPLOYER_PK"));
        PSC(vm.envAddress("PSC")).configureDestination(vm.envUint("DBC_CHAIN_ID"), vm.envAddress("KSSC"));
        LSC(vm.envAddress("LSC")).seal();
        TMSC(vm.envAddress("TMSC")).seal();
        RSC(vm.envAddress("RSC")).seal();
        PSC(vm.envAddress("PSC")).seal();
        vm.stopBroadcast();
    }
}
