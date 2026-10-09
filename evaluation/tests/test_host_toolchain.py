"""Host tool-path override (A1-0061 D-2): paths may move, frozen hashes may not.

Synthetic binaries only; no service is started. The frozen toolchain file is
never edited. Only ProVerif may be a declared local build, and only when the
frozen version and source hash match.
"""
import copy
import hashlib
import importlib
import json

import pytest


def module():
    assert importlib.util.find_spec('evaluation.host_toolchain') is not None, 'host tool resolver missing'
    return importlib.import_module('evaluation.host_toolchain')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data=b'tool'):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); path.chmod(0o700)
    return path


@pytest.fixture
def frozen(tmp_path):
    tools = {name: write(tmp_path/'frozen'/name, name.encode()) for name in ('forge', 'anvil', 'cast', 'solc', 'proverif')}
    doc = dict(foundry=dict(binaryPaths={n: dict(path=str(tools[n]), sha256=digest(n.encode())) for n in ('forge', 'anvil', 'cast')}),
               solc=dict(version='0.8.37', path=str(tools['solc']), sha256=digest(b'solc')),
               proverif=dict(version='2.05', path=str(tools['proverif']), binarySha256=digest(b'proverif'),
                             sourceSha256='4871'*16))
    return doc, tools


def test_frozen_paths_are_used_unchanged_when_present(frozen):
    doc, tools = frozen
    resolved = module().resolve_all(doc, dict(tools={}))
    assert {n: r['path'] for n, r in resolved.items()} == {n: str(p) for n, p in tools.items()}
    assert all(r['resolution'] == 'frozen-path' for r in resolved.values())


def test_missing_frozen_path_uses_override_with_identical_frozen_hash(frozen, tmp_path):
    doc, tools = frozen
    tools['cast'].unlink(); moved = write(tmp_path/'host/cast', b'cast')
    resolved = module().resolve_all(doc, dict(tools=dict(cast=dict(path=str(moved)))))
    assert resolved['cast'] == dict(path=str(moved), sha256=digest(b'cast'), frozenPath=str(tools['cast']),
                                    frozenSha256=digest(b'cast'), resolution='host-override')


@pytest.mark.parametrize('case', ['override-hash', 'frozen-path-hash', 'absent', 'unknown-tool', 'relative'])
def test_any_hash_or_identity_mismatch_refuses(frozen, tmp_path, case):
    doc, tools = frozen; override = dict(tools={})
    if case == 'override-hash':
        tools['anvil'].unlink(); override['tools']['anvil'] = dict(path=str(write(tmp_path/'host/anvil', b'other')))
    if case == 'frozen-path-hash':
        # A present frozen path never falls through to an override.
        write(tools['forge'], b'tampered'); override['tools']['forge'] = dict(path=str(write(tmp_path/'host/forge', b'forge')))
    if case == 'absent':
        tools['solc'].unlink()
    if case == 'unknown-tool':
        override['tools']['geth'] = dict(path=str(write(tmp_path/'host/geth', b'geth')))
    if case == 'relative':
        tools['cast'].unlink(); write(tmp_path/'host/cast', b'cast'); override['tools']['cast'] = dict(path='host/cast')
    with pytest.raises(ValueError):
        module().resolve_all(doc, override)


def test_proverif_declared_local_build_is_recorded_not_hidden(frozen, tmp_path):
    doc, tools = frozen
    tools['proverif'].unlink(); local = write(tmp_path/'host/proverif', b'local build')
    declared = dict(sha256=digest(b'local build'), version='2.05', sourceSha256='4871'*16, compiler='OCaml 4.14.2')
    resolved = module().resolve_all(doc, dict(tools=dict(proverif=dict(path=str(local), declaredLocalBuild=declared))))
    row = resolved['proverif']
    assert row['resolution'] == 'declared-local-build' and row['sha256'] == digest(b'local build')
    assert row['frozenSha256'] == digest(b'proverif') and row['sha256'] != row['frozenSha256']
    assert row['declaredLocalBuild'] == declared


@pytest.mark.parametrize('change', ['binary', 'version', 'source', 'non-proverif'])
def test_local_build_exception_is_narrow(frozen, tmp_path, change):
    doc, tools = frozen
    tools['proverif'].unlink(); local = write(tmp_path/'host/proverif', b'local build')
    declared = dict(sha256=digest(b'local build'), version='2.05', sourceSha256='4871'*16, compiler='OCaml 4.14.2')
    override = dict(tools=dict(proverif=dict(path=str(local), declaredLocalBuild=declared)))
    if change == 'binary': write(local, b'changed')
    if change == 'version': declared['version'] = '2.04'
    if change == 'source': declared['sourceSha256'] = '00'*32
    if change == 'non-proverif':
        tools['forge'].unlink(); other = write(tmp_path/'host/forge', b'other forge')
        override['tools']['forge'] = dict(path=str(other), declaredLocalBuild=dict(declared, sha256=digest(b'other forge')))
    with pytest.raises(ValueError):
        module().resolve_all(doc, override)


def test_repository_override_resolves_every_tool_on_this_host():
    m = module(); resolved = m.resolved()
    frozen = json.loads((m.ROOT/'evaluation/toolchain.json').read_text())
    for name in ('forge', 'anvil', 'cast'):
        assert resolved[name]['sha256'] == frozen['foundry']['binaryPaths'][name]['sha256']
    assert resolved['solc']['sha256'] == frozen['solc']['sha256']
    pv = resolved['proverif']
    assert pv['sha256'] == frozen['proverif']['binarySha256'] or (
        pv['resolution'] == 'declared-local-build' and pv['declaredLocalBuild']['sourceSha256'] == frozen['proverif']['sourceSha256'])


def test_frozen_toolchain_copy_stays_byte_identical():
    m = module()
    assert (m.ROOT/'evaluation/toolchain.json').read_bytes() == (m.ROOT/'interfaces/v1/toolchain.json').read_bytes()
