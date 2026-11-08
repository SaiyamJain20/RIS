"""Join exporter framing and binding with exact captured INITIALIZED bytes.

Internal C-F1 evaluator API for the paper-derived reconstruction. The caller
pins the reviewed context, store paths and lock choreography and supplies a
snapshot captured under that lock. This checks no SQLite row projection: even
an export omitting every signing row may pass this marker join. Keep snapshots
private; fingerprints authenticate neither a store nor a producer.
"""
import hashlib
import json

from evaluation.binding_context_v2 import verify_export
from evaluation.witness_history_v2 import verify_signed_history


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid export snapshot: ' + message)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key')
        value[key] = item
    return value


def _constant(value):
    raise ValueError('nonfinite JSON constant')


def _object(raw, label):
    _require(type(raw) is bytes, label + ' must be bytes')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                           parse_constant=_constant)
    except (UnicodeError, ValueError) as exc:
        raise ValueError('Invalid export snapshot: ' + label + ' JSON') from exc
    _require(type(value) is dict, label + ' must be an object')
    return value


def verify_export_snapshot(stdout, *, stderr, exit_code, kind, snapshot,
                           manifest, observations, expected_owner,
                           compiled_max_admins=None):
    """Return marker/binding evidence and existing declared history results.

    Successful stdout is canonical ASCII JSON with exactly one LF; stderr must
    be empty bytes. Marker whitespace is unspecified, so compare its strict
    parsed object and separately fingerprint its exact captured bytes. No RPC,
    filesystem access, exporter invocation or mutation occurs in this function.
    """
    _require(type(exit_code) is int and exit_code == 0, 'export did not succeed')
    _require(type(stderr) is bytes and not stderr, 'export stderr is not empty bytes')
    _require(kind in ('BindingExport', 'WitnessEvidence'), 'export kind')
    export = _object(stdout, 'export')
    canonical = json.dumps(export, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'
    _require(stdout == canonical, 'export framing is not canonical one-line JSON')
    context = dict(manifest=manifest, observations=observations,
                   expected_owner=expected_owner, compiled_max_admins=compiled_max_admins)
    history = None
    if kind == 'BindingExport':
        verify_export(export, **context)
        binding = export['binding_v2']
    else:
        history = verify_signed_history(export, **context)
        binding = export['binding']['binding_v2']
    marker = _object(snapshot.marker, 'marker')
    _require(marker == dict(schema='2', owner=expected_owner, binding_v2=binding),
             'physical marker differs from verified binding/owner/schema')
    if kind == 'WitnessEvidence':
        _require(marker == export['marker'], 'physical and declared marker differ')
    return dict(owner=expected_owner, binding_v2=binding,
                stdoutSha256=hashlib.sha256(stdout).hexdigest(),
                markerSha256=snapshot.marker_sha256,
                logicalSha256=snapshot.logical_sha256, history=history)
