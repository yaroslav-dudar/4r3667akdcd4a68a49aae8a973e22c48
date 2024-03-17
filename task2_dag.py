from datetime import timedelta

import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateEmptyTableOperator,
    BigQueryInsertJobOperator,
)
from airflow.providers.google.cloud.operators.gcs import GCSListObjectsOperator

from common_package.utils import parse_file_name

default_args = {
    "start_date": airflow.utils.dates.days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

bucket_name = "nginx945235-bucket"
list_files_task_id = "list_log_files"

bq_dataset_id = "test"
bq_table = "log_files"


def parse_files(**context):
    """
    Read list of file names from updstream task xcom.
    Detect timestamps in file name
    Push SQL subquery to xcom so downstream task can execute it
    """
    log_files = context["ti"].xcom_pull(task_ids=list_files_task_id, key="return_value")
    rows = []
    for file_name in log_files:
        from_timestamp, to_timestamp = parse_file_name(file_name)
        rows.append((file_name, from_timestamp, to_timestamp))

    return_value = ",".join(
        [
            f"('{name}', TIMESTAMP_SECONDS({from_timestamp}), TIMESTAMP_SECONDS({to_timestamp}))"
            for name, from_timestamp, to_timestamp in rows
        ]
    )
    context["ti"].xcom_push(key="return_value", value=return_value)


dag = DAG(
    "task2",
    default_args=default_args,
    description="Parse logs from GCS bucket",
    schedule_interval=None,
    max_active_runs=2,
    catchup=False,
    dagrun_timeout=timedelta(minutes=5),
)


list_files = GCSListObjectsOperator(
    task_id=list_files_task_id,
    bucket=bucket_name,
    dag=dag,
)

python_parser = PythonOperator(
    task_id="parser",
    python_callable=parse_files,
    dag=dag,
)

insert_query_job = BigQueryInsertJobOperator(
    task_id="insert",
    configuration={
        "query": {
            "query": """
                INSERT INTO test.log_files (file_name, from_timestamp, to_timestamp)
                VALUES {{ ti.xcom_pull(task_ids='parser', key='return_value') }}
            """,
            "useLegacySql": False,
            "priority": "BATCH",
        }
    },
    dag=dag,
)

destination_table_create = BigQueryCreateEmptyTableOperator(
    task_id="bq_create_table",
    dataset_id=bq_dataset_id,
    table_id=bq_table,
    schema_fields=[
        {"name": "file_name", "type": "STRING", "mode": "NULLABLE"},
        {"name": "from_timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "to_timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
    ],
    if_exists="ignore",
    dag=dag,
)

destination_table_create >> list_files >> python_parser >> insert_query_job
