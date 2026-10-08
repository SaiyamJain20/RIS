// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Vm, VM_ADDRESS} from "../test/utils/Vm.sol";
import {
    HMBCHash,
    Registration,
    RoleCertificate,
    SignedRoleCertificate,
    RevocationList,
    TemporalAcl,
    TempAclEntry,
    TemporalClaim
} from "../src/types/ProtocolTypes.sol";
import {TMSC} from "../src/TMSC.sol";
import {RSC} from "../src/RSC.sol";
import {FixtureConfig} from "./FixtureConfig.sol";

/// TEST-ONLY bootstrap producer for the C-E1 runner (A1-0029, answer to A3-0024). Read-only: it never
/// broadcasts. It reads a pinned PBC deployment (TMSC, RSC) and the PBC latest block timestamp t, then
/// signs with the synthetic FixtureConfig keys the public artifacts the runner submits:
/// authority-root-signed trust lists, role certificates, GID-possession registrations and credential
/// bundles for Alice (Doctor + OnDuty, H1) and Bob (Researcher, H2; registered, policy-denied on the
/// DBC). Every leaf uses a frozen v1 wire shape. No private key is written; signer addresses only.
/// Env: TMSC, RSC, EXPECT_CHAIN_ID, DEPLOYMENT_SHA256, OUT (a path under exports/). Use
/// tools/bootstrap_fixture.sh.
contract BootstrapFixture {
    Vm internal constant vm = Vm(VM_ADDRESS);

    uint64 internal constant ALICE_SERIAL = 101;
    uint64 internal constant BOB_SERIAL = 201;
    uint64 internal constant CERT_VALID_FROM = 1_700_000_000;
    uint64 internal constant CERT_VALID_UNTIL = 2_100_000_000;
    uint64 internal constant LIST_TTL = 1 days;
    uint64 internal constant ON_DUTY_TTL = 8 hours;
    uint64 internal constant REGISTRATION_TTL = 1 hours;

    struct Ctx {
        TMSC tmsc;
        RSC rsc;
        uint64 t;
    }

    function run() external {
        Ctx memory c = Ctx(TMSC(vm.envAddress("TMSC")), RSC(vm.envAddress("RSC")), uint64(block.timestamp));
        require(block.chainid == vm.envUint("EXPECT_CHAIN_ID"), "PBC chain id differs from deployment.json");
        require(address(c.tmsc).code.length > 0, "no TMSC code at the deployment address");
        require(address(c.rsc).code.length > 0, "no RSC code at the deployment address");
        require(address(c.rsc.tmsc()) == address(c.tmsc), "RSC is not wired to this TMSC");
        require(c.tmsc.pbcChainId() == block.chainid, "TMSC was deployed for another chain");

        string memory json = string.concat(
            "{",
            _kv("schemaVersion", _q("hmbc-ledger-bootstrap/v0")),
            ",",
            _kv("producer", _q("agent-1 ledger/tools/bootstrap_fixture.sh (script/BootstrapFixture.s.sol)")),
            ",",
            _kv("testOnly", "true"),
            ",",
            _binding(c),
            ",",
            _kv("trustLists", _trustLists(c)),
            ",",
            _kv("users", string.concat("{", _kv("alice", _alice(c)), ",", _kv("bob", _bob(c)), "}")),
            ",",
            _notes(),
            "}"
        );
        vm.writeFile(vm.envString("OUT"), json);
    }

    // ------------------------------------------------------------------ sections

    function _binding(Ctx memory c) internal view returns (string memory) {
        return _kv(
            "binding",
            string.concat(
                "{",
                _kv("pbcChainId", _u(block.chainid)),
                ",",
                _kv("tmsc", _addr(address(c.tmsc))),
                ",",
                _kv("rsc", _addr(address(c.rsc))),
                ",",
                _kv("blockNumber", _u(block.number)),
                ",",
                _kv("blockTimestamp", _u(c.t)),
                ",",
                _kv("deploymentSha256", _q(vm.envString("DEPLOYMENT_SHA256"))),
                ",",
                _kv("profile", _u(uint8(c.tmsc.profile()))),
                "}"
            )
        );
    }

    function _trustLists(Ctx memory c) internal view returns (string memory) {
        string[] memory items = new string[](3);
        items[0] = _crlItem(c, "H1");
        items[1] = _aclItem(c);
        items[2] = _crlItem(c, "H2");
        return _arr(items);
    }

    function _crlItem(Ctx memory c, string memory h) internal view returns (string memory) {
        address root = vm.addr(FixtureConfig.key(string.concat(h, "-root")));
        RevocationList memory l =
            RevocationList(root, c.tmsc.revocationListState(root).version + 1, c.t + LIST_TTL, new uint64[](0));
        bytes memory s =
            _sign(string.concat(h, "-root"), HMBCHash.revocationListDigest(l, block.chainid, address(c.tmsc)));
        string memory list = string.concat(
            "{",
            _kv("authority", _addr(l.authority)),
            ",",
            _kv("version", _u(l.version)),
            ",",
            _kv("validUntil", _u(l.validUntil)),
            ",",
            _kv("revokedSerials", "[]"),
            "}"
        );
        return _listItem(h, "RevocationList", "TMSC.updateRevocationList", list, s, root);
    }

    function _aclItem(Ctx memory c) internal view returns (string memory) {
        address root = vm.addr(FixtureConfig.key("H1-root"));
        address alice = vm.addr(FixtureConfig.key("alice"));
        TemporalAcl memory a;
        a.authority = root;
        a.version = c.tmsc.temporalAclState(root).version + 1;
        a.validUntil = c.t + LIST_TTL;
        a.entries = new TempAclEntry[](1);
        a.entries[0] = TempAclEntry(alice, FixtureConfig.ROLE_ON_DUTY, c.t - 60, c.t + ON_DUTY_TTL);
        bytes memory s = _sign("H1-root", HMBCHash.temporalAclDigest(a, block.chainid, address(c.tmsc)));
        string memory entry = string.concat(
            "{",
            _kv("gid", _addr(alice)),
            ",",
            _kv("role", _b32(FixtureConfig.ROLE_ON_DUTY)),
            ",",
            _kv("validFrom", _u(a.entries[0].validFrom)),
            ",",
            _kv("validUntil", _u(a.entries[0].validUntil)),
            "}"
        );
        string memory list = string.concat(
            "{",
            _kv("authority", _addr(root)),
            ",",
            _kv("version", _u(a.version)),
            ",",
            _kv("validUntil", _u(a.validUntil)),
            ",",
            _kv("entries", string.concat("[", entry, "]")),
            "}"
        );
        return _listItem("H1", "TemporalAcl", "TMSC.updateTemporalAcl", list, s, root);
    }

    function _listItem(
        string memory h,
        string memory kind,
        string memory call,
        string memory list,
        bytes memory signature,
        address signer
    ) internal pure returns (string memory) {
        string memory admin = string.concat(h, "-ca-admin");
        return string.concat(
            "{",
            _kv("kind", _q(kind)),
            ",",
            _kv("call", _q(call)),
            ",",
            _kv("submitterRole", _q(admin)),
            ",",
            _kv("submitter", _addr(vm.addr(FixtureConfig.key(admin)))),
            ",",
            _kv("list", list),
            ",",
            _kv("signature", _q(vm.toString(signature))),
            ",",
            _kv("signer", _addr(signer)),
            "}"
        );
    }

    function _alice(Ctx memory c) internal view returns (string memory) {
        SignedRoleCertificate memory cert = _cert(c, "H1", "alice", FixtureConfig.ROLE_DOCTOR, ALICE_SERIAL);
        string memory claim = string.concat(
            "{",
            _kv("authority", _addr(vm.addr(FixtureConfig.key("H1-root")))),
            ",",
            _kv("role", _b32(FixtureConfig.ROLE_ON_DUTY)),
            "}"
        );
        return _user(c, "alice", cert, string.concat("[", claim, "]"));
    }

    function _bob(Ctx memory c) internal view returns (string memory) {
        SignedRoleCertificate memory cert = _cert(c, "H2", "bob", FixtureConfig.ROLE_RESEARCHER, BOB_SERIAL);
        return _user(c, "bob", cert, "[]");
    }

    function _cert(Ctx memory c, string memory h, string memory user, bytes32 role, uint64 serial)
        internal
        view
        returns (SignedRoleCertificate memory sc)
    {
        bytes32[] memory roles = new bytes32[](1);
        roles[0] = role;
        RoleCertificate memory rc = RoleCertificate(
            vm.addr(FixtureConfig.key(string.concat(h, "-root"))),
            vm.addr(FixtureConfig.key(user)),
            roles,
            serial,
            CERT_VALID_FROM,
            CERT_VALID_UNTIL
        );
        sc = SignedRoleCertificate(
            rc, _sign(string.concat(h, "-root"), HMBCHash.roleCertificateDigest(rc, block.chainid, address(c.tmsc)))
        );
    }

    function _user(Ctx memory c, string memory label, SignedRoleCertificate memory cert, string memory claims)
        internal
        view
        returns (string memory)
    {
        string memory keyLabel = string.concat("HMBC.recipient-key.", label);
        Registration memory reg = Registration(
            cert.cert.gid,
            HMBCHash.roleCertificateDigest(cert.cert, block.chainid, address(c.tmsc)),
            keccak256(bytes(keyLabel)),
            c.t + REGISTRATION_TTL
        );
        bytes memory possession = _sign(label, HMBCHash.registrationDigest(reg, block.chainid, address(c.rsc)));
        string memory head = string.concat(
            "{",
            _kv("gid", _addr(reg.gid)),
            ",",
            _kv("recipientKeyLabel", _q(keyLabel)),
            ",",
            _kv("recipientKeyHash", _b32(reg.recipientKeyHash)),
            ","
        );
        return string.concat(head, _userTail(cert, reg, possession, claims));
    }

    function _userTail(
        SignedRoleCertificate memory cert,
        Registration memory reg,
        bytes memory possession,
        string memory claims
    ) internal pure returns (string memory) {
        string memory certJson = _certJson(cert);
        string memory bundle = string.concat(
            "{", _kv("certificates", string.concat("[", certJson, "]")), ",", _kv("temporalClaims", claims), "}"
        );
        return string.concat(
            _kv("certificate", certJson),
            ",",
            _kv("registration", _registrationJson(reg)),
            ",",
            _kv("possessionSignature", _q(vm.toString(possession))),
            ",",
            _kv("bundle", bundle),
            "}"
        );
    }

    function _certJson(SignedRoleCertificate memory sc) internal pure returns (string memory) {
        string[] memory roles = new string[](sc.cert.roles.length);
        for (uint256 i = 0; i < roles.length; i++) {
            roles[i] = _b32(sc.cert.roles[i]);
        }
        string memory body = string.concat(
            "{",
            _kv("issuer", _addr(sc.cert.issuer)),
            ",",
            _kv("gid", _addr(sc.cert.gid)),
            ",",
            _kv("roles", _arr(roles)),
            ",",
            _kv("serial", _u(sc.cert.serial)),
            ",",
            _kv("validFrom", _u(sc.cert.validFrom)),
            ",",
            _kv("validUntil", _u(sc.cert.validUntil)),
            "}"
        );
        return string.concat("{", _kv("cert", body), ",", _kv("signature", _q(vm.toString(sc.signature))), "}");
    }

    function _registrationJson(Registration memory r) internal pure returns (string memory) {
        return string.concat(
            "{",
            _kv("gid", _addr(r.gid)),
            ",",
            _kv("certDigest", _b32(r.certDigest)),
            ",",
            _kv("recipientKeyHash", _b32(r.recipientKeyHash)),
            ",",
            _kv("expiresAt", _u(r.expiresAt)),
            "}"
        );
    }

    function _notes() internal pure returns (string memory) {
        string[] memory order = new string[](3);
        order[0] = _q("submit trustLists in array order, each from its submitterRole account (TEST-ONLY CA-Admin key)");
        order[1] = _q("then RSC.register(registration, possessionSignature, certificate) for alice and bob from any funded account, before registration.expiresAt");
        order[2] = _q("pass users.<label>.bundle as the CredentialBundle of PSC.requestAccess; request signing stays with the agent-2 adapter (keyref:user:<label>)");
        string[] memory limits = new string[](4);
        limits[0] = _q("TEST-ONLY synthetic keys: privateKey = keccak256('hmbc-e0-synthetic-key:' || label); no private key is written here");
        limits[1] = _q("list versions are the current on-chain version + 1 at blockTimestamp; lists and the OnDuty window are relative to blockTimestamp");
        limits[2] = _q("certificates use fixed validity 1700000000..2100000000; registrations expire blockTimestamp + 3600");
        limits[3] = _q("Bob holds valid Researcher credentials and fails the P1 Doctor+OnDuty policy on the DBC; he is not a NOT_REGISTERED control");
        return string.concat(_kv("order", _arr(order)), ",", _kv("limits", _arr(limits)));
    }

    // ------------------------------------------------------------------ helpers

    function _sign(string memory label, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(FixtureConfig.key(label), digest);
        return abi.encodePacked(r, s, v);
    }

    function _q(string memory s) internal pure returns (string memory) {
        return string.concat('"', s, '"');
    }

    function _kv(string memory k, string memory v) internal pure returns (string memory) {
        return string.concat(_q(k), ":", v);
    }

    function _u(uint256 x) internal pure returns (string memory) {
        return _q(vm.toString(x));
    }

    function _b32(bytes32 x) internal pure returns (string memory) {
        return _q(vm.toString(x));
    }

    function _addr(address a) internal pure returns (string memory) {
        bytes memory hexChars = "0123456789abcdef";
        bytes memory out = new bytes(42);
        out[0] = "0";
        out[1] = "x";
        uint160 v = uint160(a);
        for (uint256 i = 0; i < 20; i++) {
            uint8 b = uint8(v >> (8 * (19 - i)));
            out[2 + 2 * i] = hexChars[b >> 4];
            out[3 + 2 * i] = hexChars[b & 15];
        }
        return _q(string(out));
    }

    function _arr(string[] memory xs) internal pure returns (string memory out) {
        out = "[";
        for (uint256 i = 0; i < xs.length; i++) {
            out = string.concat(out, i == 0 ? "" : ",", xs[i]);
        }
        out = string.concat(out, "]");
    }
}
