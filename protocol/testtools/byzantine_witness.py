"""TEST-ONLY real-PROCESS Byzantine witness (H1 as a supervised child; agent 2, F phase; gap G1). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys. Not imported by any production module; not an adapter
operation; not in exports/adapter.json.

    python -m testtools.byzantine_witness --behavior SPEC <the production witness's own arguments>
    SPEC  withhold | garbage | repeat:N (2..8) | equivocate | impersonate:J (0..3) | poison:FIELD

It speaks `hmbc-witness-rpc/v1` on stdin/stdout exactly like `hmbc_protocol.witness_main` (it reuses that module's parser, request shape, error replies and serve loop), so the real supervisor, the real pool and
the real ledger can be run against the same adversary as `testtools.byzantine`'s virtual endpoints (rows FL-4, FL-5, FL-7, F-12, F-17, F-22):
  withhold        reads every request and never answers (alive but silent: not a SIGSTOP, so the pool sees a live process);
  garbage         answers every well-formed request with a reply of an unknown type;
  impersonate:J   signs the ASKED message with witness J's key: a valid signature that does not recover to the replying witness;
  poison:FIELD    signs a message that differs from the asked one in FIELD (a decimal +1, a hash or address last nibble +1; a field the message does not carry stays unchanged) with its OWN key and replies with it;
  repeat:N        the HONEST reply (the production service, store and view) written N times;
  equivocate      the HONEST reply, then a second signed value from the same key (the asked message with its most telling field changed).
The first four need only the deployment (strict JSON, a TEST-ONLY key derivation, and the label must name the witness at `--index`): they make NO RPC call and touch NO state, whatever `--abi-dir` and
`--state-dir` say. `repeat` and `equivocate` start the production service (the full production start-up, which creates the durable store). A start-up failure is ONE closed JSON line on stderr, exit 2, nothing
on stdout, no path or argument echoed. A malformed request line is answered MALFORMED, as the production witness does. Key custody is TEST-ONLY (keys derive from public labels); this adversary signs with
synthetic keys only. Not claimed: that any oracle accepts what it produces; anything about consensus, clocks or a real network.
"""
from __future__ import annotations

import json
import re
import sys

from eth_account import Account

from hmbc_protocol import adapter as _e
from hmbc_protocol import adapter_v2_main as am
from hmbc_protocol import keys
from hmbc_protocol import witness_main as wm
from testtools import byzantine as bz

FIELDS = ("sequence", "authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash", "expiresAt", "stateSequence", "result", "dbcBlockNumber", "nonce")
TYPE_OF = {"checkpoint": "StateCheckpoint", "decision": "AccessDecision", "receipt": "GrantReceipt", "governance": "GovernanceAction"}
EQUIVOCATE_FIELD = {"checkpoint": "sourceBlockNumber", "decision": "stateSequence", "receipt": "dbcBlockNumber", "governance": "nonce"}
_PLAIN = re.compile(r"withhold|garbage|equivocate")
_REPEAT = re.compile(r"repeat:([2-8])")
_IMPERSONATE = re.compile(r"impersonate:([0-3])")
_POISON = re.compile(r"poison:(" + "|".join(FIELDS) + ")")
_DEC = re.compile(r"0|[1-9][0-9]*")
_HEXN = re.compile(r"0x([0-9a-f]{40}|[0-9a-f]{64})")
_NIBBLES = "0123456789abcdef"

MSG_BEHAVIOR = "refusing: --behavior must be withhold, garbage, repeat:N (N 2..8), equivocate, impersonate:J (J 0..3) or poison:FIELD"
MSG_ARGS = "refusing: the witness arguments are malformed"
MSG_DEPLOYMENT = "refusing: the deployment is unusable or does not declare a TEST-ONLY key derivation and a witness set"
MSG_LABEL = "refusing: the key label does not name the witness at this index of the deployment's witness set"


def parse_behavior(text):
    """`withhold`, `garbage`, `equivocate`, `repeat:N`, `impersonate:J` or `poison:FIELD`, exactly; anything else is a ValueError. Returns the text unchanged."""
    if isinstance(text, str) and (_PLAIN.fullmatch(text) or _REPEAT.fullmatch(text) or _IMPERSONATE.fullmatch(text) or _POISON.fullmatch(text)):
        return text
    raise ValueError("malformed behaviour")


def mutate(value):
    """The poisoned value: a canonical decimal +1; a 0x hash or address with its last hex digit +1 (mod 16); anything else (a list, a non-canonical string) unchanged."""
    if isinstance(value, str) and _DEC.fullmatch(value):
        return str(int(value) + 1)
    if isinstance(value, str) and _HEXN.fullmatch(value):
        return value[:-1] + _NIBBLES[(int(value[-1], 16) + 1) % 16]
    return value


def _parse_request(line):
    """(ident, kind, message) for a well-formed request line, else (ident or None, None, None): the production witness's own conditions, so a malformed line is answered exactly as it answers it."""
    ident = None
    try:
        obj = _e.strict_loads(line)
    except _e.AdapterError:
        return None, None, None
    if isinstance(obj, dict) and wm._is_int(obj.get("id")) and obj["id"] >= 0:
        ident = obj["id"]
    if (not isinstance(obj, dict) or set(obj) != wm.REQUEST_FIELDS or obj["schemaVersion"] != wm.SCHEMA or ident is None or not wm._is_int(obj["round"]) or obj["round"] not in (1, 2)
            or not isinstance(obj["kind"], str) or obj["kind"] not in wm.KINDS or not isinstance(obj["message"], dict)):
        return ident, None, None
    return ident, obj["kind"], dict(obj["message"])


