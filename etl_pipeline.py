"""The full ETL pipeline as a Prefect flow: Extract -> Validate -> Transform -> Load."""
from prefect import flow

from extract import extract_data
from load import load_data
from transform import transform_data
from validate import validate_data


@flow(name="cpd_incident_etl", log_prints=True)
def cpd_incident_etl() -> int:
    raw = extract_data()
    clean = validate_data(raw)
    transformed = transform_data(clean)
    return load_data(transformed)


if __name__ == "__main__":
    cpd_incident_etl()
