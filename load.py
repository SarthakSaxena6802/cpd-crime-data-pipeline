"""Load step: upsert the transformed data into a SQL database (SQLite locally, Postgres in the cloud)."""
import os

import pandas as pd
from dotenv import load_dotenv
from prefect import task
from sqlalchemy import (
    BigInteger, Column, DateTime, Integer, MetaData, String, Table, Text,
    create_engine, func, select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

load_dotenv()

# Default = a local SQLite file for testing; set DATABASE_URL to use Postgres (Neon / Docker)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cpd_local.db")

metadata = MetaData()
incidents = Table(
    "cpd_incidents", metadata,
    Column("id", BigInteger, primary_key=True),
    Column("date_time", DateTime),
    Column("type", String),
    Column("subtype", String),
    Column("location", String),
    Column("description", Text),
    Column("last_updated", DateTime),
    Column("year", Integer),
    Column("month", Integer),
    Column("day", Integer),
    Column("hour", Integer),
    Column("minute", Integer),
    Column("second", Integer),
    Column("day_of_week", String),
)


@task(retries=2, retry_delay_seconds=10)
def load_data(df: pd.DataFrame) -> int:
    engine = create_engine(DATABASE_URL)
    print(f"Database: {engine.url.render_as_string(hide_password=True)}")
    metadata.create_all(engine)  # creates the table only if it doesn't exist yet

    # Convert pandas values to plain Python values (and missing values to None/NULL)
    records = df.astype(object).where(df.notna(), None).to_dict(orient="records")

    # Upsert: insert new ids, update existing ones, never delete
    insert = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
    stmt = insert(incidents)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={c.name: stmt.excluded[c.name] for c in incidents.columns if c.name != "id"},
    )

    with engine.begin() as conn:
        conn.execute(stmt, records)
        total = conn.execute(select(func.count()).select_from(incidents)).scalar_one()

    print(f"Upserted {len(records)} rows; table now has {total} rows")
    return total


if __name__ == "__main__":
    # Quick test: extract -> validate -> transform -> load
    from extract import extract_data
    from transform import transform_data
    from validate import validate_data

    load_data.fn(transform_data.fn(validate_data.fn(extract_data.fn())))