class _Sink:
    """The stdout the serve loop writes to: it drops, repeats or extends the lines the handler produced, according to the behaviour."""

    def __init__(self, out, behavior, key, deployment):
        self._out, self._behavior, self._key, self._deployment = out, behavior, key, deployment
        self.context = None                                                          # (ident, kind, message) of the request the NEXT written line answers

    def write(self, text):
        ctx, self.context = self.context, None
        name, _, arg = self._behavior.partition(":")
        if name == "withhold":
            return len(text)
        if name == "repeat":
            for _ in range(int(arg)):
                self._out.write(text)
            return len(text)
        self._out.write(text)
        if name == "equivocate" and ctx is not None and ctx[1] is not None:
            reply = json.loads(text).get("reply")
            if isinstance(reply, dict) and reply.get("type") == "signature":
                ident, kind, message = ctx
                alt = dict(message)
                alt[EQUIVOCATE_FIELD[kind]] = mutate(alt.get(EQUIVOCATE_FIELD[kind]))
                sig = bz.sign_message(self._key, TYPE_OF[kind], alt, self._deployment)
                self._out.write(json.dumps(wm._answer(ident, {"type": "signature", "message": alt, "signature": sig}), separators=(",", ":")) + "\n")
        return len(text)

    def flush(self):
        self._out.flush()


def _light_handler(behavior, key, impersonated_key, deployment):
    name, _, arg = behavior.partition(":")

    def handle(line, service):
        ident, kind, message = _parse_request(line)
        if kind is None:
            return wm._answer(ident, dict(wm.MALFORMED))
        typ = TYPE_OF[kind]
        if name == "garbage":
            return wm._answer(ident, {"type": "bogus"})
        if name == "impersonate":
            return wm._answer(ident, {"type": "signature", "message": message, "signature": bz.sign_message(impersonated_key, typ, message, deployment)})
        if name == "poison":
            poisoned = dict(message)
            if arg in poisoned:
                poisoned[arg] = mutate(poisoned[arg])
            return wm._answer(ident, {"type": "signature", "message": poisoned, "signature": bz.sign_message(key, typ, poisoned, deployment)})
        return wm._answer(ident, {})                                                 # withhold: the sink drops it

    return handle


def _refuse(stderr, code, message):
    stderr.write(json.dumps({"error": {"code": code, "message": message}}, separators=(",", ":")) + "\n")
    return 2


def _split(argv):
    """`--behavior SPEC` and the production witness's own arguments; a problem is a ValueError (argparse would print a usage text and exit)."""
    rest, behavior, i = [], None, 0
    argv = list(argv)
    while i < len(argv):
        if argv[i] == "--behavior":
            if behavior is not None or i + 1 >= len(argv):
                raise ValueError("--behavior")
            behavior = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    if behavior is None:
        raise ValueError("--behavior")
    return behavior, rest


def main(argv=None, stdin=None, stdout=None, stderr=None, service_factory=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    stdin, stdout, stderr = stdin or sys.stdin.buffer, stdout or sys.stdout, stderr or sys.stderr
    try:
        behavior, rest = _split(argv)
        behavior = parse_behavior(behavior)
    except ValueError:
        return _refuse(stderr, "MALFORMED", MSG_BEHAVIOR)
    parser = wm._parser()

    def _error(message):                                                             # never print a usage text or exit: the caller turns it into the one closed refusal
        raise ValueError("malformed arguments")
    parser.error = _error
    try:
        args = parser.parse_args(rest)
    except ValueError:
        return _refuse(stderr, "MALFORMED", MSG_ARGS)
    try:
        manifest = am._manifest(args.deployment)
        fixture = manifest["fixture"]
        derivation, witnesses, labels = fixture["keyDerivation"], list(fixture["witnessSet"]["witnesses"]), fixture["witnessSet"].get("keyLabels")
        if not isinstance(derivation, str) or not derivation.startswith("TEST-ONLY") or len(witnesses) != 4:
            raise ValueError
    except (am.Refusal, KeyError, TypeError, ValueError, OSError):
        return _refuse(stderr, "MALFORMED", MSG_DEPLOYMENT)
    index = int(args.index)
    key = keys.synthetic_private_key(args.key_label)
    if witnesses[index] != Account.from_key(key).address.lower():
        return _refuse(stderr, "UNKNOWN_AUTHORITY", MSG_LABEL)
    name, _, arg = behavior.partition(":")
    impersonated = None
    if name == "impersonate":
        label = labels[int(arg)] if isinstance(labels, list) and len(labels) == 4 and all(isinstance(x, str) for x in labels) else f"witness-{int(arg) + 1}"
        impersonated = keys.synthetic_private_key(label)
    service = None
    if name in ("repeat", "equivocate"):
        try:
            service = (service_factory or wm.build_service)(args)                    # the full production start-up (RPC, D50, the durable store)
        except am.Refusal as e:
            return _refuse(stderr, e.code, e.message)
        except Exception:  # noqa: BLE001 - a start-up defect nobody anticipated is still ONE closed refusal
            return _refuse(stderr, "ADAPTER_UNAVAILABLE", "internal startup failure")
    sink = _Sink(stdout, behavior, key, manifest)
    original = wm.handle_line
    if name in ("withhold", "garbage", "impersonate", "poison"):
        light = _light_handler(behavior, key, impersonated, manifest)
        wm.handle_line = lambda line, svc: (setattr(sink, "context", _parse_request(line)), light(line, svc))[1]
    else:
        wm.handle_line = lambda line, svc: (setattr(sink, "context", _parse_request(line)), original(line, svc))[1]
    try:
        return wm.serve(stdin, sink, service)
    finally:
        wm.handle_line = original


if __name__ == "__main__":
    sys.exit(main())
