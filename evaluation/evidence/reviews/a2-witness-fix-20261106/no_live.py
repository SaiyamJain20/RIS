"""Review selection: never execute tests whose fixture closure starts chains."""
import json
import os
from pathlib import Path


def pytest_fixture_setup(fixturedef, request):
    if fixturedef.argname.startswith('ledger_chains') or fixturedef.argname in ('peer_root', 'live_f', 'live_e'):
        raise RuntimeError('Review selection missed a prohibited live/build fixture: ' + fixturedef.argname)


def pytest_collection_modifyitems(config, items):
    selected, excluded = [], []
    reasons = {}
    for item in items:
        names = item.fixturenames
        params = getattr(getattr(item, 'callspec', None), 'params', {})
        dynamic = params.get('fixture_name', '')
        reason = None
        if any(n.startswith('ledger_chains') or n in ('peer_root', 'live_f', 'live_e') for n in names):
            reason = 'live chain or peer build in fixture closure'
        elif isinstance(dynamic, str) and dynamic.startswith(('world', 'ledger')):
            reason = 'dynamic live fixture requested through fixture_name'
        elif item.originalname == 'test_zz_every_catalog_case_was_executed_exactly_once':
            reason = 'catalog completeness requires the excluded live catalog cases'
        if reason:
            excluded.append(item)
            reasons[item.nodeid] = reason
        else:
            selected.append(item)
    output = Path(os.environ['RIS_REVIEW_DESELECTION'])
    assert not output.exists(), 'refuse to overwrite review selection'
    output.write_text(json.dumps(dict(selected=[i.nodeid for i in selected],
                                     excludedLiveFixture=[i.nodeid for i in excluded],
                                     exclusionReasons=reasons), indent=2) + '\n')
    items[:] = selected
    config.hook.pytest_deselected(items=excluded)
