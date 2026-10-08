"""Real loopback controls for inter-profile startup and occupied-port refusal."""
import errno
import socket

import pytest

from evaluation.e1 import _available


def test_next_profile_accepts_time_wait_after_previous_listener_closed():
    # The server actively closes a real connection, leaving its local port in
    # TIME_WAIT. This is the lifecycle boundary that broke the live E1 run.
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        listener.listen(1)
        with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
            accepted, _ = listener.accept()
            accepted.close()
            assert client.recv(1) == b''
    with socket.socket() as ordinary_probe:
        with pytest.raises(OSError) as error:
            ordinary_probe.bind(('127.0.0.1', port))
        assert error.value.errno == errno.EADDRINUSE
    _available({'pbc': port})
    # The next actual server can listen immediately without adopting a process.
    with socket.socket() as replacement:
        replacement.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        replacement.bind(('127.0.0.1', port))
        replacement.listen(1)


@pytest.mark.parametrize('host', ['127.0.0.1', '0.0.0.0'])
def test_port_probe_refuses_live_listener_and_leaves_it_serving(host):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, 0))
        port = listener.getsockname()[1]
        listener.listen(1)
        with pytest.raises(OSError) as error:
            _available({'pbc': port})
        assert error.value.errno == errno.EADDRINUSE
        with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
            connection, _ = listener.accept()
            with connection:
                connection.sendall(b'still owned by the original listener')
                assert client.recv(128) == b'still owned by the original listener'
