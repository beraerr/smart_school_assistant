"""studentVle günlük activity_type özeti. Kesim günü uygulanmaz."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_science.oulad import PROCESSED_OULAD_DIR, RAW_OULAD_DIR
from data_science.oulad.load import iter_typed_csv, load_table

STUDENT_VLE_NAME = "studentVle.csv"
DAILY_NAME = "student_vle_daily.parquet"
DEFAULT_CHUNKSIZE = 1_000_000

GROUP_COLUMNS = (
    "code_module",
    "code_presentation",
    "id_student",
    "date",
    "activity_type",
)

STUDENT_VLE_DTYPES = {
    "code_module": "string",
    "code_presentation": "string",
    "id_student": "int64",
    "id_site": "int64",
    "date": "Int64",
    "sum_click": "Int64",
}


def activity_lookup(vle: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in ("id_site", "activity_type") if column not in vle.columns]
    if missing:
        raise ValueError(f"eksik sutunlar: {missing}")
    lookup = vle.loc[:, ["id_site", "activity_type"]].copy()
    if lookup["id_site"].isna().any() or lookup["id_site"].duplicated().any():
        raise ValueError("id_site vle tablosunda tekil degil")
    return lookup


def _aggregate_part(chunk: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    merged = chunk.loc[:, list(STUDENT_VLE_DTYPES)].merge(lookup, on="id_site", how="left")
    return (
        merged.groupby(list(GROUP_COLUMNS), dropna=False, sort=False)
        .agg(sum_click=("sum_click", "sum"), n_rows=("id_student", "size"))
        .reset_index()
    )


def _combine_parts(parts: list[pd.DataFrame]) -> pd.DataFrame:
    columns = list(GROUP_COLUMNS) + ["sum_click", "n_rows"]
    if not parts:
        return pd.DataFrame(columns=columns)
    combined = pd.concat(parts, ignore_index=True)
    grouped = (
        combined.groupby(list(GROUP_COLUMNS), dropna=False, sort=False)
        .agg(sum_click=("sum_click", "sum"), n_rows=("n_rows", "sum"))
        .reset_index()
    )
    grouped["n_rows"] = grouped["n_rows"].astype("int64")
    return grouped.loc[:, columns]


def aggregate_student_vle(
    path: Path,
    vle: pd.DataFrame,
    chunksize: int = DEFAULT_CHUNKSIZE,
) -> pd.DataFrame:
    lookup = activity_lookup(vle)
    parts = [
        _aggregate_part(chunk, lookup)
        for chunk in iter_typed_csv(path, STUDENT_VLE_DTYPES, chunksize)
    ]
    return _combine_parts(parts)


def write_student_vle_daily(
    raw_dir: Path | None = None,
    chunksize: int = DEFAULT_CHUNKSIZE,
    dest: Path | None = None,
) -> Path:
    directory = RAW_OULAD_DIR if raw_dir is None else Path(raw_dir)
    vle = load_table("vle", directory)
    frame = aggregate_student_vle(directory / STUDENT_VLE_NAME, vle, chunksize=chunksize)
    out = PROCESSED_OULAD_DIR / DAILY_NAME if dest is None else Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, engine="pyarrow", index=False)
    return out


def main() -> None:
    path = write_student_vle_daily()
    frame = pd.read_parquet(path, engine="pyarrow")
    print(f"table=student_vle_daily rows={len(frame)} cols={frame.shape[1]}")


if __name__ == "__main__":
    main()
