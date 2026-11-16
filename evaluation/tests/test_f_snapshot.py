"""Offline preparation controls; repositories, tools and runtimes are synthetic."""
import copy
import hashlib
import importlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

import pytest

from evaluation.manifests import canonical_hash, sha256


@pytest.fixture
def api():
    return importlib.import_module('evaluation.f_snapshot')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


@pytest.fixture
def fixture(tmp_path):
    repo = tmp_path / 'source'
    repo.mkdir()
    git(repo, 'init', '-q', '--template=')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')
    git(repo, 'config', 'user.name', 'Synthetic fixture')
    (repo / 'protocol').mkdir()
    (repo / 'protocol/probe.py').write_text('print("synthetic")\n')
    (repo / 'historical.txt').write_text('retained historical archive')
    git(repo, 'add', 'protocol/probe.py', 'historical.txt')
    git(repo, 'commit', '-qm', 'historical fixture')
    historical = git(repo, 'rev-parse', 'HEAD').decode().strip()
    (repo / 'historical.txt').unlink()
    (repo / 'protocol/probe.py').chmod(0o755)
    git(repo, 'add', 'historical.txt', 'protocol/probe.py')
    git(repo, 'commit', '-qm', 'selected fixture')
    commit = git(repo, 'rev-parse', 'HEAD').decode().strip()
    archive = git(repo, 'archive', commit, 'protocol')
    return repo, {'schemaVersion': 'hmbc-f-snapshot-plan/v1',
        'git': {'path': shutil.which('git'), 'sha256': sha256(shutil.which('git'))},
        'sources': [{'commit': commit, 'paths': ['protocol'],
                     'archiveSha256': hashlib.sha256(archive).hexdigest()}],
        'sourceFiles': {'protocol/probe.py': sha256(repo / 'protocol/probe.py')},
        'requiredGitCommits': [historical]}


def prepare(api, fixture, tmp_path, plan=None):
    repo, original = fixture
    plan = copy.deepcopy(original if plan is None else plan)
    return api.materialize_snapshot(repo, tmp_path / 'prepared', plan,
                                    expected_plan_sha256=canonical_hash(plan))


def test_exact_sources_executable_modes_and_independent_historical_archive(api, fixture, tmp_path):
    repo, plan = fixture
    result = prepare(api, fixture, tmp_path)
    assert result['status'] == 'PREPARED' and result['executionAuthorized'] is False
    assert result['gateF'] == 'NOT_RUN'
    workspace = Path(result['workspace'])
    assert sha256(workspace / 'protocol/probe.py') == plan['sourceFiles']['protocol/probe.py']
    assert os.access(workspace / 'protocol/probe.py', os.X_OK)
    assert not (workspace / '.git').exists()
    assert not (Path(result['gitDirectory']) / 'objects/info/alternates').exists()
    original_archive = git(repo, 'archive', plan['requiredGitCommits'][0])
    repo.rename(tmp_path / 'source-no-longer-at-original-path')
    env = {**os.environ, 'GIT_DIR': result['gitDirectory']}
    observed = subprocess.check_output(['git', 'archive', plan['requiredGitCommits'][0]], cwd=workspace, env=env)
    assert observed == original_archive
    assert api.verify_snapshot(result, expected_manifest_sha256=canonical_hash(result)) is True


@pytest.mark.parametrize('mutation', ['archive', 'file', 'missing-file', 'extra-file', 'commit', 'tool'])
def test_wrong_pins_fail_without_ready_snapshot(api, fixture, tmp_path, mutation):
    _, plan = fixture
    if mutation == 'archive': plan['sources'][0]['archiveSha256'] = '0' * 64
    if mutation == 'file': plan['sourceFiles']['protocol/probe.py'] = '0' * 64
    if mutation == 'missing-file': plan['sourceFiles'] = {'protocol/missing.py': '0' * 64}
    if mutation == 'extra-file': plan['sourceFiles']['protocol/extra.py'] = '0' * 64
    if mutation == 'commit': plan['requiredGitCommits'] = ['0' * 40]
    if mutation == 'tool': plan['git']['sha256'] = '0' * 64
    result = prepare(api, fixture, tmp_path)
    assert result['status'] == 'BLOCKED' and result['blockers']
    assert result['executionAuthorized'] is False


def test_plan_digest_refusal_precedes_destination_creation(api, fixture, tmp_path):
    repo, plan = fixture
    with pytest.raises(ValueError, match='plan'):
        api.materialize_snapshot(repo, tmp_path / 'prepared', plan, expected_plan_sha256='0' * 64)
    assert not (tmp_path / 'prepared').exists()


