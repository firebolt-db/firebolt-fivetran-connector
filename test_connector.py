import json
import os

from connector import schema, validate_configuration


def test_connector() -> bool:
    """Test the connector with real credentials"""

    client_id = os.environ.get("id")
    client_secret = os.environ.get("secret")
    account_name = os.environ.get("account_name", "automation")
    database = os.environ.get("database", "petro_test")
    engine_name = os.environ.get("engine_name", "petro_test")
    api_endpoint = os.environ.get("api_endpoint", "https://api.staging.firebolt.io")

    if not client_id or not client_secret:
        print("ERROR: Missing credentials in environment variables 'id' and 'secret'")
        return False

    config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "account_name": account_name,
        "database": database,
        "engine_name": engine_name,
        "api_endpoint": api_endpoint,
    }

    try:
        print("Testing configuration validation...")
        validate_configuration(config)
        print("✓ Configuration validation: PASSED")

        print("\nTesting schema discovery...")
        tables = schema(config)
        print(f"✓ Schema discovery: PASSED - Found {len(tables)} tables")

        for i, table in enumerate(tables[:3]):
            print(f"  Table {i+1}: {table['table']} ({len(table['columns'])} columns)")
            cols = list(table["columns"].items())[:3]
            for col_name, col_type in cols:
                print(f"    - {col_name}: {col_type}")

        if len(tables) > 3:
            print(f"  ... and {len(tables) - 3} more tables")

        print(f"\n✓ Connector test completed successfully!")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_connector()
