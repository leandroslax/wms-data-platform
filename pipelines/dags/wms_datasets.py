"""Dataset definitions shared across WMS Airflow DAGs."""

from airflow.datasets import Dataset

BRONZE_REFRESH_DATASET = Dataset("wms://bronze/refresh")
DBT_GOLD_REFRESH_DATASET = Dataset("wms://gold/dbt_refresh")
QUALITY_GATE_DATASET = Dataset("wms://gold/quality_passed")
