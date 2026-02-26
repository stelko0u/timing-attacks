from __future__ import annotations

from dataclasses import asdict

import numpy as np

from .config import AttackConfig, VerifyConfig
from .crypto import hmac_sha256_tag
from .verify import verify_measurement


def measure_overhead_ms(*, key: bytes, message: bytes, verify_cfg: VerifyConfig, n: int = 200) -> float:
    true_tag = hmac_sha256_tag(key, message)
    times = np.empty((n,), dtype=np.float64)
    for i in range(n):
        dt_ns, _ = verify_measurement(key=key, message=message, provided_tag=true_tag, cfg=verify_cfg)
        times[i] = float(dt_ns)
    return float(times.mean() / 1_000_000)


def overhead_sweep(*, key: bytes, message: bytes, verify_cfg: VerifyConfig, fixed_delays_ms: list[float], n: int = 120) -> list[dict]:
    rows: list[dict] = []
    for d in fixed_delays_ms:
        cfg2 = VerifyConfig(
            mode=verify_cfg.mode,
            byte_delay_us=verify_cfg.byte_delay_us,
            fixed_delay_ms=float(d),
            noise=verify_cfg.noise,
        )
        m = measure_overhead_ms(key=key, message=message, verify_cfg=cfg2, n=n)
        rows.append({"fixed_delay_ms": float(d), "mean_ms": float(m)})
    return rows


def serialize_configs(*, verify_cfg: VerifyConfig, attack_cfg: AttackConfig) -> dict:
    return {"verify": asdict(verify_cfg), "attack": asdict(attack_cfg)}
