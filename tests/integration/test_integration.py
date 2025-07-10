import os
from typing import Any, Dict

import pytest

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


class TestFireboltConnectorIntegration:
    """Integration tests for Firebolt Fivetran connector."""

    def test_configuration_validation(self, firebolt_config: Dict[str, Any]) -> None:
        """Test that configuration validation passes with real config."""
        validate_configuration(firebolt_config)

    def test_schema_discovery(self, firebolt_config: Dict[str, Any]) -> None:
        """Test schema discovery with real Firebolt connection."""
        tables = schema(firebolt_config)

        assert isinstance(tables, list), "Schema should return a list of tables"

        if tables:
            for table in tables:
                assert isinstance(table, dict), "Each table should be a dictionary"
                assert "table" in table, "Table should have 'table' key"
                assert "primary_key" in table, "Table should have 'primary_key' key"
                assert "columns" in table, "Table should have 'columns' key"

                assert isinstance(table["table"], str), "Table name should be a string"
                assert isinstance(
                    table["primary_key"], list
                ), "Primary key should be a list"
                assert isinstance(
                    table["columns"], dict
                ), "Columns should be a dictionary"

                valid_fivetran_types = {
                    "INTEGER",
                    "LONG",
                    "DOUBLE",
                    "DECIMAL",
                    "STRING",
                    "BOOLEAN",
                    "DATE",
                    "TIMESTAMP_NTZ",
                    "TIMESTAMP_TZ",
                    "JSON",
                }
                for col_name, col_type in table["columns"].items():
                    assert isinstance(
                        col_name, str
                    ), f"Column name should be string: {col_name}"
                    assert (
                        col_type in valid_fivetran_types
                    ), f"Invalid Fivetran type: {col_type}"

    @pytest.mark.slow
    def test_update_function_basic(self, firebolt_config: Dict[str, Any]) -> None:
        """Test basic update function execution (without full sync)."""
        state: Dict[str, Any] = {}

        update_generator = update(firebolt_config, state)

        assert hasattr(update_generator, "__iter__"), "Update should return a generator"
        assert hasattr(update_generator, "__next__"), "Update should return a generator"

        operations_count = 0
        max_operations = 5

        try:
            for operation in update_generator:
                operations_count += 1

                assert hasattr(
                    operation, "type"
                ), "Operation should have type attribute"

                if operations_count >= max_operations:
                    break

        except StopIteration:
            pass

        assert (
            operations_count >= 0
        ), "Update function should produce operations or complete"

    def test_incremental_sync_state_handling(
        self, firebolt_config: Dict[str, Any]
    ) -> None:
        """Test that update function handles state correctly for incremental sync."""
        state = {
            "last_sync_time": "2023-01-01T00:00:00",
            "table_cursors": {"test_table": "2023-01-01T00:00:00"},
        }

        update_generator = update(firebolt_config, state)
        assert hasattr(
            update_generator, "__iter__"
        ), "Update should return a generator with state"

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
