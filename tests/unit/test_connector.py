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

    def test_integer_types(self) -> None:
        """Test mapping of integer types."""
        assert map_firebolt_type_to_fivetran("INT") == "INT"
        assert map_firebolt_type_to_fivetran("INTEGER") == "INT"
        assert map_firebolt_type_to_fivetran("int") == "INT"
        assert map_firebolt_type_to_fivetran("integer") == "INT"

    def test_long_types(self) -> None:
        """Test mapping of long/bigint types."""
        assert map_firebolt_type_to_fivetran("BIGINT") == "LONG"
        assert map_firebolt_type_to_fivetran("LONG") == "LONG"
        assert map_firebolt_type_to_fivetran("bigint") == "LONG"
        assert map_firebolt_type_to_fivetran("long") == "LONG"

    def test_float_types(self) -> None:
        """Test mapping of float/double types."""
        assert map_firebolt_type_to_fivetran("FLOAT") == "FLOAT"
        assert map_firebolt_type_to_fivetran("DOUBLE") == "DOUBLE"
        assert map_firebolt_type_to_fivetran("float") == "FLOAT"
        assert map_firebolt_type_to_fivetran("double") == "DOUBLE"

    def test_decimal_types(self) -> None:
        """Test mapping of decimal/numeric types."""
        assert map_firebolt_type_to_fivetran("DECIMAL") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("NUMERIC") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("decimal") == "DECIMAL"
        assert map_firebolt_type_to_fivetran("numeric") == "DECIMAL"

    def test_string_types(self) -> None:
        """Test mapping of string types."""
        assert map_firebolt_type_to_fivetran("TEXT") == "STRING"
        assert map_firebolt_type_to_fivetran("STRING") == "STRING"
        assert map_firebolt_type_to_fivetran("VARCHAR") == "STRING"
        assert map_firebolt_type_to_fivetran("text") == "STRING"
        assert map_firebolt_type_to_fivetran("string") == "STRING"
        assert map_firebolt_type_to_fivetran("varchar") == "STRING"

    def test_boolean_type(self) -> None:
        """Test mapping of boolean type."""
        assert map_firebolt_type_to_fivetran("BOOLEAN") == "BOOLEAN"
        assert map_firebolt_type_to_fivetran("boolean") == "BOOLEAN"

    def test_date_types(self) -> None:
        """Test mapping of date/timestamp types."""
        assert map_firebolt_type_to_fivetran("DATE") == "NAIVE_DATE"
        assert map_firebolt_type_to_fivetran("TIMESTAMP") == "NAIVE_DATETIME"
        assert map_firebolt_type_to_fivetran("TIMESTAMPTZ") == "NAIVE_DATETIME"
        assert map_firebolt_type_to_fivetran("date") == "NAIVE_DATE"
        assert map_firebolt_type_to_fivetran("timestamp") == "NAIVE_DATETIME"
        assert map_firebolt_type_to_fivetran("timestamptz") == "NAIVE_DATETIME"

    def test_array_types(self) -> None:
        """Test mapping of array types."""
        assert map_firebolt_type_to_fivetran("ARRAY(INT)") == "JSON"
        assert map_firebolt_type_to_fivetran("ARRAY(STRING)") == "JSON"
        assert map_firebolt_type_to_fivetran("array(int)") == "JSON"
        assert map_firebolt_type_to_fivetran("ARRAY_OF_STRINGS") == "JSON"

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
