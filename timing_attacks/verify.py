from __future__ import annotations

from dataclasses import asdict

from .compare import constant_time_compare, naive_tag_compare
from .config import VerifyConfig
from .crypto import hmac_sha256_tag
from .noise import apply_noise
from .timing import now_ns, sleep_us


def verify_measurement(*, key: bytes, message: bytes, provided_tag: bytes, cfg: VerifyConfig) -> tuple[int, dict]:
    expected = hmac_sha256_tag(key, message)

    t0 = now_ns()
    if cfg.mode == "naive":
        naive_tag_compare(expected, provided_tag, byte_delay_us=cfg.byte_delay_us)
    else:
        constant_time_compare(expected, provided_tag)

    if cfg.fixed_delay_ms and cfg.fixed_delay_ms > 0:
        sleep_us(int(cfg.fixed_delay_ms * 1000))

    apply_noise(cfg.noise.profile, jitter_us=cfg.noise.jitter_us)
    t1 = now_ns()

    meta = {
        "verify_config": asdict(cfg),
        "expected_len": len(expected),
        "provided_len": len(provided_tag),
    }
    return (t1 - t0), meta
