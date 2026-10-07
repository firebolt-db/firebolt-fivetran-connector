import os
import time
from decimal import Decimal
from typing import Any, Dict, Generator, List

import pytest
from firebolt.client.auth import ClientCredentials
from firebolt.db import connect
from fivetran_connector_sdk import Logging as log
from fivetran_connector_sdk import Operations

from connector import schema, update, validate_configuration

log.LOG_LEVEL = log.Level.FINE  # type: ignore


class CapturedOperations:
    """Records the operations the connector emits through the Fivetran SDK."""

    def __init__(self) -> None:
        self.upserts: List[Dict[str, Any]] = []
        self.checkpoints: List[Dict[str, Any]] = []

    def records_for(self, table: str) -> List[Dict[str, Any]]:
        """Return the data of all upserts emitted for the given table."""
        return [op["data"] for op in self.upserts if op["table"] == table]


@pytest.fixture
def captured_operations(monkeypatch: pytest.MonkeyPatch) -> CapturedOperations:
    """
    Capture upserts and checkpoints instead of sending them to the SDK.

    Since fivetran-connector-sdk 2.x, operations are pushed onto an internal
    queue drained by the SDK runtime, and checkpoint() blocks until that queue
    is consumed. Calling update() directly would hang, so the operations are
    intercepted here and the emitted data is asserted on instead.
    """
    captured = CapturedOperations()

    def fake_upsert(table: str, data: Dict[str, Any], **_: Any) -> None:
        captured.upserts.append({"table": table, "data": data})

    def fake_checkpoint(state: Dict[str, Any]) -> None:
        captured.checkpoints.append(state)

    monkeypatch.setattr(Operations, "upsert", staticmethod(fake_upsert))
    monkeypatch.setattr(Operations, "checkpoint", staticmethod(fake_checkpoint))
    return captured


