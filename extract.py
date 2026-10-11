"""Extract step: download the Cambridge Police Daily Log from the Socrata API."""
import os

import pandas as pd
from dotenv import load_dotenv
from prefect import task
from sodapy import Socrata

load_dotenv()  # reads settings from a .env file if one exists

DOMAIN = "data.cambridgema.gov"
DATASET_ID = "3gki-wyrb"


@task(retries=3, retry_delay_seconds=10)
def extract_data() -> pd.DataFrame:
    app_token = os.getenv("SOCRATA_APP_TOKEN")  # optional; works without it, just slower limits
    with Socrata(DOMAIN, app_token, timeout=30) as client:
        # order=":id" gives a stable sort so pages don't overlap or skip rows
        records = list(client.get_all(DATASET_ID, order=":id"))
    df = pd.DataFrame.from_records(records)
    print(f"Extracted {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    return df


if __name__ == "__main__":
    # .fn() runs the plain function, skipping Prefect, for a quick test
    df = extract_data.fn()
    print(df.head(3).to_string())
