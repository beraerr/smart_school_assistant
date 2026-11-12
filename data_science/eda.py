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

from data_science.absence import absence_grade_corr, absence_pass_table
from data_science.config import PASS_THRESHOLD_20, RANDOM_STATE, REPORTS_DIR
from data_science.features import add_derived_columns
from data_science.load import NUMERIC_COLUMNS, common_student_count, load_students

FIGURE_NAMES = (
    "g3_distribution_by_subject.png",
    "g1_g2_g3_scatter.png",
    "absences_vs_g3.png",
    "failures_vs_pass_rate.png",
    "studytime_vs_g3.png",
    "numeric_correlation_heatmap.png",
)


SUBJECTS = ("mat", "por")

# G3 histogram sınırları: her tamsayı notu (0..20) kendi kutusunda. Notebook 01 ve
# write_figures aynı sınırları kullanır; g3_histogram sayıları aynı sınırlardan çıkar.
G3_BINS = np.arange(-0.5, 21.5, 1)


def _passed(grades: pd.Series) -> pd.Series:
    return grades >= PASS_THRESHOLD_20


def g3_zero_by_subject(frame: pd.DataFrame) -> dict[str, int]:
    """Final notu 0 olan kayıt sayısı, ders bazında (mat, por).

    01_uci_eda notebook'undaki hücre mantığından taşınmıştır.
    """
    featured = add_derived_columns(frame)
    zero_rows = featured.loc[featured["g3_zero"] == 1]
    counts = zero_rows.groupby("subject").size().reindex(list(SUBJECTS), fill_value=0)
    return {str(subject): int(count) for subject, count in counts.items()}


def g3_histogram(frame: pd.DataFrame) -> list[dict]:
    """Ders başına 0..20 her not değeri için `{subject, g3, n}`; n sıfır olsa da satır vardır."""
    rows: list[dict] = []
    for subject in SUBJECTS:
        grades = frame.loc[frame["subject"] == subject, "G3"]
        counts, _ = np.histogram(grades, bins=G3_BINS)
        for grade, count in zip(range(len(G3_BINS) - 1), counts):
            rows.append({"subject": subject, "g3": grade, "n": int(count)})
    return rows


def numeric_correlation_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Sayısal sütunların Pearson korelasyon matrisi (NUMERIC_COLUMNS sırasıyla)."""
    return frame.loc[:, list(NUMERIC_COLUMNS)].corr()


def correlation_matrix_payload(frame: pd.DataFrame) -> dict:
    """`{columns: [...], values: [[...]]}`; sonlu olmayan hücre hata verir."""
    matrix = numeric_correlation_matrix(frame)
    values = [[float(cell) for cell in row] for row in matrix.to_numpy()]
    if not all(np.isfinite(cell) for row in values for cell in row):
        raise ValueError("korelasyon matrisinde sonlu olmayan değer var")
    return {"columns": [str(column) for column in matrix.columns], "values": values}


def grade_points(frame: pd.DataFrame) -> pd.DataFrame:
    """G1–G2–G3 saçılımının verisi: subject, G1, G2, G3 (başka sütun yok), satır sırası korunur."""
    return frame.loc[:, ["subject", "G1", "G2", "G3"]].reset_index(drop=True)


def grade_records(frame: pd.DataFrame) -> list[dict]:
    """`grade_points` satırları: `{subject, g1, g2, g3}`."""
    points = grade_points(frame)
    return [
        {"subject": str(subject), "g1": g1, "g2": g2, "g3": g3}
        for subject, g1, g2, g3 in zip(
            points["subject"], points["G1"].tolist(), points["G2"].tolist(), points["G3"].tolist()
        )
    ]


def build_absence_summary(frame: pd.DataFrame) -> dict:
    """Devamsızlık özeti. Hesap data_science.absence fonksiyonlarıyla yapılır."""
    featured = add_derived_columns(frame)
    kept = featured.loc[featured["g3_zero"] == 0]
    pearson_all, spearman_all = absence_grade_corr(featured)
    pearson_excl, spearman_excl = absence_grade_corr(kept)
    table_all = absence_pass_table(featured)
    table_excl = absence_pass_table(kept)
    buckets = [
        {
            "bucket": str(row_all["absence_bucket_label"]),
            "n_excl": int(row_excl["n_rows"]),
            "pass_all": float(row_all["pass_rate"]),
            "pass_excl": float(row_excl["pass_rate"]),
        }
        for (_, row_all), (_, row_excl) in zip(table_all.iterrows(), table_excl.iterrows())
    ]
    return {
        "pearson_all": pearson_all,
        "pearson_excl": pearson_excl,
        "spearman_all": spearman_all,
        "spearman_excl": spearman_excl,
        "buckets": buckets,
    }


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
        "absence": build_absence_summary(frame),
    }


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_figures(frame: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    colors = {"mat": "#1f77b4", "por": "#ff7f0e"}

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = G3_BINS
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

    matrix = numeric_correlation_matrix(frame)
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
