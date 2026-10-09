"""Test-infrastructure guards (live)."""
import ledger_setup as setup
from hmbc_protocol import ledger as ledger_mod
from support import rpc


def test_setup_time_comes_from_a_fresh_block_not_the_stale_deployment_head(ledger):
    """Anvil timestamps new blocks from the wall clock, but `get_block('latest')` is the LAST mined block. After the session has been alive for a while
    that head is old, so anything derived from it (a 20 s duty window) can already be over when setup runs. Simulate 25 s of idle time and require the
    short duty window to be live right after setup."""
    led = ledger_mod.Ledger.from_deployment(ledger.deployment)
    rpc(ledger.pbc_url, "evm_increaseTime", [25])                                    # the chain's clock moves on; no block is mined
    ctx = setup.setup_pbc(led, duty_seconds=20)
    now = led.pbc.get_block()["timestamp"]
    code, records = led.pbc.call(led.TMSC, "checkCredentials", ctx.alice, ctx.bundle, str(now))
    assert code == "0" and len(records) == 2, "the temporal duty entry was already expired when setup finished"
