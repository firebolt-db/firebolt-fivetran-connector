# This is a Fivetran connector for Firebolt database.
"""Firebolt Fivetran Connector.
This connector demonstrates how to fetch data from Firebolt database and upsert it into destination using Firebolt Python SDK.
"""
# See the Technical Reference documentation (https://fivetran.com/docs/connectors/connector-sdk/technical-reference#update)
# and the Best Practices documentation (https://fivetran.com/docs/connectors/connector-sdk/best-practices) for details


import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from firebolt.client.auth import ClientCredentials
from firebolt.client.constants import DEFAULT_API_URL
from firebolt.db import connect

# For supporting Data operations like Upsert(), Update(), Delete() and checkpoint()
# For enabling Logs in your connector code
# Import required classes from fivetran_connector_sdk
# For supporting Connector operations like Update() and Schema()
from fivetran_connector_sdk import Connector
from fivetran_connector_sdk import Logging as log
from fivetran_connector_sdk import Operations as op

"""
GUIDELINES TO FOLLOW WHILE WRITING AN EXAMPLE CONNECTOR:
- Import only the necessary modules and libraries to keep the code clean and efficient.
- Use clear, consistent and descriptive names for your functions and variables.
- For constants and global variables, use uppercase letters with underscores (e.g. CHECKPOINT_INTERVAL, TABLE_NAME).
- Add comments to explain the purpose of each function in the docstring.
- Add comments to explain the purpose of complex logic within functions, where necessary.
- Add comments to highlight where users can make changes to the code to suit their specific use case.
- Split your code into smaller functions to improve readability and maintainability where required.
- Use logging to provide useful information about the connector's execution. Do not log excessively.
- Implement error handling to catch exceptions and log them appropriately. Catch specific exceptions where possible.
- Define the complete data model with primary key and data types in the schema function.
- Ensure that the connector does not load all data into memory at once. This can cause memory overflow errors. Use pagination or streaming where possible.
- Add comments to explain pagination or streaming logic to help users understand how to handle large datasets.
- Add comments for upsert, update and delete to explain the purpose of upsert, update and delete. This will help users understand the upsert, update and delete processes.
- Checkpoint your state at regular intervals to ensure that the connector can resume from the last successful sync in case of interruptions.
- Add comments for checkpointing to explain the purpose of checkpoint. This will help users understand the checkpointing process.
- Refer to the Best Practices documentation (https://fivetran.com/docs/connectors/connector-sdk/best-practices)
"""


def validate_configuration(configuration: dict) -> None:
    """
    Validate the configuration dictionary to ensure it contains all required parameters.
    This function is called at the start of the update method to ensure that the connector has all necessary configuration values.
    Args:
        configuration: a dictionary that holds the configuration settings for the connector.
    Raises:
        ValueError: if any required configuration parameter is missing.
    """

    required_configs = [
        "client_id",
        "client_secret",
        "account_name",
        "database",
        "engine_name",
    ]

    optional_configs = ["iteration_column", "api_endpoint"]
    for key in required_configs:
        if key not in configuration:
            raise ValueError(f"Missing required configuration value: {key}")
        if not configuration[key] or configuration[key].strip() == "":
            raise ValueError(f"Configuration value '{key}' cannot be empty")


def map_firebolt_type_to_fivetran(firebolt_type: str) -> str:
    """
    Map Firebolt data types to Fivetran data types.
    Args:
        firebolt_type: Firebolt column data type
    Returns:
        str: Corresponding Fivetran data type
    """
    type_mapping = {
        "INT": "INTEGER",
        "INTEGER": "INTEGER",
        "BIGINT": "LONG",
        "LONG": "LONG",
        "FLOAT": "DOUBLE",
        "DOUBLE": "DOUBLE",
        "DECIMAL": "DECIMAL",
        "NUMERIC": "DECIMAL",
        "TEXT": "STRING",
        "STRING": "STRING",
        "VARCHAR": "STRING",
        "BOOLEAN": "BOOLEAN",
        "DATE": "DATE",
        "TIMESTAMP": "TIMESTAMP_NTZ",
        "TIMESTAMPTZ": "TIMESTAMP_TZ",
    }

    upper_type = firebolt_type.upper()

    if "(" in upper_type:
        base_type = upper_type.split("(")[0]
        if base_type in type_mapping:
            return type_mapping[base_type]

    if upper_type.startswith("ARRAY"):
        return "JSON"

    return type_mapping.get(upper_type, "STRING")


