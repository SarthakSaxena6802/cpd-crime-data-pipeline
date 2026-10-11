"""Transform step: remove duplicates and add date/time parts for analysis."""
import pandas as pd
from prefect import task


@task
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    # Keep only the most recently updated copy of each incident id
    before = len(df)
    df = df.sort_values("last_updated", na_position="first").drop_duplicates(subset="id", keep="last")
    print(f"Removed {before - len(df)} duplicate ids")

    # Split date_time into parts so the dashboard can group by hour, month, etc.
    dt = df["date_time"].dt
    df = df.assign(
        year=dt.year,
        month=dt.month,
        day=dt.day,
        hour=dt.hour,
        minute=dt.minute,
        second=dt.second,
        day_of_week=dt.day_name(),
    )

    df = df.sort_values("date_time").reset_index(drop=True)
    print(f"Transform done: {len(df)} rows, {len(df.columns)} columns")
    return df


if __name__ == "__main__":
    # Quick test: extract -> validate -> transform
    from extract import extract_data
    from validate import validate_data

    df = transform_data.fn(validate_data.fn(extract_data.fn()))
    print(df[["id", "date_time", "year", "month", "day", "hour", "day_of_week", "type"]].head(3).to_string())
    print(df["type"].value_counts())
