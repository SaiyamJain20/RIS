"""Six in-memory check removals; original module bytes remain untouched."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.tests.test_public_observations_v2 import setup
from evaluation import public_observations_v2 as original

source = (ROOT / 'evaluation/public_observations_v2.py').read_text()
changes = {
    'genesis': ("_require(block(chain, '0')['hash'] == observed['genesisHash'], chain + ' genesis changed')", 'pass'),
    'deployment': ("_require(block(chain, observed['deployBlock']['number']) == observed['deployBlock'], chain + ' deploy block changed')", 'pass'),
    'chain': ("_require(value == pin['chains'][chain]['chainId'], chain + ' chain ID mismatch')", 'pass'),
    'abi': ("_require(hashlib.sha256(contract.path.read_bytes()).hexdigest() == contract.abi_sha256, 'ABI changed')", 'pass'),
    'manifest': ("_require(manifest == pin, 'manifest changed')", 'pass'),
    'deadline': ('if time.monotonic() >= deadline:', 'if False:'),
}
results = []
for label, (old, new) in changes.items():
    assert source.count(old) == 1, label
    mutant = types.ModuleType('collector_mutant_' + label)
    exec(compile(source.replace(old, new), '<in-memory ' + label + ' removal>', 'exec'), mutant.__dict__)
    verdicts = []
    for module in (original, mutant):
        with tempfile.TemporaryDirectory(prefix='hmbc-collector-mutation-') as tmp:
            tmp = Path(tmp)
            case = setup()
            manifest, _, _, paths, rpcs = case
            if label in ('genesis', 'deployment'):
                tag = '0x0' if label == 'genesis' else hex(int(manifest['chains']['pbc']['deployBlock']))
                seen = [0]
                def corrupt(method, params, reply):
                    if method == 'eth_getBlockByNumber' and params[0] == tag:
                        seen[0] += 1
                        if seen[0] > 1:
                            return {**reply, 'hash': '0x' + '99' * 32}
                    return reply
                rpcs['pbc'].rewrite = corrupt
            elif label == 'chain':
                rpcs['pbc'].rewrite = lambda m, p, r: '0x1' if m == 'eth_chainId' and rpcs['dbc'].calls else r
            elif label == 'abi':
                local = tmp / 'PSC.json'
                local.write_bytes(paths['PSC'].read_bytes())
                paths['PSC'] = local
                def corrupt(m, p, r):
                    local.write_bytes(local.read_bytes() + b' ')
                    return r
                rpcs['dbc'].rewrite = corrupt
            elif label == 'manifest':
                def corrupt(m, p, r):
                    manifest['fixture']['relay']['address'] = '0x' + 'aa' * 20
                    return r
                rpcs['dbc'].rewrite = corrupt
            else:
                clock = [0.0]
                saved = module.time
                module.time = types.SimpleNamespace(monotonic=lambda: clock[0])
                rpcs['pbc'].rewrite = lambda m, p, r: (clock.__setitem__(0, 11.0), r)[1]
            try:
                module.collect(manifest, rpcs, paths, output=tmp / 'run', compiled_max_admins='8', timeout=10)
                verdicts.append('accepted')
            except (ValueError, TimeoutError):
                verdicts.append('refused')
            finally:
                if label == 'deadline':
                    module.time = saved
    assert verdicts == ['refused', 'accepted'], (label, verdicts)
    results.append({'removed': label, 'original': verdicts[0], 'mutant': verdicts[1]})
print(json.dumps({'classification': 'deliberate in-memory mutations; synthetic transport', 'controls': results}, indent=2))
