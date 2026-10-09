"""Offline edge cases for the ABI/chain layers (no node needed)."""
import pytest

from hmbc_protocol import abi, chain

KSSC_LIKE = abi.Contract([{"type": "function", "name": "f", "stateMutability": "view",
                           "inputs": [{"name": "a", "type": "uint64"}, {"name": "b", "type": "bytes32[]"}, {"name": "c", "type": "bytes"}, {"name": "d", "type": "bool"}],
                           "outputs": []}])
OK = ["1", ["0x" + "11" * 32], "0x00ff", True]


def test_valid_arguments_encode():
    assert KSSC_LIKE.calldata("f", *OK)[:4] == KSSC_LIKE.selector("f")


@pytest.mark.parametrize("bad", [
    ["-1", OK[1], OK[2], OK[3]], ["18446744073709551616", OK[1], OK[2], OK[3]], [1, OK[1], OK[2], OK[3]], [True, OK[1], OK[2], OK[3]],
    ["01", OK[1], OK[2], OK[3]], ["1 ", OK[1], OK[2], OK[3]], ["1", ["0x" + "11" * 31], OK[2], OK[3]], ["1", "0x" + "11" * 32, OK[2], OK[3]],
    ["1", [None], OK[2], OK[3]], ["1", OK[1], "0xf", OK[3]], ["1", OK[1], "0xFF", OK[3]], ["1", OK[1], b"\x00", OK[3]], ["1", OK[1], OK[2], 1],
    ["1", OK[1], OK[2], "true"],
])
def test_noncanonical_arguments_are_refused(bad):
    with pytest.raises(abi.AbiError):
        KSSC_LIKE.calldata("f", *bad)


def test_wrong_argument_count_is_refused():
    for args in ([], OK[:3], OK + ["x"]):
        with pytest.raises(abi.AbiError):
            KSSC_LIKE.calldata("f", *args)


def test_overloaded_functions_are_refused_at_load_time():
    dup = {"type": "function", "name": "g", "inputs": [], "outputs": []}
    with pytest.raises(abi.AbiError):
        abi.Contract([dup, {**dup, "inputs": [{"name": "x", "type": "uint8"}]}])


def rejected(code: int) -> str:
    return "0x" + chain.REJECTED_SELECTOR.hex() + format(code, "064x")


def test_revert_data_decodes_to_ledger_names():
    assert chain._revert(rejected(16)).code == "UNAUTHORIZED_CALLER"
    assert chain._revert(rejected(6)).code == "STALE_STATE"
    assert chain._revert(rejected(99)).code == "UNKNOWN_99"


@pytest.mark.parametrize("data", [None, "", "0x", "0x1234", "0xdeadbeef" + "00" * 32, "0x" + chain.REJECTED_SELECTOR.hex(), "zz", 5, {"a": 1}])
def test_other_revert_data_is_not_mistaken_for_a_ledger_error(data):
    assert chain._revert(data) is None


@pytest.mark.parametrize("tag,ok", [("latest", True), (0, True), (5, True), (-1, False), (True, False), ("0x5", False), (1.5, False), (None, False), ("earliest", False)])
def test_block_tags_are_strict(tag, ok):
    if ok:
        assert chain.Chain._tag(tag)
    else:
        with pytest.raises(chain.ChainError):
            chain.Chain._tag(tag)
