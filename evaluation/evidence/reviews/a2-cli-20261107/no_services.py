"""Refuse live fixture setup before its body, including dynamic fixture requests."""
import pytest

@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    name = fixturedef.argname
    if name.startswith(('ledger_chains', 'world')) or name in {'ledger', 'ledger_paper', 'ledger_paper_minimal', 'ledger_no_nonce', 'ledger_no_receipt_binding', 'f_deployment', 'e_deployment'}:
        pytest.fail('No-service review refuses fixture setup: ' + name)
