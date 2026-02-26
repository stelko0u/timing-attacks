from __future__ import annotations

import hmac

from .timing import sleep_us


def naive_tag_compare(expected: bytes, provided: bytes, *, byte_delay_us: int) -> None:
    n = min(len(expected), len(provided))
    for i in range(n):
        if expected[i] != provided[i]:
            return
        sleep_us(byte_delay_us)
    if len(expected) != len(provided):
        return


def constant_time_compare(expected: bytes, provided: bytes) -> None:
    hmac.compare_digest(expected, provided)
