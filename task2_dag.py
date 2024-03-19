import json
import logging
from datetime import timedelta
from typing import List

import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateEmptyTableOperator, BigQueryInsertJobOperator)
from airflow.providers.google.cloud.operators.gcs import GCSListObjectsOperator

from common_package.utils import NginxLog, parse_nginx_log

logger = logging.getLogger("airflow.task")

default_args = {
    "start_date": airflow.utils.dates.days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

bucket_name = "nginx945235-bucket"
list_files_task_id = "list_log_files"

bq_dataset_id = "test"
bq_table = "nginx_access_logs"


def parse_single_log_file(file_content: bytes) -> List[NginxLog]:
    """
    Parse raw nginx logs and return list of NginxLog objects
    """
    access_logs: List[NginxLog] = []

    for row in file_content.decode("utf8").split("\n"):
        if not row:
            continue

        raw_log = json.loads(row)["textPayload"]
        try:
            parsed_log = parse_nginx_log(raw_log)
            access_logs.append(parsed_log)
        except ValueError:
            logger.warning(f"Can't process log: {raw_log}")

    return access_logs


def parse_files(**context):
    """
    Read list of file names from updstream task xcom.
    Detect timestamps in file name
    Push SQL subquery to xcom so downstream task can execute it
    """
    log_files = context["ti"].xcom_pull(task_ids=list_files_task_id, key="return_value")
    hook = GCSHook()
    access_logs: List[NginxLog] = []

    for file_name in log_files:
        # read file content to memory
        file_content = hook.download(
            bucket_name=bucket_name,
            object_name=file_name,
        )
        access_logs.extend(parse_single_log_file(file_content))

    # prepare input for sql query
    return_value = ",".join(
        [
            (
                f"('{log.remote_addr}', '{log.remote_user}', TIMESTAMP_SECONDS({log.time_local}), "
                f"'{log.http_method}', '{log.request_url}', '{log.http_protocol}', {log.status}, "
                f"{log.body_bytes_sent}, '{log.http_referer}', '{log.http_user_agent}', '{log.gzip_ratio}')"
            )
            for log in access_logs
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
    # filter out error log files
    match_glob="stdout/**",
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
                INSERT INTO test.nginx_access_logs
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
        {"name": "remote_addr", "type": "STRING", "mode": "NULLABLE"},
        {"name": "remote_user", "type": "STRING", "mode": "NULLABLE"},
        {"name": "time_local", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "http_method", "type": "STRING", "mode": "NULLABLE"},
        {"name": "request_url", "type": "STRING", "mode": "NULLABLE"},
        {"name": "http_protocol", "type": "STRING", "mode": "NULLABLE"},
        {"name": "status", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "body_bytes_sent", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "http_referer", "type": "STRING", "mode": "NULLABLE"},
        {"name": "http_user_agent", "type": "STRING", "mode": "NULLABLE"},
        {"name": "gzip_ratio", "type": "STRING", "mode": "NULLABLE"},
    ],
    if_exists="ignore",
    dag=dag,
)

destination_table_create >> list_files >> python_parser >> insert_query_job
