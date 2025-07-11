from typing import Dict, Union

import pytest

from connector import map_firebolt_type_to_fivetran, validate_configuration


class TestValidateConfiguration:
    """Test cases for validate_configuration function."""

    def test_validate_configuration_success(self) -> None:
        """Test that valid configuration passes validation."""
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "account_name": "test_account",
            "database": "test_database",
            "engine_name": "test_engine",
        }
        validate_configuration(config)

    def test_validate_configuration_missing_key(self) -> None:
        """Test that missing required key raises ValueError."""
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "account_name": "test_account",
            "database": "test_database",
        }
        with pytest.raises(
            ValueError, match="Missing required configuration value: engine_name"
        ):
            validate_configuration(config)

    def test_validate_configuration_empty_value(self) -> None:
        """Test that empty string value raises ValueError."""
        config = {
            "client_id": "test_client_id",
            "client_secret": "",
            "account_name": "test_account",
            "database": "test_database",
            "engine_name": "test_engine",
        }
        with pytest.raises(
            ValueError, match="Configuration value 'client_secret' cannot be empty"
        ):
            validate_configuration(config)

    def test_validate_configuration_whitespace_only_value(self) -> None:
        """Test that whitespace-only value raises ValueError."""
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "account_name": "   ",
            "database": "test_database",
            "engine_name": "test_engine",
        }
        with pytest.raises(
            ValueError, match="Configuration value 'account_name' cannot be empty"
        ):
            validate_configuration(config)

    def test_validate_configuration_none_value(self) -> None:
        """Test that None value raises ValueError."""
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "account_name": "test_account",
            "database": None,
            "engine_name": "test_engine",
        }
        with pytest.raises(
            ValueError, match="Configuration value 'database' cannot be empty"
        ):
            validate_configuration(config)

    def test_validate_configuration_all_required_keys(self) -> None:
        """Test that all required keys are checked."""
        required_keys = [
            "client_id",
            "client_secret",
            "account_name",
            "database",
            "engine_name",
        ]

        for missing_key in required_keys:
            config = {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "account_name": "test_account",
                "database": "test_database",
                "engine_name": "test_engine",
            }
            del config[missing_key]

            with pytest.raises(
                ValueError, match=f"Missing required configuration value: {missing_key}"
            ):
                validate_configuration(config)


