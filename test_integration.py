import json
import os
import pytest
from unittest.mock import patch
from connector import schema, update, validate_configuration


class TestFireboltFivetranConnectorIntegration:
    
    @pytest.fixture
    def test_configuration(self):
        config_file = "test_configuration.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "client_id": os.environ.get("SERVICE_ID"),
                "client_secret": os.environ.get("SERVICE_SECRET"),
                "account_name": os.environ.get("ACCOUNT_NAME"),
                "database": os.environ.get("DATABASE_NAME"),
                "engine_name": os.environ.get("ENGINE_NAME"),
                "api_endpoint": os.environ.get("API_ENDPOINT", "https://api.staging.firebolt.io")
            }
    
    def test_configuration_validation(self, test_configuration):
        validate_configuration(test_configuration)
        
        incomplete_config = test_configuration.copy()
        del incomplete_config["client_id"]
        
        with pytest.raises(ValueError, match="Missing required configuration value: client_id"):
            validate_configuration(incomplete_config)
    
    def test_schema_discovery(self, test_configuration):
        discovered_schema = schema(test_configuration)
        
        assert isinstance(discovered_schema, list)
        
        if discovered_schema:
            for table_schema in discovered_schema:
                assert "table" in table_schema
                assert "primary_key" in table_schema
                assert "columns" in table_schema
                assert isinstance(table_schema["columns"], dict)
                
                valid_fivetran_types = {
                    "BOOLEAN", "SHORT", "INT", "LONG", "DECIMAL", "FLOAT", 
                    "DOUBLE", "NAIVE_DATE", "NAIVE_DATETIME", "UTC_DATETIME", 
                    "BINARY", "XML", "STRING", "JSON"
                }
                
                for column_name, column_type in table_schema["columns"].items():
                    if isinstance(column_type, dict):
                        assert column_type.get("type") in valid_fivetran_types
                    else:
                        assert column_type in valid_fivetran_types
    
    def test_data_sync_basic(self, test_configuration):
        initial_state = {}
        
        operations = list(update(test_configuration, initial_state))
        
        assert len(operations) > 0
        
        last_operation = operations[-1]
        assert hasattr(last_operation, 'type')
        
        if hasattr(last_operation, 'state'):
            checkpoint_state = last_operation.state
            assert "last_sync_time" in checkpoint_state
            assert "table_cursors" in checkpoint_state
    
    def test_data_sync_incremental(self, test_configuration):
        initial_state = {}
        initial_operations = list(update(test_configuration, initial_state))
        
        checkpoint_state = None
        for op in initial_operations:
            if hasattr(op, 'state'):
                checkpoint_state = op.state
                break
        
        assert checkpoint_state is not None, "No checkpoint found in initial sync"
        
        incremental_operations = list(update(test_configuration, checkpoint_state))
        
        assert len(incremental_operations) > 0
        
        final_checkpoint = None
        for op in incremental_operations:
            if hasattr(op, 'state'):
                final_checkpoint = op.state
        
        assert final_checkpoint is not None
        assert "last_sync_time" in final_checkpoint
        assert "table_cursors" in final_checkpoint
    
    def test_error_handling_invalid_credentials(self):
        invalid_config = {
            "client_id": "invalid_client_id",
            "client_secret": "invalid_client_secret",
            "account_name": "invalid_account",
            "database": "invalid_database",
            "engine_name": "invalid_engine"
        }
        
        with pytest.raises(Exception):
            schema(invalid_config)
        
        with pytest.raises(Exception):
            list(update(invalid_config, {}))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
