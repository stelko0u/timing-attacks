from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseConfig:
    profile: str = "none"  # none | jitter | cpu
    jitter_us: int = 0
    cpu_threads: int = 0


@dataclass(frozen=True)
class VerifyConfig:
    mode: str = "naive"  # naive | constant
    byte_delay_us: int = 800  # amplification for naive compare
    fixed_delay_ms: float = 0.0  # hardening: add fixed delay (both modes)
    noise: NoiseConfig = NoiseConfig()


@dataclass(frozen=True)
class AttackConfig:
    tag_len: int = 32
    repetitions_per_guess: int = 30
    alpha: float = 0.01
    max_repetitions_per_guess: int = 5000
    decision: str = "ttest"  # ttest | ks
    top_k: int = 16
    coarse_repetitions: int = 10
