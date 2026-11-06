"""TEST-ONLY virtual-time transport for the pool driver (the delivery-hold hook family of SIGNING-RULES section 8, schedules (a) and (b)). Not imported by any production module; not an adapter operation.

`VirtualTransport(endpoints)` plays witnesses against `witness_pool_driver.run_collection` on a deterministic virtual clock in milliseconds. Each endpoint offers
  send_delay(round_no) -> ms        how long the write to that witness is HELD before it is delivered (the delivery hold: a large value keeps the write undelivered until the pool cancels it)
  deliver(round_no, message) -> [(reply_delay_ms, reply), ...]   what the witness does when the write is delivered (its state changes at DELIVERY time, not at send time)
Ties: a delivery at time t happens before a reply at t; a reply at exactly the pool's timer deadline is NOT returned by `next_event` (the timer wins, as the collection's rule says), it is returned by the next call.
`cancel(w, r)` drops a write that has not been delivered yet. Nothing here reads a real clock.

`ServiceEndpoint` turns a real `WitnessService` method into such an endpoint: a signature becomes a `{"type": "signature", ...}` reply and a `WitnessRefusal` a `{"type": "error", ...}` reply with the recorded value.
"""
from __future__ import annotations

import heapq


class VirtualTransport:
    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.t = 0
        self._q = []
        self._n = 0
        self.sent, self.cancelled, self.delivered = [], [], []

    def now_ms(self):
        return self.t

    def _push(self, when, kind, payload):
        self._n += 1
        heapq.heappush(self._q, (when, 0 if kind == "deliver" else 1, self._n, kind, payload))

    def send(self, witness, round_no, message):
        self.sent.append((self.t, witness, round_no))
        self._push(self.t + self.endpoints[witness].send_delay(round_no), "deliver", (witness, round_no, message))

    def cancel(self, witness, round_no):
        self.cancelled.append((self.t, witness, round_no))
        self._q = [e for e in self._q if not (e[3] == "deliver" and e[4][0] == witness and e[4][1] == round_no)]
        heapq.heapify(self._q)

    def next_event(self, deadline_ms):
        while self._q:
            when, _, _, kind, payload = self._q[0]
            if kind == "reply" and when >= deadline_ms:
                break
            if kind == "deliver" and when > deadline_ms:
                break
            heapq.heappop(self._q)
            self.t = max(self.t, when)
            if kind == "deliver":
                w, r, message = payload
                self.delivered.append((self.t, w, r))
                for delay, reply in self.endpoints[w].deliver(r, message):
                    self._push(self.t + delay, "reply", (w, r, reply))
            else:
                w, r, reply = payload
                return self.t, w, r, reply
        self.t = max(self.t, deadline_ms)
        return None


class ServiceEndpoint:
    """A real witness (`sign` is e.g. `service.sign_checkpoint`) behind the virtual transport. `muted` witnesses never reply; delays are per round (an int, or {round: ms})."""

    def __init__(self, sign, *, deliver_delay=0, reply_delay=100, muted=False):
        self.sign, self.deliver_delay, self.reply_delay, self.muted = sign, deliver_delay, reply_delay, muted
        self.deliveries = []

    @staticmethod
    def _knob(v, r):
        return v[r] if isinstance(v, dict) else v

    def send_delay(self, round_no):
        return self._knob(self.deliver_delay, round_no)

    def deliver(self, round_no, message):
        self.deliveries.append((round_no, dict(message)))
        if self.muted:
            return []
        from hmbc_protocol.witness_service import WitnessRefusal
        try:
            sig = self.sign(message)
            reply = {"type": "signature", "message": dict(message), "signature": sig}
        except WitnessRefusal as e:
            reply = {"type": "error", "code": e.code, "reason": e.reason, "recorded": e.recorded}
        return [(self._knob(self.reply_delay, round_no), reply)]
