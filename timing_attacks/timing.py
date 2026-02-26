from __future__ import annotations

import time


def now_ns() -> int:
    return time.perf_counter_ns()


def busywait_us(us: int) -> None:
    if us <= 0:
        return
    target = time.perf_counter_ns() + (us * 1_000)
    while time.perf_counter_ns() < target:
        pass


def sleep_us(us: int) -> None:
    if us <= 0:
        return
    if us < 2_000:
        busywait_us(us)
        return
    time.sleep(us / 1_000_000)
