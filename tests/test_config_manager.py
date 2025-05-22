"""Tests for the configuration manager module."""
import pytest
import tempfile
import os
import yaml
from config.config_manager import ConfigManager

def test_load_config(test_config):
    """Test loading configuration from file."""
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        yaml.safe_dump(test_config, f)
    
    try:
        # Test config loading
        config_manager = ConfigManager(f.name)
        
        # Verify config values
        assert config_manager.discord_token == 'test-token'
        assert config_manager.application_id == 123456789
        assert config_manager.channel_id == 987654321
        assert config_manager.timezone == 'Europe/Berlin'
    finally:
        os.unlink(f.name)

def test_load_config_missing_file():
    """Test loading configuration from non-existent file."""
    with pytest.raises(FileNotFoundError):
        ConfigManager('nonexistent.yaml')

def test_load_config_invalid_yaml():
    """Test loading configuration from invalid YAML file."""
    # Create temporary file with invalid YAML
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        f.write('invalid: yaml: content:')
    
    try:
        with pytest.raises(yaml.YAMLError):
            ConfigManager(f.name)
    finally:
        os.unlink(f.name)