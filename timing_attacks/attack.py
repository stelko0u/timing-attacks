from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .config import AttackConfig, VerifyConfig
from .crypto import hmac_sha256_tag
from .stats import Decision, decide
from .verify import verify_measurement


@dataclass
class AttackProgress:
    byte_index: int
    decided_byte: int | None
    p_value: float | None
    repetitions_per_guess: int


@dataclass
class AttackResult:
    recovered_tag_hex: str
    true_tag_hex: str
    correct_bytes: int
    total_bytes: int
    attack_accuracy: float
    samples_needed: int
    alpha: float
    decisions: list[dict]


def _fmt_hex(b: bytes) -> str:
    return b.hex()


def _measure_candidate_times(
    *,
    key: bytes,
    message: bytes,
    verify_cfg: VerifyConfig,
    guess_prefix: bytes,
    guess_byte: int,
    rest_len: int,
    r: int,
) -> np.ndarray:
    guess = bytearray(guess_prefix)
    guess.append(int(guess_byte))
    if rest_len > 0:
        guess.extend(b"\x00" * rest_len)
    times = np.empty((r,), dtype=np.float64)
    for k in range(r):
        dt_ns, _ = verify_measurement(key=key, message=message, provided_tag=bytes(guess), cfg=verify_cfg)
        times[k] = float(dt_ns)
    return times


def run_attack(
    *,
    key: bytes,
    message: bytes,
    verify_cfg: VerifyConfig,
    attack_cfg: AttackConfig,
    on_progress=None,
) -> AttackResult:
    true_tag = hmac_sha256_tag(key, message)
    tag_len = min(attack_cfg.tag_len, len(true_tag))
    recovered = bytearray()
    decisions: list[dict] = []
    samples_total = 0

    for i in range(tag_len):
        # Stage 1: coarse sampling for all 256 candidates.
        r0 = max(2, int(attack_cfg.coarse_repetitions))
        means = np.empty((256,), dtype=np.float64)
        coarse_samples: list[np.ndarray] = []
        for b in range(256):
            s = _measure_candidate_times(
                key=key,
                message=message,
                verify_cfg=verify_cfg,
                guess_prefix=bytes(recovered),
                guess_byte=b,
                rest_len=(tag_len - (i + 1)),
                r=r0,
            )
            coarse_samples.append(s)
            means[b] = float(s.mean())
        samples_total += 256 * r0

        top_k = int(max(2, min(256, attack_cfg.top_k)))
        candidates = list(np.argsort(means)[-top_k:][::-1])

        # Stage 2: refine top-k until we can decide.
        per_candidate = {int(b): coarse_samples[int(b)] for b in candidates}
        r = max(r0, int(attack_cfg.repetitions_per_guess))

        best_decision: Decision | None = None
        while True:
            # Ensure each candidate has r samples.
            for b in list(per_candidate.keys()):
                s = per_candidate[b]
                if int(s.size) < r:
                    extra = _measure_candidate_times(
                        key=key,
                        message=message,
                        verify_cfg=verify_cfg,
                        guess_prefix=bytes(recovered),
                        guess_byte=b,
                        rest_len=(tag_len - (i + 1)),
                        r=(r - int(s.size)),
                    )
                    per_candidate[b] = np.concatenate([s, extra])
                    samples_total += int(extra.size)

            ordered = sorted(per_candidate.items(), key=lambda kv: float(kv[1].mean()), reverse=True)
            best_b, best_s = ordered[0]
            second_b, second_s = ordered[1]
            best_decision = decide([best_s, second_s], method=attack_cfg.decision)

            if on_progress is not None:
                on_progress(
                    AttackProgress(
                        byte_index=i,
                        decided_byte=int(best_b),
                        p_value=float(best_decision.p_value),
                        repetitions_per_guess=r,
                    )
                )

            if float(best_decision.p_value) < float(attack_cfg.alpha):
                recovered.append(int(best_b))
                decisions.append(
                    {
                        "byte_index": i,
                        "picked": int(best_b),
                        "p_value": float(best_decision.p_value),
                        "best_mean_ns": float(best_s.mean()),
                        "second_mean_ns": float(second_s.mean()),
                        "final_repetitions_per_guess": int(r),
                        "candidates": candidates,
                    }
                )
                break

            if r >= int(attack_cfg.max_repetitions_per_guess):
                recovered.append(int(best_b))
                decisions.append(
                    {
                        "byte_index": i,
                        "picked": int(best_b),
                        "p_value": float(best_decision.p_value),
                        "best_mean_ns": float(best_s.mean()),
                        "second_mean_ns": float(second_s.mean()),
                        "final_repetitions_per_guess": int(r),
                        "candidates": candidates,
                    }
                )
                break

            r = min(int(attack_cfg.max_repetitions_per_guess), int(r * 2))

    correct = sum(1 for i in range(tag_len) if recovered[i] == true_tag[i])
    acc = (correct / tag_len) * 100.0 if tag_len else 0.0

    return AttackResult(
        recovered_tag_hex=_fmt_hex(bytes(recovered)),
        true_tag_hex=_fmt_hex(true_tag[:tag_len]),
        correct_bytes=int(correct),
        total_bytes=int(tag_len),
        attack_accuracy=float(acc),
        samples_needed=int(samples_total),
        alpha=float(attack_cfg.alpha),
        decisions=decisions,
    )


def result_to_dict(r: AttackResult) -> dict:
    return asdict(r)