def test_destination_is_never_overwritten(api, fixture, tmp_path):
    (tmp_path / 'prepared').mkdir()
    keep = tmp_path / 'prepared/user.txt'
    keep.write_text('preserve')
    with pytest.raises(FileExistsError): prepare(api, fixture, tmp_path)
    assert keep.read_text() == 'preserve'


@pytest.mark.parametrize('path', ['../protocol', '/protocol', '.', 'protocol/../protocol', 'protocol//probe.py', ':magic'])
def test_unsafe_source_paths_rejected_before_creation(api, fixture, tmp_path, path):
    fixture[1]['sources'][0]['paths'] = [path]
    with pytest.raises(ValueError): prepare(api, fixture, tmp_path)
    assert not (tmp_path / 'prepared').exists()


def test_overlapping_source_ownership_rejected(api, fixture, tmp_path):
    fixture[1]['sources'].append(copy.deepcopy(fixture[1]['sources'][0]))
    with pytest.raises(ValueError, match='overlap'): prepare(api, fixture, tmp_path)


def test_git_symlink_archive_refused(api, fixture, tmp_path):
    repo, plan = fixture
    (repo / 'protocol/link').symlink_to('/outside')
    git(repo, 'add', 'protocol/link')
    git(repo, 'commit', '-qm', 'unsafe input fixture')
    plan['sources'][0]['commit'] = git(repo, 'rev-parse', 'HEAD').decode().strip()
    plan['sources'][0]['archiveSha256'] = hashlib.sha256(git(repo, 'archive', 'HEAD', 'protocol')).hexdigest()
    result = prepare(api, fixture, tmp_path)
    assert result['status'] == 'BLOCKED' and 'regular' in str(result['blockers'])


@pytest.mark.parametrize('mutation', ['bytes', 'extra', 'mode', 'manifest', 'git-object'])
def test_post_copy_drift_is_rejected(api, fixture, tmp_path, mutation):
    result = prepare(api, fixture, tmp_path)
    expected = canonical_hash(result)
    file = Path(result['workspace']) / 'protocol/probe.py'
    if mutation == 'bytes': file.write_text('changed')
    if mutation == 'extra': file.with_name('extra.py').write_text('changed')
    if mutation == 'mode': file.chmod(0o644)
    if mutation == 'manifest': result['sourceFiles']['protocol/probe.py'] = '0' * 64
    if mutation == 'git-object':
        objects = [p for p in (Path(result['gitDirectory']) / 'objects').rglob('*') if p.is_file()]
        assert objects, 'control must modify a real copied object'
        old_mode = objects[0].stat().st_mode & 0o777
        objects[0].chmod(0o600)
        objects[0].write_bytes(b'broken')
        objects[0].chmod(old_mode)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        api.verify_snapshot(result, expected_manifest_sha256=expected)


def test_inherited_git_redirect_and_global_configuration_do_not_select_inputs(api, fixture, tmp_path, monkeypatch):
    monkeypatch.setenv('GIT_DIR', '/nonexistent')
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', 'core.bare')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', 'true')
    assert prepare(api, fixture, tmp_path)['status'] == 'PREPARED'


def test_runtime_tree_and_lexical_tool_inventory_does_not_claim_closure(api, tmp_path):
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'library.so').write_bytes(b'synthetic library')
    tool = tmp_path / 'bin/tool'
    tool.parent.mkdir()
    tool.symlink_to(runtime / 'library.so')
    result = api.inventory_runtime(tools={'python': str(tool)}, roots=[runtime])
    assert result['tools']['python']['path'] == str(tool)
    assert result['tools']['python']['resolvedPath'] == str(runtime / 'library.so')
    assert result['closureEstablished'] is False
    assert api.verify_runtime_inventory(result, expected_inventory_sha256=canonical_hash(result)) is True


@pytest.mark.parametrize('mutation', ['file', 'extra', 'link', 'mode', 'directory', 'tool'])
def test_runtime_inventory_detects_drift(api, tmp_path, mutation):
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    library = runtime / 'library.so'
    library.write_text('fixture')
    link = runtime / 'link'
    link.symlink_to('library.so')
    tool = tmp_path / 'tool'
    tool.write_text('synthetic executable')
    result = api.inventory_runtime(tools={'python': str(tool)}, roots=[runtime])
    if mutation == 'file': library.write_text('changed')
    if mutation == 'extra': (runtime / 'new.so').write_text('new')
    if mutation == 'link': link.unlink(); link.symlink_to(tool)
    if mutation == 'mode': library.chmod(0o755)
    if mutation == 'directory': (runtime / 'new-directory').mkdir()
    if mutation == 'tool': tool.write_text('changed')
    with pytest.raises(ValueError, match='inventory'):
        api.verify_runtime_inventory(result, expected_inventory_sha256=canonical_hash(result))


