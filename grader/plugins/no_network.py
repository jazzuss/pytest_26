"""Blocks real network access while the grader runs your tests.

Tests should never depend on the network. If one tries, it fails with a
message that explains what to do instead.
"""

from __future__ import annotations

import socket

_MESSAGE = (
    "PyTest Quest blocked a REAL network call to {host!r}. Tests must not use the "
    "network: replace it with a mock. Tip: patch the name where it is USED, "
    "e.g. 'dungeon.raven.urlopen', not where it is defined ('urllib.request.urlopen')."
)


def _blocked_getaddrinfo(host, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
    # RuntimeError on purpose: urllib only turns OSErrors into URLError, so this
    # one travels straight up to the test instead of being retried.
    raise RuntimeError(_MESSAGE.format(host=host))


socket.getaddrinfo = _blocked_getaddrinfo
