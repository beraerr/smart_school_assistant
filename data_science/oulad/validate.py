"""OULAD tablolarını ve günlük studentVle özetini düz metin olarak doğrular."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data_science.oulad import RAW_OULAD_DIR
from data_science.oulad.dataset import FEATURES_NAME
from data_science.oulad.load import STUDENT_KEY_COLUMNS, iter_typed_csv, load_tables
from data_science.oulad.vle import (
    DAILY_NAME,
    DEFAULT_CHUNKSIZE,
    PROCESSED_OULAD_DIR,
    STUDENT_VLE_DTYPES,
    STUDENT_VLE_NAME,
)


def _text(value: object) -> str:
    if pd.isna(value):
        return "NA"
    return str(value)


def _print_table(name: str, rows: int, cols: int, columns: list[str], missing: pd.Series) -> None:
    print(f"table={name} rows={rows} cols={cols}")
    for column in columns:
        print(f"missing {name} {column}={int(missing[column])}")


def _print_key(name: str, frame: pd.DataFrame) -> int:
    extra = int(frame.duplicated(list(STUDENT_KEY_COLUMNS)).sum())
    unique = 1 if extra == 0 else 0
    keys = ",".join(STUDENT_KEY_COLUMNS)
    print(f"key {name} {keys} unique={unique} extra={extra}")
    return extra


def _student_vle_facts(path: Path) -> tuple[int, list[str], pd.Series, int]:
    rows = 0
    clicks = 0
    columns: list[str] | None = None
    missing: pd.Series | None = None
    for chunk in iter_typed_csv(path, STUDENT_VLE_DTYPES, DEFAULT_CHUNKSIZE):
        rows += len(chunk)
        part = chunk["sum_click"].sum(skipna=True)
        if pd.notna(part):
            clicks += int(part)
        column_missing = chunk.isna().sum()
        if missing is None:
            columns = list(chunk.columns)
            missing = column_missing
        else:
            missing = missing.add(column_missing, fill_value=0)
    if columns is None or missing is None:
        raise RuntimeError(f"bos csv: {path}")
    return rows, columns, missing, clicks


def _sum_as_int(series: pd.Series) -> int:
    total = pd.to_numeric(series, errors="raise").sum(skipna=True)
    if pd.isna(total):
        return 0
    return int(total)


def report() -> None:
    tables = load_tables()
    for name, frame in tables.items():
        _print_table(name, len(frame), frame.shape[1], list(frame.columns), frame.isna().sum())

    student_vle_path = RAW_OULAD_DIR / STUDENT_VLE_NAME
    raw_rows, columns, missing, raw_clicks = _student_vle_facts(student_vle_path)
    _print_table("studentVle", raw_rows, len(columns), columns, missing)

    info_extra = _print_key("studentInfo", tables["studentInfo"])
    registration_extra = _print_key("studentRegistration", tables["studentRegistration"])

    courses = tables["courses"].loc[:, ["code_module", "code_presentation"]]
    courses = courses.drop_duplicates().sort_values(
        ["code_module", "code_presentation"], kind="mergesort"
    )
    for module, presentation in courses.itertuples(index=False):
        print(f"presentation code_module={module} code_presentation={presentation}")

    info = tables["studentInfo"]
    counts = (
        info.groupby(["code_module", "code_presentation", "final_result"], dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values(
            ["code_module", "code_presentation", "final_result"],
            kind="mergesort",
            na_position="last",
        )
    )
    for module, presentation, result, count in counts.itertuples(index=False):
        print(
            "final_result "
            f"code_module={_text(module)} "
            f"code_presentation={_text(presentation)} "
            f"result={_text(result)} n={int(count)}"
        )

    daily_path = PROCESSED_OULAD_DIR / DAILY_NAME
    if not daily_path.is_file():
        raise FileNotFoundError(daily_path)
    daily = pd.read_parquet(daily_path, engine="pyarrow")
    daily_rows = _sum_as_int(daily["n_rows"])
    daily_clicks = _sum_as_int(daily["sum_click"])
    print(f"studentVle rows={raw_rows}")
    print(f"student_vle_daily n_rows_sum={daily_rows}")
    print(f"studentVle sum_click={raw_clicks}")
    print(f"student_vle_daily sum_click={daily_clicks}")

    errors: list[str] = []
    if info_extra:
        errors.append(f"studentInfo: anahtar tekil degil, extra={info_extra}")
    if registration_extra:
        errors.append(
            f"studentRegistration: anahtar tekil degil, extra={registration_extra}"
        )
    if raw_rows != daily_rows:
        errors.append(f"studentVle rows: beklenen {raw_rows}, bulunan {daily_rows}")
    if raw_clicks != daily_clicks:
        errors.append(
            f"studentVle sum_click: beklenen {raw_clicks}, bulunan {daily_clicks}"
        )
    if errors:
        raise RuntimeError("dogrulama uyusmazligi:\n" + "\n".join(errors))


def _fmt_rate(series: pd.Series) -> str:
    count = len(series)
    if count == 0:
        return "NA"
    return f"{(float(series.sum()) / float(count)):.6f}"


def report_features(path: Path | None = None) -> None:
    source = PROCESSED_OULAD_DIR / FEATURES_NAME if path is None else Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    frame = pd.read_parquet(source, engine="pyarrow")
    print(f"features rows={len(frame)}")
    for split in ("history", "train", "test"):
        part = frame.loc[frame["split"].astype(str) == split]
        print(
            f"split={split} rows={len(part)} "
            f"at_risk_rate={_fmt_rate(part['at_risk'])} "
            f"has_history_rate={_fmt_rate(part['has_history'])}"
        )
    print(f"has_history_rate={_fmt_rate(frame['has_history'])}")
    print(f"cols={frame.shape[1]}")
    missing = frame.isna().sum()
    for column in frame.columns:
        print(f"missing features {column}={int(missing[column])}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="OULAD tablolarini dogrular")
    parser.add_argument("--features", action="store_true")
    args = parser.parse_args(argv)
    if args.features:
        report_features()
        return
    report()


if __name__ == "__main__":
    main()
