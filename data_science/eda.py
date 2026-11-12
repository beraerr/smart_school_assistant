"""Ham birleşik tablo için grafikler ve eda_summary.json. Model yok."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

# Betik penceresiz çalışır. Notebook çekirdeği (ipykernel) kendi backend'ini korur.
if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from data_science.config import PASS_THRESHOLD_20, RANDOM_STATE, REPORTS_DIR
from data_science.load import NUMERIC_COLUMNS, common_student_count, load_students

FIGURE_NAMES = (
    "g3_distribution_by_subject.png",
    "g1_g2_g3_scatter.png",
    "absences_vs_g3.png",
    "failures_vs_pass_rate.png",
    "studytime_vs_g3.png",
    "numeric_correlation_heatmap.png",
)


def _passed(grades: pd.Series) -> pd.Series:
    return grades >= PASS_THRESHOLD_20


def build_summary(frame: pd.DataFrame) -> dict:
    correlations = {
        column: float(frame[column].corr(frame["G3"]))
        for column in NUMERIC_COLUMNS
        if column != "G3"
    }
    correlations = {name: value for name, value in correlations.items() if pd.notna(value)}
    ranking = sorted(correlations, key=lambda name: (-abs(correlations[name]), name))
    top = [
        {
            "feature": name,
            "correlation": correlations[name],
            "abs_correlation": abs(correlations[name]),
        }
        for name in ranking[:10]
    ]
    row_counts = {
        "total": int(len(frame)),
        "mat": int((frame["subject"] == "mat").sum()),
        "por": int((frame["subject"] == "por").sum()),
    }
    pass_rate = {
        subject: float(_passed(part["G3"]).mean())
        for subject, part in frame.groupby("subject", sort=True)
    }
    return {
        "row_counts": row_counts,
        "pass_rate_by_subject": {str(subject): rate for subject, rate in pass_rate.items()},
        "g3_zero_count": int((frame["G3"] == 0).sum()),
        "top_abs_correlation_with_g3": top,
        "g1_g3_correlation": correlations["G1"],
        "g2_g3_correlation": correlations["G2"],
        "common_student_count": int(common_student_count(frame)),
        "missing_value_count": int(frame.isna().sum().sum()),
    }


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_figures(frame: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    colors = {"mat": "#1f77b4", "por": "#ff7f0e"}

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.arange(-0.5, 21.5, 1)
    for subject in ("mat", "por"):
        values = frame.loc[frame["subject"] == subject, "G3"]
        ax.hist(
            values,
            bins=bins,
            alpha=0.55,
            label=subject,
            color=colors[subject],
            edgecolor="white",
            linewidth=0.4,
        )
    ax.set_xlabel("G3")
    ax.set_ylabel("satır sayısı")
    ax.set_title("Ders bazında G3 dağılımı")
    ax.legend()
    _save(fig, figures_dir / "g3_distribution_by_subject.png")

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.4))
    for ax, (left, right) in zip(axes, (("G1", "G2"), ("G1", "G3"), ("G2", "G3"))):
        for subject in ("mat", "por"):
            part = frame.loc[frame["subject"] == subject]
            ax.scatter(
                part[left],
                part[right],
                s=12,
                alpha=0.4,
                c=colors[subject],
                label=subject,
                linewidths=0,
            )
        correlation = float(frame[left].corr(frame[right]))
        ax.set_xlabel(left)
        ax.set_ylabel(right, labelpad=8)
        ax.set_title(f"{left} vs {right} (r={correlation:.3f})")
    axes[0].legend()
    fig.tight_layout(w_pad=2.8)
    _save(fig, figures_dir / "g1_g2_g3_scatter.png")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for subject in ("mat", "por"):
        part = frame.loc[frame["subject"] == subject]
        ax.scatter(
            part["absences"],
            part["G3"],
            s=16,
            alpha=0.45,
            c=colors[subject],
            label=subject,
            linewidths=0,
        )
    ax.set_xlabel("absences")
    ax.set_ylabel("G3")
    ax.set_title("Devamsızlık ve G3")
    ax.legend()
    _save(fig, figures_dir / "absences_vs_g3.png")

    passed = _passed(frame["G3"]).astype(float)
    rates = passed.groupby(frame["failures"], sort=True).mean()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    positions = rates.index.to_numpy()
    heights = rates.to_numpy()
    ax.bar(positions, heights, color="#4c78a8", width=0.7)
    ax.set_xticks(list(positions))
    ax.set_xticklabels([str(int(value)) for value in positions])
    ax.set_xlabel("failures")
    ax.set_ylabel("geçme oranı (G3 >= 10)")
    ax.set_ylim(0, 1.05)
    ax.set_title("Geçmiş başarısızlık ve geçme oranı")
    for position, height in zip(positions, heights):
        ax.text(position, height + 0.02, f"{height:.2f}", ha="center", va="bottom", fontsize=8)
    _save(fig, figures_dir / "failures_vs_pass_rate.png")

    levels = sorted(int(value) for value in frame["studytime"].unique())
    boxes = [frame.loc[frame["studytime"] == level, "G3"].to_numpy() for level in levels]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot(boxes, positions=levels, widths=0.6)
    ax.set_xticks(levels)
    ax.set_xlabel("studytime")
    ax.set_ylabel("G3")
    ax.set_title("Haftalık çalışma süresi ve G3")
    _save(fig, figures_dir / "studytime_vs_g3.png")

    matrix = frame.loc[:, list(NUMERIC_COLUMNS)].corr()
    labels = list(matrix.columns)
    values = matrix.to_numpy()
    fig, ax = plt.subplots(figsize=(11, 9))
    image = ax.imshow(values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90)
    ax.set_yticklabels(labels)
    ax.set_title("Sayısal özellik korelasyon ısı haritası")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    _save(fig, figures_dir / "numeric_correlation_heatmap.png")


def write_summary(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    np.random.seed(RANDOM_STATE)
    frame = load_students()
    figures_dir = REPORTS_DIR / "figures"
    write_figures(frame, figures_dir)
    summary = build_summary(frame)
    write_summary(summary, REPORTS_DIR / "eda_summary.json")


if __name__ == "__main__":
    main()