@pytest.fixture
def firebolt_config() -> Dict[str, Any]:
    """Fixture providing Firebolt configuration from environment variables."""
    client_id = os.environ.get("client_id")
    client_secret = os.environ.get("client_secret")
    account_name = os.environ.get("account_name")
    database = os.environ.get("database")
    engine_name = os.environ.get("engine_name")
    api_endpoint = os.environ.get("api_endpoint")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing credentials in environment variables 'id' and 'secret'"
        )

    if not account_name or not database or not engine_name or not api_endpoint:
        raise ValueError(
            "Missing configuration in environment variables: account_name,"
            "database, engine_name, api_endpoint"
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "account_name": account_name,
        "database": database,
        "engine_name": engine_name,
        "api_endpoint": api_endpoint,
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
            bigint_col BIGINT,
            name STRING,
            numeric_col NUMERIC(10,2),
            float_col FLOAT,
            double_col DOUBLE PRECISION,
            real_col REAL,
            created_date DATE,
            updated_at TIMESTAMP,
            updated_at_tz TIMESTAMPTZ,
            is_active BOOLEAN,
            binary_data BYTEA,
            tags ARRAY(STRING),
            location GEOGRAPHY
        )
        """
        cursor.execute(create_table_sql)

        # Prepare binary data for testing
        binary_data = b"\\x01020304"

        test_data = [
            (
                1,  # id (INT)
                9223372036854775807,  # bigint_col (BIGINT)
                "Product A",  # name (STRING)
                99.99,  # numeric_col (NUMERIC)
                3.14,  # float_col (FLOAT)
                2.7182818284590452353602874713527,  # double_col (DOUBLE PRECISION)
                1.618,  # real_col (REAL)
                "2023-01-01",  # created_date (DATE)
                "2023-01-01 10:00:00",  # updated_at (TIMESTAMP)
                "2023-01-01 10:00:00+00:00",  # updated_at_tz (TIMESTAMPTZ)
                True,  # is_active (BOOLEAN)
                binary_data,  # binary_data (BYTEA)
                ["electronics", "gadgets"],  # tags (ARRAY)
                "POINT(0 0)",  # location (GEOGRAPHY)
            ),
            (
                2,  # id (INT)
                -9223372036854775808,  # bigint_col (BIGINT)
                "Product B",  # name (STRING)
                149.50,  # numeric_col (NUMERIC)
                2.718,  # float_col (FLOAT)
                3.1415926535897932384626433832795,  # double_col (DOUBLE PRECISION)
                2.718,  # real_col (REAL)
                "2023-01-02",  # created_date (DATE)
                "2023-01-02 11:00:00",  # updated_at (TIMESTAMP)
                "2023-01-02 11:00:00+00:00",  # updated_at_tz (TIMESTAMPTZ)
                False,  # is_active (BOOLEAN)
                binary_data,  # binary_data (BYTEA)
                ["books", "education"],  # tags (ARRAY)
                "POINT(1 1)",  # location (GEOGRAPHY)
            ),
            (
                3,  # id (INT)
                42,  # bigint_col (BIGINT)
                "Product C",  # name (STRING)
                75.25,  # numeric_col (NUMERIC)
                1.414,  # float_col (FLOAT)
                1.4142135623730950488016887242097,  # double_col (DOUBLE PRECISION)
                3.14,  # real_col (REAL)
                "2023-01-03",  # created_date (DATE)
                "2023-01-03 12:00:00",  # updated_at (TIMESTAMP)
                "2023-01-03 12:00:00+00:00",  # updated_at_tz (TIMESTAMPTZ)
                True,  # is_active (BOOLEAN)
                binary_data,  # binary_data (BYTEA)
                ["clothing", "fashion"],  # tags (ARRAY)
                "POINT(2 2)",  # location (GEOGRAPHY)
            ),
        ]

        for row in test_data:
            cursor.execute(
                f"""
            INSERT INTO "{table_name}" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            "id": "INT",
            "bigint_col": "LONG",
            "name": "STRING",
            "numeric_col": {"type": "DECIMAL", "precision": 10, "scale": 2},
            "float_col": "DOUBLE",  # Float is alias for DOUBLE in Firebolt
            "double_col": "DOUBLE",
            "real_col": "FLOAT",  # Real is alias for FLOAT in Firebolt
            "created_date": "NAIVE_DATE",
            "updated_at": "NAIVE_DATETIME",
            "updated_at_tz": "UTC_DATETIME",
            "is_active": "BOOLEAN",
            "binary_data": "BINARY",
            "tags": "JSON",
            "location": "STRING",
        }

        for col_name, expected_type in expected_columns.items():
            assert (
                col_name in test_table["columns"]
            ), f"Column {col_name} should be present"
            assert (
                test_table["columns"][col_name] == expected_type
            ), f"Column {col_name} should be {expected_type}"

    def test_update_function_with_test_data(
        self,
        firebolt_config: Dict[str, Any],
        test_table_setup: str,
        captured_operations: CapturedOperations,
    ) -> None:
        """Test update function emits correct operations for test table data."""
        update(firebolt_config, {})

        test_records = captured_operations.records_for(test_table_setup)

        assert (
            len(test_records) == 3
        ), f"Should have 3 upsert operations for test table, got {len(test_records)}"

        names = [record["name"] for record in test_records]
        assert "Product A" in names, "Should contain Product A"
        assert "Product B" in names, "Should contain Product B"
        assert "Product C" in names, "Should contain Product C"

        expected_columns = [
            "id",
            "bigint_col",
            "name",
            "numeric_col",
            "float_col",
            "double_col",
            "real_col",
            "created_date",
            "updated_at",
            "updated_at_tz",
            "is_active",
            "binary_data",
            "tags",
            "location",
        ]
        for record in test_records:
            assert set(record.keys()) == set(
                expected_columns
            ), f"Record keys should match expected columns, got {record.keys()}"

        assert (
            len(captured_operations.checkpoints) == 1
        ), "Should checkpoint once at the end of the sync"
        assert (
            test_table_setup in captured_operations.checkpoints[0]["table_cursors"]
        ), "Checkpoint should contain a cursor for the test table"

    def test_incremental_sync_with_iteration_column(
        self,
        firebolt_config: Dict[str, Any],
        test_table_setup: str,
        captured_operations: CapturedOperations,
    ) -> None:
        """Test incremental sync using iteration column emits filtered operations."""
        config_with_iteration = firebolt_config.copy()
        config_with_iteration["iteration_column"] = "updated_at"

        state = {
            "last_sync_time": "2023-01-01T00:00:00",
            "table_cursors": {test_table_setup: "2023-01-01 10:30:00"},
        }

        update(config_with_iteration, state)

        test_records = captured_operations.records_for(test_table_setup)

        assert (
            len(test_records) == 2
        ), f"Should have 2 upsert operations after cursor, got {len(test_records)}"

        names = [record["name"] for record in test_records]

        assert "Product B" in names, "Should contain Product B"
        assert "Product C" in names, "Should contain Product C"
        assert (
            "Product A" not in names
        ), "Should not contain Product A (filtered by cursor)"

        for record in test_records:
            updated_at = record.get("updated_at")
            assert updated_at is not None, "Record should have updated_at field"

        new_cursor = captured_operations.checkpoints[-1]["table_cursors"][
            test_table_setup
        ]
        assert new_cursor.startswith(
            "2023-01-03"
        ), f"Cursor should advance to the last synced row, got {new_cursor}"

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

    def test_data_type_mapping(
        self,
        firebolt_config: Dict[str, Any],
        test_table_setup: str,
        captured_operations: CapturedOperations,
    ) -> None:
        """
        Test that all data types are correctly mapped and data is
        correctly returned.
        """
        update(firebolt_config, {})

        test_records = captured_operations.records_for(test_table_setup)

        assert (
            len(test_records) == 3
        ), f"Should have 3 upsert operations for test table, got {len(test_records)}"

        # Find record for Product A
        product_a = None
        for record in test_records:
            if record.get("name") == "Product A":
                product_a = record
                break

        assert product_a is not None, "Product A should be in the results"

        # Verify each data type is correctly mapped and returned
        assert isinstance(product_a["id"], int), "INT should be mapped to an integer"
        assert product_a["id"] == 1, "INT value should be correct"

        assert isinstance(
            product_a["bigint_col"], int
        ), "BIGINT should be mapped to an integer"
        assert (
            product_a["bigint_col"] == 9223372036854775807
        ), "BIGINT value should be correct"

        assert isinstance(product_a["name"], str), "STRING should be mapped to a string"
        assert product_a["name"] == "Product A", "STRING value should be correct"

        assert isinstance(
            product_a["numeric_col"], Decimal
        ), "NUMERIC should be mapped to a Decimal"
        assert product_a["numeric_col"] == Decimal(
            "99.99"
        ), "NUMERIC value should be correct"

        assert isinstance(
            product_a["float_col"], float
        ), "FLOAT should be mapped to a float"
        assert (
            abs(product_a["float_col"] - 3.14) < 0.0001
        ), "FLOAT value should be correct"

        assert isinstance(
            product_a["double_col"], float
        ), "DOUBLE should be mapped to a float"
        assert (
            abs(product_a["double_col"] - 2.7182818284590452353602874713527) < 0.0001
        ), "DOUBLE value should be correct"

        assert isinstance(
            product_a["real_col"], float
        ), "REAL should be mapped to a float"
        assert (
            abs(product_a["real_col"] - 1.618) < 0.0001
        ), "REAL value should be correct"

        assert isinstance(
            product_a["created_date"], str
        ), "DATE should be mapped to a string"
        assert product_a["created_date"] == "2023-01-01", "DATE value should be correct"

        assert isinstance(
            product_a["updated_at"], str
        ), "TIMESTAMP should be mapped to a string"
        assert (
            "2023-01-01" in product_a["updated_at"]
        ), "TIMESTAMP value should be correct"

        assert isinstance(
            product_a["updated_at_tz"], str
        ), "TIMESTAMPTZ should be mapped to a string"
        assert (
            "2023-01-01" in product_a["updated_at_tz"]
        ), "TIMESTAMPTZ value should be correct"

        assert isinstance(
            product_a["is_active"], bool
        ), "BOOLEAN should be mapped to a bool"
        assert product_a["is_active"] is True, "BOOLEAN value should be correct"

        assert isinstance(
            product_a["binary_data"], bytes
        ), "BYTEA should be mapped to bytes"

        assert isinstance(
            product_a["tags"], str
        ), "ARRAY should be mapped to a JSON string"
        assert "electronics" in product_a["tags"], "ARRAY value should be correct"
        assert "gadgets" in product_a["tags"], "ARRAY value should be correct"

        assert isinstance(
            product_a["location"], str
        ), "GEOGRAPHY should be mapped to a string"
        assert len(product_a["location"]) > 0, "GEOGRAPHY value should not be empty"
