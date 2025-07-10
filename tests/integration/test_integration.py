import os
import time
from datetime import datetime
from typing import Any, Dict, Generator

import pytest
from firebolt.client.auth import ClientCredentials
from firebolt.db import connect

from connector import schema, update, validate_configuration


@pytest.fixture
def firebolt_config() -> Dict[str, Any]:
    """Fixture providing Firebolt configuration from environment variables."""
    client_id = os.environ.get("id")
    client_secret = os.environ.get("secret")

    if not client_id or not client_secret:
        pytest.skip("Missing credentials in environment variables 'id' and 'secret'")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "account_name": os.environ.get("account_name", "automation"),
        "database": os.environ.get("database", "petro_test"),
        "engine_name": os.environ.get("engine_name", "petro_test"),
        "api_endpoint": os.environ.get(
            "api_endpoint", "https://api.staging.firebolt.io"
        ),
    }


@pytest.fixture
def test_table_setup(firebolt_config: Dict[str, Any]) -> Generator[str, None, None]:
    """Fixture that creates a test table with known data and cleans it up."""
    timestamp = int(time.time())
    table_name = f"fivetran_test_table_{timestamp}"

    auth = ClientCredentials(
        client_id=firebolt_config["client_id"],
        client_secret=firebolt_config["client_secret"],
    )

    with connect(
        auth=auth,
        account_name=firebolt_config["account_name"],
        database=firebolt_config["database"],
        engine_name=firebolt_config["engine_name"],
        api_endpoint=firebolt_config["api_endpoint"],
    ) as connection:
        cursor = connection.cursor()

        create_table_sql = f"""
        CREATE DIMENSION TABLE "{table_name}" (
            id INT,
            name STRING,
            created_date DATE,
            updated_at TIMESTAMP,
            is_active BOOLEAN,
            price DECIMAL(10,2),
            tags ARRAY(STRING)
        )
        """
        cursor.execute(create_table_sql)

        test_data = [
            (
                1,
                "Product A",
                "2023-01-01",
                "2023-01-01 10:00:00",
                True,
                99.99,
                ["electronics", "gadgets"],
            ),
            (
                2,
                "Product B",
                "2023-01-02",
                "2023-01-02 11:00:00",
                False,
                149.50,
                ["books", "education"],
            ),
            (
                3,
                "Product C",
                "2023-01-03",
                "2023-01-03 12:00:00",
                True,
                75.25,
                ["clothing", "fashion"],
            ),
        ]

        for row in test_data:
            cursor.execute(
                f"""
            INSERT INTO "{table_name}" VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                row,
            )

        try:
            yield table_name
        finally:
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')


class TestFireboltConnectorIntegration:
    """Integration tests for Firebolt Fivetran connector with dedicated test table."""

    def test_configuration_validation(self, firebolt_config: Dict[str, Any]) -> None:
        """Test that configuration validation passes with real config."""
        validate_configuration(firebolt_config)

    def test_schema_discovery_with_test_table(
        self, firebolt_config: Dict[str, Any], test_table_setup: str
    ) -> None:
        """Test schema discovery with dedicated test table."""
        tables = schema(firebolt_config)

        assert isinstance(tables, list), "Schema should return a list of tables"

        test_table = None
        for table in tables:
            if table["table"] == test_table_setup:
                test_table = table
                break

        assert (
            test_table is not None
        ), f"Test table {test_table_setup} should be discovered"

        assert "table" in test_table, "Table should have 'table' key"
        assert "primary_key" in test_table, "Table should have 'primary_key' key"
        assert "columns" in test_table, "Table should have 'columns' key"

        expected_columns = {
            "id": "INTEGER",
            "name": "STRING",
            "created_date": "DATE",
            "updated_at": "TIMESTAMP_NTZ",
            "is_active": "BOOLEAN",
            "price": "DECIMAL",
            "tags": "JSON",
        }

        for col_name, expected_type in expected_columns.items():
            assert (
                col_name in test_table["columns"]
            ), f"Column {col_name} should be present"
            assert (
                test_table["columns"][col_name] == expected_type
            ), f"Column {col_name} should be {expected_type}"

    def test_update_function_with_test_data(
        self, firebolt_config: Dict[str, Any], test_table_setup: str
    ) -> None:
        """Test update function with known test data."""
        state: Dict[str, Any] = {}

        update_generator = update(firebolt_config, state)

        operations = []
        for operation in update_generator:
            operations.append(operation)
            if (
                len(operations) > 5
                and hasattr(operation, "type")
                and operation.type == "CHECKPOINT"
            ):
                break

        upsert_ops = [
            op
            for op in operations
            if hasattr(op, "type")
            and op.type == "UPSERT"
            and op.table == test_table_setup
        ]
        assert (
            len(upsert_ops) == 3
        ), f"Should have 3 upsert operations for test table, got {len(upsert_ops)}"

        test_records = [op.data for op in upsert_ops]
        assert len(test_records) == 3, "Should have 3 test records"

        names = [record["name"] for record in test_records]
        assert "Product A" in names, "Should contain Product A"
        assert "Product B" in names, "Should contain Product B"
        assert "Product C" in names, "Should contain Product C"

    def test_incremental_sync_with_iteration_column(
        self, firebolt_config: Dict[str, Any], test_table_setup: str
    ) -> None:
        """Test incremental sync using iteration column with test data."""
        config_with_iteration = firebolt_config.copy()
        config_with_iteration["iteration_column"] = "updated_at"

        state = {
            "last_sync_time": "2023-01-01T00:00:00",
            "table_cursors": {test_table_setup: "2023-01-01 10:30:00"},
        }

        update_generator = update(config_with_iteration, state)

        operations = []
        for operation in update_generator:
            operations.append(operation)
            if len(operations) > 10:
                break

        upsert_ops = [
            op
            for op in operations
            if hasattr(op, "type")
            and op.type == "UPSERT"
            and op.table == test_table_setup
        ]

        assert (
            len(upsert_ops) == 2
        ), f"Should have 2 upsert operations after cursor, got {len(upsert_ops)}"

        names = [op.data["name"] for op in upsert_ops]
        assert "Product B" in names, "Should contain Product B"
        assert "Product C" in names, "Should contain Product C"
        assert (
            "Product A" not in names
        ), "Should not contain Product A (filtered by cursor)"

    def test_configuration_with_custom_iteration_column(
        self, firebolt_config: Dict[str, Any]
    ) -> None:
        """Test configuration with custom iteration column for incremental sync."""
        config_with_iteration = firebolt_config.copy()
        config_with_iteration["iteration_column"] = "updated_at"

        validate_configuration(config_with_iteration)

        tables = schema(config_with_iteration)
        assert isinstance(
            tables, list
        ), "Schema should work with iteration column config"
