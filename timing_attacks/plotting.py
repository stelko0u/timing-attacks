from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


def plot_pvalues(decisions: list[dict], *, alpha: float, out_path: Path) -> None:
    xs = [d["byte_index"] for d in decisions]
    ys = [d.get("p_value") for d in decisions]
    ys2 = [y if y is not None else 1.0 for y in ys]

    fig = plt.figure(figsize=(9, 3.2), dpi=160)
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, ys2, marker="o", linewidth=1.5)
    ax.axhline(alpha, color="#b91c1c", linewidth=1.2, linestyle="--")
    ax.set_title("Statistical decision per byte (p-value)")
    ax.set_xlabel("byte index")
    ax.set_ylabel("p-value")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_means(decisions: list[dict], *, out_path: Path) -> None:
    xs = [d["byte_index"] for d in decisions]
    best = [d.get("best_mean_ns") for d in decisions]
    second = [d.get("second_mean_ns") for d in decisions]
    best2 = [v if v is not None else 0.0 for v in best]
    second2 = [v if v is not None else 0.0 for v in second]

    fig = plt.figure(figsize=(9, 3.2), dpi=160)
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, best2, label="best mean", linewidth=1.6)
    ax.plot(xs, second2, label="2nd mean", linewidth=1.2)
    ax.set_title("Mean time gap (best vs second)")
    ax.set_xlabel("byte index")
    ax.set_ylabel("mean elapsed (ns)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_overhead(rows: list[dict], *, out_path: Path) -> None:
    xs = [float(r["fixed_delay_ms"]) for r in rows]
    ys = [float(r["mean_ms"]) for r in rows]

    fig = plt.figure(figsize=(9, 3.2), dpi=160)
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, ys, marker="o", linewidth=1.6)
    ax.set_title("Overhead vs fixed delay")
    ax.set_xlabel("fixed_delay_ms")
    ax.set_ylabel("mean verify time (ms)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
