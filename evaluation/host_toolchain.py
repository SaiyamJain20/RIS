"""Resolve frozen tool pins to binaries on the executing host (A1-0061 D-2).

The frozen `evaluation/toolchain.json` (source of `interfaces/v1/toolchain.json`)
is never edited. A tool may only move to a different path when its bytes still
hash to the frozen value. A frozen path that exists must match its hash; it
never falls through to an override. The single declared exception is a local
ProVerif build of the frozen version from the frozen source archive; its
different binary hash is returned and recorded, not hidden.
"""
import copy
import json
from pathlib import Path

from evaluation.manifests import sha256

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT/'evaluation/toolchain.json'
OVERRIDE = ROOT/'evaluation/host-tools.json'
NAMES = ('forge', 'anvil', 'cast', 'solc', 'proverif')


def _frozen_pins(frozen):
    pins = {name: dict(path=row['path'], sha256=row['sha256']) for name, row in frozen['foundry']['binaryPaths'].items()}
    pins['solc'] = dict(path=frozen['solc']['path'], sha256=frozen['solc']['sha256'])
    pv = frozen['proverif']
    pins['proverif'] = dict(path=pv['path'], sha256=pv['binarySha256'])
    if set(pins) != set(NAMES):
        raise ValueError('Frozen toolchain tool set changed')
    return pins


def _hash(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('Tool paths must be absolute')
    return sha256(path) if path.is_file() else None


def resolve_all(frozen, override):
    """Return {tool: {path, sha256, frozenPath, frozenSha256, resolution, ...}}."""
    pins = _frozen_pins(frozen)
    entries = override.get('tools', {})
    if not isinstance(entries, dict) or not set(entries) <= set(NAMES):
        raise ValueError('Host override names an unknown tool')
    resolved = {}
    for name, pin in pins.items():
        actual = _hash(pin['path'])
        if actual is not None:
            if actual != pin['sha256']:
                raise ValueError('Frozen tool path exists with a different hash: '+name)
            resolved[name] = dict(path=pin['path'], sha256=actual, frozenPath=pin['path'],
                                  frozenSha256=pin['sha256'], resolution='frozen-path')
            continue
        entry = entries.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
            raise ValueError('Frozen tool is absent and has no host override: '+name)
        if set(entry) - {'path', 'declaredLocalBuild'}:
            raise ValueError('Unexpected host override fields: '+name)
        actual = _hash(entry['path'])
        if actual is None:
            raise ValueError('Host override tool is absent: '+name)
        row = dict(path=entry['path'], sha256=actual, frozenPath=pin['path'], frozenSha256=pin['sha256'])
        declared = entry.get('declaredLocalBuild')
        if declared is None:
            if actual != pin['sha256']:
                raise ValueError('Host override hash differs from the frozen pin: '+name)
            row['resolution'] = 'host-override'
        else:
            pv = frozen['proverif']
            if (name != 'proverif' or not isinstance(declared, dict) or declared.get('sha256') != actual
                    or declared.get('version') != pv['version'] or declared.get('sourceSha256') != pv['sourceSha256']):
                raise ValueError('Only a declared ProVerif build of the frozen version/source may differ: '+name)
            row.update(resolution='declared-local-build', declaredLocalBuild=copy.deepcopy(declared))
        resolved[name] = row
    return resolved


def resolved():
    frozen = json.loads(FROZEN.read_text())
    override = json.loads(OVERRIDE.read_text()) if OVERRIDE.is_file() else dict(tools={})
    return resolve_all(frozen, override)


def resolve(name):
    if name not in NAMES:
        raise ValueError('Unknown tool')
    return resolved()[name]
