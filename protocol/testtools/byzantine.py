"""TEST-ONLY Byzantine witness variants (H1) and the per-witness ledger-view override (H3) for the virtual transport. Not imported by any production module; not an adapter operation; no key is read from anywhere
(the caller passes the synthetic private keys).

Each variant is an ENDPOINT for `testtools.virtual_transport.VirtualTransport`: `send_delay(round_no)` and `deliver(round_no, message) -> [(reply_delay_ms, reply), ...]`.
  withhold(sign)                          never replies (a stopped witness);
  delayed(endpoint, ms)                   the inner endpoint's replies arrive `ms` later;
  Repeater(endpoint, n)                   every reply of the inner endpoint, n times;
  Equivocator(endpoint, key, name, deployment, alt)    the inner (honest) reply, then a second signature of `alt(message)` by the same key: two signed values from one witness;
  Impersonator(inner, key, name, deployment)           signs the asked message with `key`, which is NOT the replying witness's (another member's key, or a key outside the set): the signature verifies but
                                                       does not recover to the sender;
  Poisoner(inner, key, name, deployment, mutate)       signs `mutate(message)` with `key` and replies with that message instead of the asked one;
  Garbage()                               a reply of no known type.
`inner` of the two signing variants is the honest witness's sign function; it is accepted so a variant can be swapped in where a service endpoint was, and it is NOT called (a Byzantine witness does not need
the store).
H3: `view_override(service, view)` points one `WitnessService` at another ledger view for the duration of a block and restores it. It BREAKS the safe-ledger assumption by design and is for the conditional
rows only.
"""
from __future__ import annotations

import contextlib

from hmbc_protocol import eip712, messages


def sign_message(key, name, message, deployment):
    """A raw signature over the digest of `message` under the deployment's domain for `name`, with no store and no validation (what a Byzantine key holder can always do)."""
    return eip712.sign_digest(key, messages.digest_of(name, message, messages.domain_for(name, message, deployment)))


class _Endpoint:
    deliveries = ()

    def __init__(self, reply_delay=100):
        self.reply_delay = reply_delay
        self.deliveries = []

    def send_delay(self, round_no):
        return 0


def withhold(sign):
    from .virtual_transport import ServiceEndpoint
    return ServiceEndpoint(sign, muted=True)


class _Wrap(_Endpoint):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner

    def send_delay(self, round_no):
        return self.inner.send_delay(round_no)


class delayed(_Wrap):
    def __init__(self, inner, ms):
        super().__init__(inner)
        self.ms = ms

    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        return [(d + self.ms, r) for d, r in self.inner.deliver(round_no, message)]


class Repeater(_Wrap):
    def __init__(self, inner, n):
        super().__init__(inner)
        self.n = n

    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        return [(d, dict(r)) for d, r in self.inner.deliver(round_no, message)] * self.n


class Equivocator(_Wrap):
    def __init__(self, inner, key, name, deployment, alt):
        super().__init__(inner)
        self.key, self.name, self.deployment, self.alt = key, name, deployment, alt

    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        first = self.inner.deliver(round_no, message)
        other = self.alt(dict(message))
        return first + [(self.reply_delay + 1, {"type": "signature", "message": other, "signature": sign_message(self.key, self.name, other, self.deployment)})]


class Impersonator(_Endpoint):
    def __init__(self, inner, key, name, deployment):
        super().__init__()
        self.key, self.name, self.deployment = key, name, deployment

    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        return [(self.reply_delay, {"type": "signature", "message": dict(message), "signature": sign_message(self.key, self.name, message, self.deployment)})]


class Poisoner(_Endpoint):
    def __init__(self, inner, key, name, deployment, mutate):
        super().__init__()
        self.key, self.name, self.deployment, self.mutate = key, name, deployment, mutate

    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        other = self.mutate(dict(message))
        return [(self.reply_delay, {"type": "signature", "message": other, "signature": sign_message(self.key, self.name, other, self.deployment)})]


class Garbage(_Endpoint):
    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        return [(self.reply_delay, {"type": "no-such-reply"})]


@contextlib.contextmanager
def view_override(service, view):
    """H3 (TEST-ONLY): `service` reads `view` inside the block; the old view is restored on exit, even on an exception."""
    old = service._view
    service._view = view
    try:
        yield service
    finally:
        service._view = old
