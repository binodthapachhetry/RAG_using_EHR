from google.cloud import bigquery

# --- utility to build CREATE TABLE DDLs -----------------------------------+
def _field_to_sql(field: bigquery.SchemaField) -> str:
    type_map = {
        "STRING": "STRING", "INTEGER": "INT64", "INT64": "INT64",
        "FLOAT": "FLOAT64", "FLOAT64": "FLOAT64", "BOOLEAN": "BOOL",
        "BOOL": "BOOL", "TIMESTAMP": "TIMESTAMP", "DATE": "DATE",
        "TIME": "TIME", "DATETIME": "DATETIME", "NUMERIC": "NUMERIC",
        "BIGNUMERIC": "BIGNUMERIC", "GEOGRAPHY": "GEOGRAPHY", "JSON": "JSON"
    }
    sql_type = type_map.get(field.field_type.upper(), "JSON")
    if field.mode == "REPEATED":
        sql_type = f"ARRAY<{sql_type}>"
    return f"{field.name} {sql_type}"

# --- public API -----------------------------------------------------------+
def get_fhir_synthea_schema(project_id: str, dataset_id: str) -> dict[str, str]:
    """
    Return {fully_qualified_table_name: CREATE TABLE DDL} for every table
    in the specified dataset.  Runs once at start-up; caller may cache.
    """
    client = bigquery.Client(project=project_id)
    ddl_map: dict[str, str] = {}
    for tbl in client.list_tables(f"{project_id}.{dataset_id}"):
        fq_table = f"`{tbl.project}.{tbl.dataset_id}.{tbl.table_id}`"
        schema = client.get_table(tbl.reference).schema
        columns = ",\n    ".join(_field_to_sql(f) for f in schema)
        ddl_map[fq_table] = f"CREATE TABLE {fq_table} (\n    {columns}\n);"
    return ddl_map