def has_timestamp_column(cursor: Any, table_name: str, database: str) -> bool:
    """
    Check if table has a timestamp column for incremental sync.
    Args:
        cursor: Database cursor
        table_name: Name of the table
        database: Database name
    Returns:
        bool: True if table has timestamp columns
    """
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_schema = ? AND table_name = ? 
        AND data_type IN ('TIMESTAMP', 'TIMESTAMPTZ', 'DATE')
    """,
        [database, table_name],
    )

    result = cursor.fetchone()
    return result[0] > 0 if result else False


def schema(configuration: dict) -> List[Dict[str, Any]]:
    """
    Define the schema function which discovers tables from Firebolt database.
    See the technical reference documentation for more details on the schema function:
    https://fivetran.com/docs/connectors/connector-sdk/technical-reference#schema
    Args:
        configuration: a dictionary that holds the configuration settings for the connector.
    """

    validate_configuration(configuration)

    auth = ClientCredentials(
        client_id=configuration["client_id"],
        client_secret=configuration["client_secret"],
    )

    with connect(
        auth=auth,
        account_name=configuration["account_name"],
        database=configuration["database"],
        engine_name=configuration["engine_name"],
        api_endpoint=configuration.get("api_endpoint", f"https://{DEFAULT_API_URL}"),
    ) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """,
        )

        results = cursor.fetchall()

        tables = {}
        for row in results:
            table_name, column_name, data_type, is_nullable = row
            if table_name not in tables:
                tables[table_name] = {
                    "table": table_name,
                    "primary_key": ["_fivetran_id"],
                    "columns": {},
                }

            fivetran_type = map_firebolt_type_to_fivetran(data_type)
            tables[table_name]["columns"][column_name] = fivetran_type

        return list(tables.values())


def update(configuration: dict, state: dict) -> Any:
    """
     Define the update function, which is a required function, and is called by Fivetran during each sync.
    See the technical reference documentation for more details on the update function
    https://fivetran.com/docs/connectors/connector-sdk/technical-reference#update
    Args:
        configuration: A dictionary containing connection details
        state: A dictionary containing state information from previous runs
        The state dictionary is empty for the first sync or for any full re-sync
    """

    if not hasattr(log, "LOG_LEVEL") or log.LOG_LEVEL is None:
        log.LOG_LEVEL = log.Level.INFO

    log.info("Starting Firebolt data sync")

    validate_configuration(configuration=configuration)

    auth = ClientCredentials(
        client_id=configuration["client_id"],
        client_secret=configuration["client_secret"],
    )

    last_sync_time = state.get("last_sync_time")
    table_cursors = state.get("table_cursors", {})

    try:
        with connect(
            auth=auth,
            account_name=configuration["account_name"],
            database=configuration["database"],
            engine_name=configuration["engine_name"],
            api_endpoint=configuration.get(
                "api_endpoint", f"https://{DEFAULT_API_URL}"
            ),
        ) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT DISTINCT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """,
            )

            tables = [row[0] for row in cursor.fetchall()]
            log.info(f"Found {len(tables)} tables to sync: {tables}")

            current_sync_time = datetime.utcnow().isoformat()
            new_table_cursors = {}

            for table_name in tables:
                log.info(f"Syncing table: {table_name}")

                iteration_column = configuration.get("iteration_column")
                last_cursor = table_cursors.get(table_name)

                query = f'SELECT * FROM "{table_name}"'
                if last_cursor and iteration_column:
                    query += f" WHERE \"{iteration_column}\" > '{last_cursor}'"
                    query += f' ORDER BY "{iteration_column}"'

                cursor.execute_stream(query)

                batch_size = 1000
                batch_count = 0
                last_iteration_value = None

                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break

                    columns = [desc.name for desc in cursor.description]

                    for row in rows:
                        record = dict(zip(columns, row))

                        record["_fivetran_id"] = f"{table_name}_{hash(str(row))}"

                        if iteration_column and iteration_column in record:
                            last_iteration_value = record[iteration_column]

                        yield op.upsert(table=table_name, data=record)

                    batch_count += 1
                    if batch_count % 10 == 0:
                        log.info(
                            f"Processed {batch_count * batch_size} records from {table_name}"
                        )

                if iteration_column and last_iteration_value is not None:
                    new_table_cursors[table_name] = str(last_iteration_value)
                else:
                    new_table_cursors[table_name] = current_sync_time

                log.info(f"Completed sync for table: {table_name}")

            new_state = {
                "last_sync_time": current_sync_time,
                "table_cursors": new_table_cursors,
            }

            yield op.checkpoint(new_state)
            log.info("Firebolt sync completed successfully")

    except Exception as e:
        log.severe(f"Failed to sync data from Firebolt: {str(e)}")
        raise RuntimeError(f"Failed to sync data: {str(e)}")


# Create the connector object using the schema and update functions
connector = Connector(update=update, schema=schema)

# Check if the script is being run as the main module.
# This is Python's standard entry method allowing your script to be run directly from the command line or IDE 'run' button.
# This is useful for debugging while you write your code. Note this method is not called by Fivetran when executing your connector in production.
# Please test using the Fivetran debug command prior to finalizing and deploying your connector.
if __name__ == "__main__":
    # Open the configuration.json file and load its contents
    with open("configuration.json", "r") as f:
        configuration = json.load(f)

    # Test the connector locally
    connector.debug(configuration=configuration)