def test_runtime_directory_symlinks_and_special_files_refused(api, tmp_path):
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'dir').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError): api.inventory_runtime(tools={}, roots=[runtime])
    (runtime / 'dir').unlink()
    os.mkfifo(runtime / 'fifo')
    with pytest.raises(ValueError): api.inventory_runtime(tools={}, roots=[runtime])


@pytest.mark.parametrize('kind', ['traversal', 'hardlink', 'symlink', 'fifo', 'unselected'])
def test_unsafe_archive_members_leave_snapshot_blocked(api, fixture, tmp_path, monkeypatch, kind):
    _, plan = fixture
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as handle:
        member = tarfile.TarInfo('../outside' if kind == 'traversal' else
                                 'outside' if kind == 'unselected' else 'protocol/unsafe')
        if kind == 'hardlink': member.type = tarfile.LNKTYPE; member.linkname = '/outside'
        if kind == 'symlink': member.type = tarfile.SYMTYPE; member.linkname = '/outside'
        if kind == 'fifo': member.type = tarfile.FIFOTYPE
        handle.addfile(member)
    payload = buffer.getvalue()
    plan['sources'][0]['archiveSha256'] = hashlib.sha256(payload).hexdigest()
    real_git = api._git
    def hostile_archive(tool, *args, **kwargs):
        return payload if 'archive' in args else real_git(tool, *args, **kwargs)
    monkeypatch.setattr(api, '_git', hostile_archive)
    result = prepare(api, fixture, tmp_path)
    assert result['status'] == 'BLOCKED'
    assert not (tmp_path / 'outside').exists()


def test_runtime_tool_symlink_spelling_is_pinned(api, tmp_path):
    root = tmp_path / 'runtime'
    root.mkdir()
    (root / 'library').write_text('fixture')
    tool = tmp_path / 'tool'
    tool.symlink_to(root / 'library')
    inventory = api.inventory_runtime(tools={'tool': str(tool)}, roots=[root])
    tool.unlink()
    tool.symlink_to('runtime/library')
    with pytest.raises(ValueError, match='inventory'):
        api.verify_runtime_inventory(inventory, expected_inventory_sha256=canonical_hash(inventory))


def test_snapshot_cannot_write_inside_pinned_source_repository(api, fixture):
    repo, plan = fixture
    with pytest.raises(ValueError):
        api.materialize_snapshot(repo, repo / 'prepared', plan, expected_plan_sha256=canonical_hash(plan))
    assert not (repo / 'prepared').exists()


@pytest.mark.parametrize('which', ['workspace', 'gitDirectory'])
def test_snapshot_root_symlink_is_not_a_closed_input(api, fixture, tmp_path, which):
    result = prepare(api, fixture, tmp_path)
    path = Path(result[which])
    moved = path.with_name(path.name + '-moved')
    path.rename(moved)
    path.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError):
        api.verify_snapshot(result, expected_manifest_sha256=canonical_hash(result))


def test_multiple_nonoverlapping_commits_preserve_nested_source_selection(api, fixture, tmp_path):
    repo, plan = fixture
    old = plan['requiredGitCommits'][0]
    archive = git(repo, 'archive', old, 'historical.txt')
    plan['sources'].append({'commit': old, 'paths': ['historical.txt'],
                            'archiveSha256': hashlib.sha256(archive).hexdigest()})
    plan['sources'][0]['paths'] = ['protocol/probe.py']
    plan['sources'][0]['archiveSha256'] = hashlib.sha256(git(repo, 'archive', plan['sources'][0]['commit'], 'protocol/probe.py')).hexdigest()
    plan['sourceFiles']['historical.txt'] = hashlib.sha256(b'retained historical archive').hexdigest()
    result = prepare(api, fixture, tmp_path)
    assert result['status'] == 'PREPARED'
    assert len(result['sourceFiles']) == 2
    assert api.verify_snapshot(result, expected_manifest_sha256=canonical_hash(result))


def test_git_store_has_no_remote_or_source_dependency(api, fixture, tmp_path):
    result = prepare(api, fixture, tmp_path)
    objects = Path(result['gitDirectory'])
    config = (objects / 'config').read_text()
    assert 'remote' not in config and str(fixture[0]) not in config
    assert not (objects / 'hooks').exists()
    assert not (objects / 'FETCH_HEAD').exists()
