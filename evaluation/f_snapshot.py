"""Offline inputs for the paper-derived HMBC reconstruction; no execution authority.

Source extraction never executes package code. Historical Git objects are copied
into a separate shallow bare store with no alternate/object-store dependency.
Runtime inventories cover explicit selected roots only, not transitive closure.
These APIs assume exclusive ownership of the new destination while preparing it;
they are not a filesystem sandbox against a concurrent hostile writer.
"""

import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile

from evaluation.manifests import canonical_hash, sha256

_SHA = re.compile(r'[0-9a-f]{64}\Z')
_COMMIT = re.compile(r'[0-9a-f]{40}\Z')


def _relative(value):
    path = PurePosixPath(value)
    if (not isinstance(value, str) or not value or path.is_absolute()
            or any(part in {'', '.', '..'} for part in value.split('/'))
            or any(part.startswith(('-', ':')) for part in path.parts)
            or '\\' in value or '\0' in value or '.git' in path.parts):
        raise ValueError('Noncanonical or unsafe source path')
    return value


def _git(tool, *args, cwd=None):
    if sha256(tool['path']) != tool['sha256']:
        raise ValueError('Git tool pin mismatch')
    # Do not inherit GIT_DIR, alternates, command-scope config, hooks or user
    # aliases. No remotes are configured and fetch accepts an absolute local path.
    env = {'PATH': str(Path(tool['path']).parent) + ':/usr/bin:/bin',
           'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_ATTR_NOSYSTEM': '1',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_SYSTEM': '/dev/null'}
    output = subprocess.run([tool['path'], '-c', 'core.hooksPath=/dev/null',
        '-c', 'maintenance.auto=false', '-c', 'gc.auto=0', *map(str, args)],
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, timeout=60).stdout
    if sha256(tool['path']) != tool['sha256']:
        raise ValueError('Git tool pin changed')
    return output


def _validate_plan(plan, expected):
    if not _SHA.fullmatch(expected) or canonical_hash(plan) != expected:
        raise ValueError('Snapshot plan hash mismatch')
    if plan.get('schemaVersion') != 'hmbc-f-snapshot-plan/v1':
        raise ValueError('Unknown snapshot plan')
    tool = plan['git']
    if not Path(tool['path']).is_absolute() or not _SHA.fullmatch(tool['sha256']):
        raise ValueError('Absolute Git executable and SHA-256 required')
    owned = []
    if not plan['sources'] or not plan['sourceFiles']:
        raise ValueError('Nonempty sources and exact file pins required')
    for source in plan['sources']:
        if not _COMMIT.fullmatch(source['commit']) or not _SHA.fullmatch(source['archiveSha256']):
            raise ValueError('Full commit and archive hash required')
        if not source['paths']:
            raise ValueError('Nonempty source paths required')
        for raw in source['paths']:
            name = _relative(raw)
            if any(name == old or name.startswith(old + '/') or old.startswith(name + '/') for old in owned):
                raise ValueError('Source ownership overlap')
            owned.append(name)
    for name, digest in plan['sourceFiles'].items():
        _relative(name)
        if not _SHA.fullmatch(digest) or not any(name == base or name.startswith(base + '/') for base in owned):
            raise ValueError('Source hash or ownership mismatch')
    if any(not _COMMIT.fullmatch(commit) for commit in plan['requiredGitCommits']):
        raise ValueError('Full required Git commit IDs required')


def _file(path):
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError(f'Expected regular input: {path}')
    return {'sha256': sha256(path), 'mode': stat.S_IMODE(mode)}


def _source_inventory(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Snapshot inventory root must be a regular directory')
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Source input must be regular, not symlink')
        if path.is_dir():
            continue
        files[path.relative_to(root).as_posix()] = _file(path)
    return files


def _extract(archive, root, paths):
    with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
        for member in handle:
            name = _relative(member.name.rstrip('/'))
            # Git includes ancestor directories for selected nested paths.
            allowed = any(name == base or name.startswith(base + '/') or
                          (member.isdir() and base.startswith(name + '/')) for base in paths)
            if not allowed or not (member.isdir() or member.isfile()):
                raise ValueError('Archive input must be selected regular files/directories')
            target = root / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                stream = handle.extractfile(member)
                while block := stream.read(1024 * 1024):
                    output.write(block)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def _commit_record(tool, repository, commit):
    # Repository is always an absolute directory (original worktree or bare copy).
    actual = _git(tool, '-C', repository, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if actual != commit:
        raise ValueError('Required object is not the exact commit')
    archive = _git(tool, '-C', repository, 'archive', commit)
    return {'commit': commit,
            'tree': _git(tool, '-C', repository, 'rev-parse', commit + '^{tree}').decode().strip(),
            'archiveSha256': hashlib.sha256(archive).hexdigest()}


def materialize_snapshot(repository, destination, plan, *, expected_plan_sha256):
    """Prepare a new pinned source workspace; a PREPARED result authorizes no run.

    Invalid plan structure/hash fails before writes. Acquisition errors leave a
    BLOCKED manifest and partial artifacts for diagnosis; callers must never use
    those partial artifacts as a prepared snapshot. Existing destinations survive.
    """
    plan = copy.deepcopy(plan)
    _validate_plan(plan, expected_plan_sha256)
    repository = Path(repository).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.resolve().is_relative_to(repository):
        raise ValueError('Disposable snapshot must be outside source repository')
    destination.mkdir(parents=True, exist_ok=False)
    workspace = destination / 'workspace'
    workspace.mkdir()
    objects = destination / 'objects.git'
    result = {'schemaVersion': 'hmbc-f-snapshot/v1', 'status': 'BLOCKED',
        'executionAuthorized': False, 'gateF': 'NOT_RUN', 'blockers': [],
        'planSha256': expected_plan_sha256, 'plan': plan,
        'workspace': str(workspace), 'gitDirectory': str(objects),
        'sourceFiles': {}, 'gitCommits': [], 'gitStoreFiles': {}}
    tool = plan['git']
    try:
        for source in plan['sources']:
            archive = _git(tool, '-C', repository, 'archive', source['commit'], '--', *source['paths'])
            if hashlib.sha256(archive).hexdigest() != source['archiveSha256']:
                raise ValueError('Source archive pin mismatch')
            _extract(archive, workspace, source['paths'])
        result['sourceFiles'] = _source_inventory(workspace)
        if {key: row['sha256'] for key, row in result['sourceFiles'].items()} != plan['sourceFiles']:
            raise ValueError('Extracted source file inventory mismatch')
        commits = sorted(set(plan['requiredGitCommits'] + [s['commit'] for s in plan['sources']]))
        _git(tool, 'init', '--bare', '--template=', objects)
        for index, commit in enumerate(commits):
            record = _commit_record(tool, repository, commit)
            _git(tool, '-C', objects, 'fetch', '--no-tags', '--no-write-fetch-head',
                 '--depth=1', '--', repository, f'{commit}:refs/hmbc/input-{index}')
            if _commit_record(tool, objects, commit) != record:
                raise ValueError('Copied Git archive differs from original')
            result['gitCommits'].append(record)
        if (objects / 'objects/info/alternates').exists():
            raise ValueError('Copied object store must not depend on alternates')
        result['gitStoreFiles'] = _source_inventory(objects)
        # Re-check sources after object acquisition, before publishing readiness.
        if _source_inventory(workspace) != result['sourceFiles']:
            raise ValueError('Snapshot source changed during acquisition')
        result['status'] = 'PREPARED'
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as error:
        result['blockers'].append(str(error))
    (destination / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def verify_snapshot(manifest, *, expected_manifest_sha256):
    """Recheck pinned bytes/modes and historical archives without the origin repo."""
    if not _SHA.fullmatch(expected_manifest_sha256) or canonical_hash(manifest) != expected_manifest_sha256:
        raise ValueError('Snapshot manifest pin mismatch')
    if manifest.get('schemaVersion') != 'hmbc-f-snapshot/v1' or manifest['status'] != 'PREPARED':
        raise ValueError('Snapshot was not prepared')
    _validate_plan(manifest['plan'], manifest['planSha256'])
    if manifest['blockers'] or manifest['executionAuthorized'] is not False or manifest['gateF'] != 'NOT_RUN':
        raise ValueError('Snapshot preparation cannot authorize execution')
    if _source_inventory(Path(manifest['workspace'])) != manifest['sourceFiles']:
        raise ValueError('Snapshot source inventory mismatch')
    objects = Path(manifest['gitDirectory'])
    if _source_inventory(objects) != manifest['gitStoreFiles']:
        raise ValueError('Snapshot Git store inventory mismatch')
    for record in manifest['gitCommits']:
        if _commit_record(manifest['plan']['git'], objects, record['commit']) != record:
            raise ValueError('Historical Git object pin mismatch')
    return True


def _tool(path):
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Tool requires an absolute file path')
    return {'path': str(path), 'resolvedPath': str(path.resolve(strict=True)),
            'symlink': os.readlink(path) if path.is_symlink() else None,
            **_file(path.resolve(strict=True))}


def inventory_runtime(*, tools, roots):
    """Observe exact selected trees/tools; never infer undiscovered dependencies."""
    entries = {}
    names = []
    for raw in roots:
        root = Path(raw)
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise ValueError('Runtime root must be an absolute regular directory')
        names.append(str(root))
        for path in [root, *sorted(root.rglob('*'))]:
            name = str(path)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                if not path.is_file():
                    raise ValueError('Runtime symlinks must target regular files')
                entries[name] = {'target': os.readlink(path), 'resolvedPath': str(path.resolve(strict=True)),
                                 **_file(path.resolve(strict=True))}
            elif stat.S_ISDIR(mode):
                entries[name] = {'directory': True, 'mode': stat.S_IMODE(mode)}
            else:
                entries[name] = _file(path)
    if not names:
        raise ValueError('At least one explicit runtime root required')
    return {'schemaVersion': 'hmbc-f-runtime-inventory/v1', 'closureEstablished': False,
            'roots': sorted(set(names)), 'entries': dict(sorted(entries.items())),
            'tools': {name: _tool(path) for name, path in sorted(tools.items())}}


def verify_runtime_inventory(inventory, *, expected_inventory_sha256):
    if not _SHA.fullmatch(expected_inventory_sha256) or canonical_hash(inventory) != expected_inventory_sha256:
        raise ValueError('Runtime inventory pin mismatch')
    fresh = inventory_runtime(tools={key: row['path'] for key, row in inventory['tools'].items()},
                              roots=inventory['roots'])
    if fresh != inventory:
        raise ValueError('Runtime inventory drift')
    return True
