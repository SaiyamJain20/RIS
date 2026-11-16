"""TEST-ONLY scripted child that speaks hmbc-witness-rpc/v1 badly or well, for the process transport's edge cases (agent 2, F task 3, Step 2). Not a witness: it holds no key and signs nothing; the
"signature" it returns is a fixed 65-byte placeholder, because the transport judges only the envelope and the pool judges the signature.

    python stub_witness_child.py MODE [ARG]

Request lines on stdin are the real ones: {"schemaVersion", "id", "round", "kind", "message"}. MODE decides what happens for each request (the first one for the modes that say so):
  echo                 a well-formed signature reply echoing the request's message
  reflect              like echo, but `message` is the whole request object (so a test sees the exact request the transport wrote)
  hang                 reads every request and never replies
  noread               never reads stdin at all (its pipe fills up) and sleeps until killed
  exit2                writes one JSON error line to stderr and exits 2 before reading anything (a witness that fails to start)
  garbage              replies "this is not json"
  badutf8              replies two bytes that are not UTF-8
  badutf8-in-json      replies an otherwise valid reply with a raw 0xff byte inside a JSON string
  badschema            wrong schemaVersion
  extra-key            the envelope has one member too many
  missing-reply        the envelope has no `reply`
  reply-not-object     `reply` is the number 5
  id-null, id-bool, id-str, id-neg, id-future    the id is null, true, "0", -1, 10**6
  fixed-id N           always answers with id N whatever was asked (N may belong to another witness)
  duplicate            replies twice to every request
  partial              writes the first half of the reply, sleeps 0.4 s, writes the rest
  big-then-echo        the first reply is a 2 MiB line, later replies are normal
  noise                writes 300 KiB to stderr (first line FIRST-LINE) and then echoes
  die-after-first      echoes once and exits 0
  late N               sleeps N milliseconds before every echo
  dup-keys             the envelope repeats the `reply` member (strict JSON refuses a duplicate key)
  deep                 a reply whose message nests 100000 arrays (json.loads raises RecursionError on it)
  limit N              a reply line of exactly 1 MiB + N bytes (without the newline)
  close-stdin          closes its stdin (fd 0) at once and sleeps: alive, but every write to it fails with EPIPE
  json-number          replies the JSON number 5 (valid JSON, not an object)
  endless              writes 3 MiB without a newline and then sleeps
  spontaneous          writes one unprompted garbage line at startup, then behaves like echo
  slowreader           sleeps 0.5 s before it reads its first request, then echoes
"""
import json
import os
import sys
import time

SCHEMA = "hmbc-witness-rpc/v1"
SIG = "0x" + "11" * 65


def out(raw):
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def env(ident, reply, schema=SCHEMA):
    return json.dumps({"schemaVersion": schema, "id": ident, "reply": reply}, separators=(",", ":")).encode() + b"\n"


def echo(req):
    return {"type": "signature", "message": req["message"], "signature": SIG}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "echo"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == "exit2":
        sys.stderr.write('{"error":{"code":"MALFORMED","message":"stub startup refusal"}}\n')
        sys.stderr.flush()
        sys.exit(2)
    if mode == "noread":
        time.sleep(3600)
        return
    if mode == "close-stdin":
        os.close(0)
        time.sleep(3600)
        return
    if mode == "noise":
        sys.stderr.write("FIRST-LINE noise\n" + ("noise line that nobody reads and that must not block the child\n" * 5000))
        sys.stderr.flush()
    if mode == "spontaneous":
        out(b"unprompted line\n")
    if mode == "slowreader":
        time.sleep(0.5)
    served = 0
    for raw in sys.stdin.buffer:
        req = json.loads(raw)
        i = req["id"]
        served += 1
        if mode in ("echo", "noise", "spontaneous", "slowreader"):
            out(env(i, echo(req)))
        elif mode == "reflect":
            out(env(i, {"type": "signature", "message": req, "signature": SIG}))
        elif mode == "hang":
            continue
        elif mode == "garbage":
            out(b"this is not json\n")
        elif mode == "badutf8":
            out(b"\xff\xfe\n")
        elif mode == "badutf8-in-json":
            out(b'{"schemaVersion":"' + SCHEMA.encode() + b'","id":' + str(i).encode() + b',"reply":{"type":"signature","message":{"a":"\xff"},"signature":"' + SIG.encode() + b'"}}\n')
        elif mode == "badschema":
            out(env(i, echo(req), schema="hmbc-witness-rpc/v0"))
        elif mode == "extra-key":
            out(json.dumps({"schemaVersion": SCHEMA, "id": i, "reply": echo(req), "extra": 1}, separators=(",", ":")).encode() + b"\n")
        elif mode == "missing-reply":
            out(json.dumps({"schemaVersion": SCHEMA, "id": i}, separators=(",", ":")).encode() + b"\n")
        elif mode == "reply-not-object":
            out(env(i, 5))
        elif mode in ("id-null", "id-bool", "id-str", "id-neg", "id-future"):
            bad = {"id-null": None, "id-bool": True, "id-str": "0", "id-neg": -1, "id-future": 10 ** 6}[mode]
            out(env(bad, echo(req)))
        elif mode == "fixed-id":
            out(env(int(arg), echo(req)))
        elif mode == "duplicate":
            out(env(i, echo(req)) * 2)
        elif mode == "partial":
            line = env(i, echo(req))
            out(line[: len(line) // 2])
            time.sleep(0.4)
            out(line[len(line) // 2:])
        elif mode == "big-then-echo":
            if served == 1:
                out(env(i, {"type": "signature", "message": {"pad": "x" * (2 << 20)}, "signature": SIG}))
            else:
                out(env(i, echo(req)))
        elif mode == "die-after-first":
            out(env(i, echo(req)))
            sys.exit(0)
        elif mode == "json-number":
            out(b"5\n")
        elif mode == "endless":
            out(b"x" * (3 << 20))
            time.sleep(3600)
        elif mode == "dup-keys":
            inner = json.dumps(echo(req), separators=(",", ":"))
            out(('{"schemaVersion":"%s","id":%d,"reply":%s,"reply":%s}\n' % (SCHEMA, i, inner, inner)).encode())
        elif mode == "deep":
            out(('{"schemaVersion":"%s","id":%d,"reply":{"type":"signature","message":{"a":%s%s},"signature":"%s"}}\n' % (SCHEMA, i, "[" * 100000, "]" * 100000, SIG)).encode())
        elif mode == "limit":
            base = len(env(i, {"type": "signature", "message": {"pad": ""}, "signature": SIG})) - 1
            line = env(i, {"type": "signature", "message": {"pad": "x" * ((1 << 20) + int(arg) - base)}, "signature": SIG})
            assert len(line) - 1 == (1 << 20) + int(arg)
            out(line)
        elif mode == "late":
            time.sleep(int(arg) / 1000)
            out(env(i, echo(req)))
        else:
            raise SystemExit("unknown mode " + mode)


if __name__ == "__main__":
    main()
