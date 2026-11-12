"""Hafta 8 yolları ve eşikler. Model hiperparametresi yok."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

# Depo köküne göre data_science/data/raw, data_science/data/processed, data_science/reports.
RAW_DIR = PACKAGE_DIR / "data" / "raw"
PROCESSED_DIR = PACKAGE_DIR / "data" / "processed"
REPORTS_DIR = PACKAGE_DIR / "reports"

RANDOM_STATE = 42

# 20'lik UCI notu. Backend PASS_GRADE=50 (100'lük) ile aynı kural: G3 * 5 >= 50.
PASS_THRESHOLD_20 = 10
