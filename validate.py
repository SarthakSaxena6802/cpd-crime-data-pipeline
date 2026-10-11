"""Validate step: check the extracted data has the expected columns and sensible values."""
import pandas as pd
from prefect import task

EXPECTED_COLUMNS = ["date_time", "id", "type", "subtype", "location", "description", "last_updated"]
REQUIRED_NOT_NULL = ["date_time", "id", "type", "location"]
MAX_BAD_ROW_FRACTION = 0.05  # fail the run if more than 5% of rows are unusable


@task
def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("No data returned from the API")

    # 1. Schema: every expected column must exist; extra columns are ignored
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns from API: {missing}")
    extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if extra:
        print(f"Ignoring extra columns: {extra}")
    df = df[EXPECTED_COLUMNS].copy()

    # 2. Types: values that can't be converted become empty (NaN/NaT) instead of crashing
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["date_time"] = pd.to_datetime(df["date_time"], format="ISO8601", errors="coerce")
    df["last_updated"] = pd.to_datetime(df["last_updated"], format="ISO8601", errors="coerce")

    # 3. Required fields: drop rows missing any of them, but fail if too many are bad
    bad = df[REQUIRED_NOT_NULL].isna().any(axis=1)
    n_bad = int(bad.sum())
    if n_bad > len(df) * MAX_BAD_ROW_FRACTION:
        raise ValueError(f"{n_bad} of {len(df)} rows have missing/invalid required fields")
    if n_bad:
        print(f"Dropping {n_bad} rows with missing/invalid required fields")
    df = df[~bad].copy()
    df["id"] = df["id"].astype("int64")

    print(f"Validation passed: {len(df)} rows")
    return df


if __name__ == "__main__":
    # Quick test: extract, then validate
    from extract import extract_data

    df = validate_data.fn(extract_data.fn())
    print(df.dtypes)
    print(f"Date range: {df['date_time'].min()} to {df['date_time'].max()}")
