// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCHash, RevocationList, TemporalAcl, TempAclEntry} from "../src/types/ProtocolTypes.sol";
import {TMSC} from "../src/TMSC.sol";
import {RSC} from "../src/RSC.sol";
import {FixtureConfig} from "./FixtureConfig.sol";
import {BootstrapFixture} from "./BootstrapFixture.s.sol";

/// TEST-ONLY signed trust-list producer for E2 schedules (A1-0034): one authority-root-signed RevocationList
/// or TemporalAcl for a pinned PBC deployment, in the frozen v1 wire shape, using the bootstrap producer's
/// helpers (BootstrapFixture is reused unchanged). READ-ONLY: it never broadcasts and writes no private key.
/// Entry point `sign()` (use tools/sign_list.sh). Env, besides TMSC, RSC, EXPECT_CHAIN_ID,
/// DEPLOYMENT_SHA256 and OUT:
///   LIST_KIND crl|tempacl; LIST_AUTHORITY H1..H4; LIST_VERSION (0 or unset = on-chain version + 1;
///   any other value is used as given, e.g. an equal version); LIST_VALID_FOR seconds (default 1 day);
///   REVOKED "s1,s2" (crl; emitted in the given order, the TMSC requires strictly ascending);
///   DUTY_GIDS "alice,bob", DUTY_FROM_AGO "60,60", DUTY_UNTIL_IN "20,3600" (tempacl; OnDuty entries
///   valid [t - ago, t + in]).
contract SignList is BootstrapFixture {
    function sign() external {
        Ctx memory c = Ctx(TMSC(vm.envAddress("TMSC")), RSC(vm.envAddress("RSC")), uint64(block.timestamp));
        require(block.chainid == vm.envUint("EXPECT_CHAIN_ID"), "PBC chain id differs from deployment.json");
        require(address(c.tmsc).code.length > 0, "no TMSC code at the deployment address");
        require(address(c.rsc).code.length > 0, "no RSC code at the deployment address");
        require(address(c.rsc.tmsc()) == address(c.tmsc), "RSC is not wired to this TMSC");
        require(c.tmsc.pbcChainId() == block.chainid, "TMSC was deployed for another chain");

        string memory h = vm.envString("LIST_AUTHORITY");
        address root = vm.addr(FixtureConfig.key(string.concat(h, "-root")));
        require(c.tmsc.isAuthority(root), "LIST_AUTHORITY is not a configured authority");
        uint64 validUntil = c.t + uint64(vm.envOr("LIST_VALID_FOR", uint256(1 days)));
        bytes32 kind = keccak256(bytes(vm.envString("LIST_KIND")));
        string memory item;
        if (kind == keccak256("crl")) {
            item = _crl(c, h, root, validUntil);
        } else if (kind == keccak256("tempacl")) {
            item = _acl(c, h, root, validUntil);
        } else {
            revert("LIST_KIND must be crl or tempacl");
        }
        vm.writeFile(
            vm.envString("OUT"),
            string.concat(
                "{",
                _kv("schemaVersion", _q("hmbc-ledger-signed-list/v0")),
                ",",
                _kv("producer", _q("agent-1 ledger/tools/sign_list.sh (script/SignList.s.sol)")),
                ",",
                _kv("testOnly", "true"),
                ",",
                _binding(c),
                ",",
                _kv("item", item),
                "}"
            )
        );
    }

    function _version(uint64 onChain) internal view returns (uint64) {
        uint256 v = vm.envOr("LIST_VERSION", uint256(0));
        return v == 0 ? onChain + 1 : uint64(v);
    }

    function _crl(Ctx memory c, string memory h, address root, uint64 validUntil) internal view returns (string memory) {
        uint256[] memory raw = vm.envOr("REVOKED", ",", new uint256[](0));
        RevocationList memory l = RevocationList(
            root, _version(c.tmsc.revocationListState(root).version), validUntil, new uint64[](raw.length)
        );
        string[] memory serials = new string[](raw.length);
        for (uint256 i = 0; i < raw.length; i++) {
            l.revokedSerials[i] = uint64(raw[i]);
            serials[i] = _u(raw[i]);
        }
        bytes memory s =
            _sign(string.concat(h, "-root"), HMBCHash.revocationListDigest(l, block.chainid, address(c.tmsc)));
        string memory list = string.concat(
            "{",
            _kv("authority", _addr(root)),
            ",",
            _kv("version", _u(l.version)),
            ",",
            _kv("validUntil", _u(l.validUntil)),
            ",",
            _kv("revokedSerials", _arr(serials)),
            "}"
        );
        return _listItem(h, "RevocationList", "TMSC.updateRevocationList", list, s, root);
    }

    function _acl(Ctx memory c, string memory h, address root, uint64 validUntil) internal view returns (string memory) {
        string[] memory gids = vm.envOr("DUTY_GIDS", ",", new string[](0));
        uint256[] memory ago = vm.envOr("DUTY_FROM_AGO", ",", new uint256[](0));
        uint256[] memory until = vm.envOr("DUTY_UNTIL_IN", ",", new uint256[](0));
        require(ago.length == gids.length && until.length == gids.length, "DUTY_* lists differ in length");
        TemporalAcl memory a;
        a.authority = root;
        a.version = _version(c.tmsc.temporalAclState(root).version);
        a.validUntil = validUntil;
        a.entries = new TempAclEntry[](gids.length);
        string[] memory entries = new string[](gids.length);
        for (uint256 i = 0; i < gids.length; i++) {
            a.entries[i] = TempAclEntry(
                vm.addr(FixtureConfig.key(gids[i])), FixtureConfig.ROLE_ON_DUTY, c.t - uint64(ago[i]), c.t + uint64(until[i])
            );
            entries[i] = _entryJson(a.entries[i]);
        }
        bytes memory s = _sign(string.concat(h, "-root"), HMBCHash.temporalAclDigest(a, block.chainid, address(c.tmsc)));
        string memory list = string.concat(
            "{",
            _kv("authority", _addr(root)),
            ",",
            _kv("version", _u(a.version)),
            ",",
            _kv("validUntil", _u(a.validUntil)),
            ",",
            _kv("entries", _arr(entries)),
            "}"
        );
        return _listItem(h, "TemporalAcl", "TMSC.updateTemporalAcl", list, s, root);
    }

    function _entryJson(TempAclEntry memory e) internal pure returns (string memory) {
        return string.concat(
            "{",
            _kv("gid", _addr(e.gid)),
            ",",
            _kv("role", _b32(e.role)),
            ",",
            _kv("validFrom", _u(e.validFrom)),
            ",",
            _kv("validUntil", _u(e.validUntil)),
            "}"
        );
    }
}
