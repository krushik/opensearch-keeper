"""
Tests for the configuration module.
"""

import os
import tempfile
import pytest
import yaml

from opensearch_keeper.config import Config


@pytest.fixture
def sample_config():
    """Create a sample configuration file."""
    config_data = {
        "environments": {
            "qa": {
                "host": "opensearch-qa.example.com",
                "port": 443,
                "use_ssl": True,
                "verify_certs": True,
            },
            "prod": {
                "host": "opensearch-prod.example.com",
                "port": 443,
                "use_ssl": True,
                "verify_certs": True,
            },
        },
        "storage_dir": "./dump",
        "ignore_patterns": [".opendistro_security", ".kibana*"],
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml.dump(config_data, f)
        config_path = f.name

    yield config_path

    # Cleanup
    os.unlink(config_path)


def test_load_config(sample_config):
    """Test loading configuration from a file."""
    config = Config(sample_config)
    assert config.config_path == sample_config
    assert "environments" in config.config_data
    assert "qa" in config.config_data["environments"]
    assert "prod" in config.config_data["environments"]


def test_get_environment_config(sample_config):
    """Test getting environment configuration."""
    config = Config(sample_config)

    qa_config = config.get_environment_config("qa")
    assert qa_config["host"] == "opensearch-qa.example.com"
    assert qa_config["port"] == 443

    prod_config = config.get_environment_config("prod")
    assert prod_config["host"] == "opensearch-prod.example.com"

    with pytest.raises(ValueError):
        config.get_environment_config("non_existent")


def test_get_storage_dir(sample_config):
    """Test getting storage directory."""
    config = Config(sample_config)
    assert config.get_storage_dir() == "./dump"


def test_get_templates_dir(sample_config):
    """Test getting templates directory."""
    config = Config(sample_config)
    templates_dir = config.get_templates_dir("qa")
    assert templates_dir.endswith("/dump/qa/templates")


def test_get_ism_policies_dir(sample_config):
    """Test getting ISM policies directory."""
    config = Config(sample_config)
    policies_dir = config.get_ism_policies_dir("prod")
    assert policies_dir.endswith("/dump/prod/ism_policies")


def test_get_ignore_patterns(sample_config):
    """Test getting ignore patterns."""
    config = Config(sample_config)
    patterns = config.get_ignore_patterns()
    assert len(patterns) == 2
    assert ".opendistro_security" in patterns
    assert ".kibana*" in patterns


def test_get_available_environments(sample_config):
    """Test getting available environments."""
    config = Config(sample_config)
    environments = config.get_available_environments()
    assert sorted(environments) == ["prod", "qa"]
