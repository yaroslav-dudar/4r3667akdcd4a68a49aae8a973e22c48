import airflow
from airflow import DAG
from airflow.contrib.operators.bigquery_operator import (
    BigQueryOperator,
    BigQueryCreateEmptyTableOperator,
)
from datetime import timedelta

default_args = {
    "start_date": airflow.utils.dates.days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dataset_id = "test"
destination_table = "aggregated_events"
source_table = "events"

dag = DAG(
    "task1",
    default_args=default_args,
    description="aggregate data from BigQuery table",
    schedule_interval="*/5 * * * *",
    max_active_runs=2,
    catchup=False,
    dagrun_timeout=timedelta(minutes=5),
)

source_table_create = BigQueryCreateEmptyTableOperator(
    task_id="bq_create_source_table",
    dataset_id=dataset_id,
    table_id=source_table,
    schema_fields=[
        {"name": "random_character", "type": "STRING", "mode": "NULLABLE"},
        {"name": "random_digit", "type": "INTEGER", "mode": "NULLABLE"},
    ],
    if_exists="ignore",
    dag=dag,
)

destination_table_create = BigQueryCreateEmptyTableOperator(
    task_id="bq_create_destination_table",
    dataset_id=dataset_id,
    table_id=source_table,
    schema_fields=[
        {"name": "current_timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "character", "type": "STRING", "mode": "NULLABLE"},
        {"name": "sum_digits", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "count_all", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "max_digit", "type": "INTEGER", "mode": "NULLABLE"},
    ],
    if_exists="ignore",
    dag=dag,
)

execute_query = BigQueryOperator(
    task_id="bq_aggregate_events",
    use_legacy_sql=False,
    write_disposition="WRITE_APPEND",
    allow_large_results=True,
    sql=f"""
    WITH agg_events AS (
        SELECT
            max(random_digit) OVER () AS max_digit,
            count(random_digit) OVER () AS count_all,
            random_digit,
            random_character
        FROM `{dataset_id}.{source_table}`
    )

    SELECT
        TIMESTAMP_MILLIS( CAST(UNIX_MILLIS(CURRENT_TIMESTAMP()) / 60000 AS INT64) * 60000) AS current_timestamp,
        upper(random_character) AS character,
        sum(random_digit) AS sum_digits,
        max(max_digit) AS max_digit,
        max(count_all) AS count_all
    FROM agg_events GROUP BY upper(random_character);

    """,
    destination_dataset_table=f"{dataset_id}.{destination_table}",
    dag=dag,
)

source_table_create >> destination_table_create >> execute_query
