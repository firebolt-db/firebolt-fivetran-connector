import os
import time
from typing import Any, Dict, Generator

import pytest
from firebolt.client.auth import ClientCredentials
from firebolt.db import connect
from fivetran_connector_sdk import Logging as log
from fivetran_connector_sdk.protos.connector_sdk_pb2 import Record

from connector import schema, update, validate_configuration

log.LOG_LEVEL = log.Level.FINE  # type: ignore


def extract_record_data(record: Record) -> Dict[str, Any]:
    """Helper function to extract data from a record."""
    data = {}
    for key in record.data:
        field_value = record.data[key]
        print(f"Processing value : {field_value}")
        if field_value.HasField("string"):
            data[key] = field_value.string
        elif field_value.HasField("long"):
            data[key] = field_value.long
        elif field_value.HasField("double"):
            data[key] = field_value.double
        elif field_value.HasField("binary"):
            data[key] = field_value.binary
        elif field_value.HasField("float"):
            data[key] = field_value.float
        elif field_value.HasField("boolean"):
            data[key] = field_value.boolean
    return data


@pytest.fixture
def firebolt_config() -> Dict[str, Any]:
    """Fixture providing Firebolt configuration from environment variables."""
    client_id = os.environ.get("id")
    client_secret = os.environ.get("secret")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing credentials in environment variables 'id' and 'secret'"
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "account_name": os.environ.get("account_name"),
        "database": os.environ.get("database"),
        "engine_name": os.environ.get("engine_name"),
        "api_endpoint": os.environ.get("api_endpoint"),
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
            id INT,                           /* Integer type */
            bigint_col BIGINT,                /* Bigint type */
            name STRING,                      /* String type */
            numeric_col NUMERIC(10,2),        /* Numeric/Decimal type */
            float_col FLOAT,                  /* Float type */
            double_col DOUBLE PRECISION,      /* Double precision type */
            real_col REAL,                    /* Real type */
            created_date DATE,                /* Date type */
            updated_at TIMESTAMP,             /* Timestamp type */
            updated_at_tz TIMESTAMPTZ,        /* Timestamptz type */
            is_active BOOLEAN,                /* Boolean type */
            binary_data BYTEA,                /* Binary type */
            tags ARRAY(STRING),               /* Array type */
            location GEOGRAPHY               /* Geography type */
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
            "numeric_col": "DECIMAL",
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
        self, firebolt_config: Dict[str, Any], test_table_setup: str
    ) -> None:
        """Test update function emits correct operations for test table data."""
        state: Dict[str, Any] = {}

        update_generator = update(firebolt_config, state)

        operations = []
        for operation in update_generator:
            operations.append(operation)
            if len(operations) > 300:
                log.warning(
                    "More than 300 operations received, "
                    "stopping iteration to avoid infinite loop"
                )
                break

        upsert_ops = []
        for op in operations:
            if isinstance(op, list):
                if len(op) > 0:
                    update_response = op[0]
                    if hasattr(update_response, "record") and update_response.HasField(
                        "record"
                    ):
                        record = update_response.record
                        if record.table_name == test_table_setup:
                            upsert_ops.append(record)

        assert (
            len(upsert_ops) == 3
        ), f"Should have 3 upsert operations for test table, got {len(upsert_ops)}"

        test_records = [extract_record_data(record) for record in upsert_ops]

        assert len(test_records) == 3, "Should have 3 test records"

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

    def test_incremental_sync_with_iteration_column(
        self, firebolt_config: Dict[str, Any], test_table_setup: str
    ) -> None:
        """Test incremental sync using iteration column emits filtered operations."""
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
            if len(operations) > 300:
                log.warning(
                    "More than 300 operations received, "
                    "stopping iteration to avoid infinite loop"
                )
                break

        upsert_ops = []
        for op in operations:
            if isinstance(op, list):
                if len(op) > 0:
                    update_response = op[0]
                    if hasattr(update_response, "record") and update_response.HasField(
                        "record"
                    ):
                        record = update_response.record
                        if record.table_name == test_table_setup:
                            upsert_ops.append(record)

        assert (
            len(upsert_ops) == 2
        ), f"Should have 2 upsert operations after cursor, got {len(upsert_ops)}"

        test_records = [extract_record_data(record) for record in upsert_ops]

        names = [record["name"] for record in test_records]

        assert "Product B" in names, "Should contain Product B"
        assert "Product C" in names, "Should contain Product C"
        assert (
            "Product A" not in names
        ), "Should not contain Product A (filtered by cursor)"

        for record in test_records:
            updated_at = record.get("updated_at")
            assert updated_at is not None, "Record should have updated_at field"

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
        self, firebolt_config: Dict[str, Any], test_table_setup: str
    ) -> None:
        """
        Test that all data types are correctly mapped and data is
        correctly returned.
        """
        state: Dict[str, Any] = {}

        update_generator = update(firebolt_config, state)

        operations = []
        for operation in update_generator:
            operations.append(operation)
            if len(operations) > 300:
                log.warning(
                    "More than 300 operations received, "
                    "stopping iteration to avoid infinite loop"
                )
                break

        upsert_ops = []
        for op in operations:
            if isinstance(op, list) and len(op) > 0:
                update_response = op[0]
                if hasattr(update_response, "record") and update_response.HasField(
                    "record"
                ):
                    record = update_response.record
                    if record.table_name == test_table_setup:
                        upsert_ops.append(record)

        assert (
            len(upsert_ops) == 3
        ), f"Should have 3 upsert operations for test table, got {len(upsert_ops)}"

        test_records = [extract_record_data(record) for record in upsert_ops]

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
            product_a["numeric_col"], float
        ), "NUMERIC should be mapped to a float"
        assert (
            abs(product_a["numeric_col"] - 99.99) < 0.0001
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
        ), "BOOLEAN should be mapped to a boolean"
        assert product_a["is_active"] is True, "BOOLEAN value should be correct"

        assert "binary_data" in product_a, "BYTEA should be present"

        assert isinstance(
            product_a["tags"], str
        ), "ARRAY should be mapped to a JSON string"
        assert "electronics" in product_a["tags"], "ARRAY value should be correct"
        assert "gadgets" in product_a["tags"], "ARRAY value should be correct"

        assert isinstance(
            product_a["location"], str
        ), "GEOGRAPHY should be mapped to a string"
        assert "POINT" in product_a["location"], "GEOGRAPHY value should be correct"
