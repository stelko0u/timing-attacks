from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Decision:
    best_index: int
    second_index: int
    p_value: float
    best_mean: float
    second_mean: float


def _try_scipy():
    try:
        from scipy import stats as st  # type: ignore

        return st
    except Exception:
        return None


def ttest_pvalue(a: np.ndarray, b: np.ndarray) -> float:
    st = _try_scipy()
    if st is not None:
        res = st.ttest_ind(a, b, equal_var=False, alternative="greater")
        return float(res.pvalue)

    ma, mb = float(a.mean()), float(b.mean())
    va, vb = float(a.var(ddof=1)), float(b.var(ddof=1))
    na, nb = int(a.size), int(b.size)
    denom = math.sqrt((va / na) + (vb / nb))
    if denom == 0.0:
        return 1.0
    t = (ma - mb) / denom
    return float(0.5 * math.erfc(t / math.sqrt(2)))


def ks_pvalue(a: np.ndarray, b: np.ndarray) -> float:
    st = _try_scipy()
    if st is None:
        return 1.0
    res = st.ks_2samp(a, b, alternative="greater")
    return float(res.pvalue)


def decide(samples_by_candidate: list[np.ndarray], *, method: str) -> Decision:
    means = [float(s.mean()) for s in samples_by_candidate]
    best = int(np.argmax(np.array(means)))
    second = int(np.argsort(np.array(means))[-2])
    a = samples_by_candidate[best]
    b = samples_by_candidate[second]
    if method == "ks":
        p = ks_pvalue(a, b)
    else:
        p = ttest_pvalue(a, b)
    return Decision(
        best_index=best,
        second_index=second,
        p_value=p,
        best_mean=means[best],
        second_mean=means[second],
    )