class TestMapFireboltTypeToFivetran:
    """Test cases for map_firebolt_type_to_fivetran function."""

    @pytest.fixture
    def expected_decimal(self) -> Dict[str, Union[str, int]]:
        """Helper function to return expected decimal type."""
        return {
            "type": "DECIMAL",
            "precision": 10,
            "scale": 2,
        }

    @pytest.fixture
    def expected_numeric(self) -> Dict[str, Union[str, int]]:
        """Helper function to return expected numeric type."""
        return {
            "type": "DECIMAL",
            "precision": 38,
            "scale": 9,
        }

    def test_integer_types(self) -> None:
        """Test mapping of integer types."""
        assert map_firebolt_type_to_fivetran("INT") == "INT"
        assert map_firebolt_type_to_fivetran("INTEGER") == "INT"
        assert map_firebolt_type_to_fivetran("INT4") == "INT"
        assert map_firebolt_type_to_fivetran("int") == "INT"
        assert map_firebolt_type_to_fivetran("integer") == "INT"
        assert map_firebolt_type_to_fivetran("int4") == "INT"

    def test_long_types(self) -> None:
        """Test mapping of long/bigint types."""
        assert map_firebolt_type_to_fivetran("BIGINT") == "LONG"
        assert map_firebolt_type_to_fivetran("LONG") == "LONG"
        assert map_firebolt_type_to_fivetran("INT8") == "LONG"
        assert map_firebolt_type_to_fivetran("bigint") == "LONG"
        assert map_firebolt_type_to_fivetran("long") == "LONG"
        assert map_firebolt_type_to_fivetran("int8") == "LONG"

    def test_float_types(self) -> None:
        """Test mapping of float/double types."""
        assert map_firebolt_type_to_fivetran("FLOAT") == "FLOAT"
        assert map_firebolt_type_to_fivetran("FLOAT4") == "FLOAT"
        assert map_firebolt_type_to_fivetran("REAL") == "FLOAT"
        assert map_firebolt_type_to_fivetran("float") == "FLOAT"
        assert map_firebolt_type_to_fivetran("float4") == "FLOAT"
        assert map_firebolt_type_to_fivetran("real") == "FLOAT"

    def test_double_types(self) -> None:
        """Test mapping of double precision types."""
        assert map_firebolt_type_to_fivetran("DOUBLE") == "DOUBLE"
        assert map_firebolt_type_to_fivetran("FLOAT8") == "FLOAT"
        assert map_firebolt_type_to_fivetran("DOUBLE PRECISION") == "DOUBLE"
        assert map_firebolt_type_to_fivetran("double") == "DOUBLE"
        assert map_firebolt_type_to_fivetran("float8") == "FLOAT"
        assert map_firebolt_type_to_fivetran("double precision") == "DOUBLE"

    def test_decimal_types(self, expected_decimal, expected_numeric) -> None:
        """Test mapping of decimal/numeric types."""
        assert map_firebolt_type_to_fivetran("DECIMAL") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("NUMERIC") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("decimal") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("numeric") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("DECIMAL(10,2)") == expected_decimal
        assert map_firebolt_type_to_fivetran("NUMERIC(38,9)") == expected_numeric

    def test_string_types(self) -> None:
        """Test mapping of string types."""
        assert map_firebolt_type_to_fivetran("TEXT") == "STRING"
        assert map_firebolt_type_to_fivetran("STRING") == "STRING"
        assert map_firebolt_type_to_fivetran("text") == "STRING"
        assert map_firebolt_type_to_fivetran("string") == "STRING"

    def test_boolean_type(self) -> None:
        """Test mapping of boolean type."""
        assert map_firebolt_type_to_fivetran("BOOLEAN") == "BOOLEAN"
        assert map_firebolt_type_to_fivetran("BOOL") == "BOOLEAN"
        assert map_firebolt_type_to_fivetran("boolean") == "BOOLEAN"
        assert map_firebolt_type_to_fivetran("bool") == "BOOLEAN"

    def test_date_types(self) -> None:
        """Test mapping of date/timestamp types."""
        assert map_firebolt_type_to_fivetran("DATE") == "NAIVE_DATE"
        assert map_firebolt_type_to_fivetran("TIMESTAMP") == "NAIVE_DATETIME"
        assert map_firebolt_type_to_fivetran("TIMESTAMPTZ") == "UTC_DATETIME"
        assert map_firebolt_type_to_fivetran("date") == "NAIVE_DATE"
        assert map_firebolt_type_to_fivetran("timestamp") == "NAIVE_DATETIME"
        assert map_firebolt_type_to_fivetran("timestamptz") == "UTC_DATETIME"

    def test_binary_type(self) -> None:
        """Test mapping of binary type."""
        assert map_firebolt_type_to_fivetran("BYTEA") == "BINARY"
        assert map_firebolt_type_to_fivetran("bytea") == "BINARY"

    def test_spatial_type(self) -> None:
        """Test mapping of spatial type to STRING."""
        assert map_firebolt_type_to_fivetran("GEOGRAPHY") == "STRING"
        assert map_firebolt_type_to_fivetran("geography") == "STRING"

    def test_array_types(self) -> None:
        """Test mapping of array types."""
        assert map_firebolt_type_to_fivetran("ARRAY(INT)") == "JSON"
        assert map_firebolt_type_to_fivetran("ARRAY(STRING)") == "JSON"
        assert map_firebolt_type_to_fivetran("array(int)") == "JSON"

    def test_struct_type(self) -> None:
        """Test mapping of struct type to JSON."""
        assert map_firebolt_type_to_fivetran("STRUCT(a INT, b STRING)") == "JSON"
        assert map_firebolt_type_to_fivetran("struct(a int, b string)") == "JSON"

    def test_parameterized_types(self, expected_decimal) -> None:
        """Test mapping of parameterized types."""
        assert map_firebolt_type_to_fivetran("FLOAT(25)") == "FLOAT"
        assert map_firebolt_type_to_fivetran("FLOAT(53)") == "FLOAT"
        assert map_firebolt_type_to_fivetran("DECIMAL(10,2)") == expected_decimal

    def test_unknown_types(self) -> None:
        """Test mapping of unknown types defaults to STRING."""
        assert map_firebolt_type_to_fivetran("UNKNOWN_TYPE") == "STRING"
        assert map_firebolt_type_to_fivetran("CUSTOM_TYPE") == "STRING"
        assert map_firebolt_type_to_fivetran("") == "STRING"

    def test_case_insensitive(self) -> None:
        """Test that type mapping is case insensitive."""
        assert map_firebolt_type_to_fivetran("Int") == "INT"
        assert map_firebolt_type_to_fivetran("BiGiNt") == "LONG"
        assert map_firebolt_type_to_fivetran("VarChar") == "STRING"
        assert map_firebolt_type_to_fivetran("TimeStamp") == "NAIVE_DATETIME"
        assert map_firebolt_type_to_fivetran("TimeStampTZ") == "UTC_DATETIME"
