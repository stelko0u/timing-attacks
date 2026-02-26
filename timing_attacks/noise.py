from __future__ import annotations

import random
import threading
from dataclasses import dataclass

from .timing import busywait_us, sleep_us


class _CpuLoad:
    def __init__(self, threads: int):
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        for i in range(max(0, threads)):
            t = threading.Thread(target=self._worker, name=f"cpu-load-{i}", daemon=True)
            self._threads.append(t)

    def start(self) -> None:
        for t in self._threads:
            t.start()

    def stop(self) -> None:
        self._stop.set()

    def _worker(self) -> None:
        while not self._stop.is_set():
            busywait_us(200)
            sleep_us(200)


@dataclass(frozen=True)
class NoiseRuntime:
    cpu: _CpuLoad | None = None


def start_noise(profile: str, *, cpu_threads: int) -> NoiseRuntime:
    if profile != "cpu" or cpu_threads <= 0:
        return NoiseRuntime(cpu=None)
    cpu = _CpuLoad(cpu_threads)
    cpu.start()
    return NoiseRuntime(cpu=cpu)


def stop_noise(rt: NoiseRuntime) -> None:
    if rt.cpu:
        rt.cpu.stop()


def apply_noise(profile: str, *, jitter_us: int) -> None:
    if profile == "jitter" and jitter_us > 0:
        j = random.randint(0, jitter_us)
        if j < 2_000:
            busywait_us(j)
        else:
            sleep_us(j)
