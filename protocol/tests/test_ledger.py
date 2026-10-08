import copy

import pytest

from hmbc_protocol import ledger


def test_from_deployment_loads_all_six_contracts_with_deployed_addresses(ledger_chains):
    led = ledger.Ledger.from_deployment(ledger_chains.deployment)
    dep = ledger_chains.deployment["chains"]
    assert led.pbc.chain_id == int(dep["pbc"]["chainId"]) and led.dbc.chain_id == int(dep["dbc"]["chainId"])
    for name, side in (("PSC", "pbc"), ("RSC", "pbc"), ("TMSC", "pbc"), ("LSC", "pbc"), ("ACSC", "dbc"), ("KSSC", "dbc")):
        assert getattr(led, name).address == dep[side]["contracts"][name]
    assert led.pbc.url == dep["pbc"]["rpcUrl"] and led.dbc.url == dep["dbc"]["rpcUrl"]


def test_abi_hash_mismatch_is_refused(ledger_chains):
    bad = copy.deepcopy(ledger_chains.deployment)
    bad["abi"]["PSC"]["abiSha256"] = "0" * 64
    with pytest.raises(ledger.LedgerError, match="PSC"):
        ledger.Ledger.from_deployment(bad)


def test_missing_or_malformed_contract_entries_are_refused(ledger_chains):
    for mutate in (lambda d: d["chains"]["pbc"]["contracts"].pop("RSC"),
                   lambda d: d["chains"]["dbc"]["contracts"].__setitem__("KSSC", "0xABC"),
                   lambda d: d["abi"].pop("TMSC"),
                   lambda d: d["chains"]["pbc"].__setitem__("rpcUrl", "file:///etc/passwd")):
        bad = copy.deepcopy(ledger_chains.deployment)
        mutate(bad)
        with pytest.raises(ledger.LedgerError):
            ledger.Ledger.from_deployment(bad)
