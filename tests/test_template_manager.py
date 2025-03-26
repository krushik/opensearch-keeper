"""
Tests for the template manager module.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from opensearch_keeper.template_manager import TemplateManager


@pytest.fixture
def mock_opensearch():
    """Create a mock OpenSearch client."""
    with patch("opensearch_keeper.template_manager.OpenSearch") as mock_client:
        # Mock the client instance
        instance = MagicMock()
        mock_client.return_value = instance

        # Mock the indices API
        instance.indices = MagicMock()
        instance.indices.get_index_template.return_value = {
            "index_templates": [
                {
                    "name": "template1",
                    "index_template": {"index_patterns": ["pattern1*"]},
                },
                {
                    "name": "template2",
                    "index_template": {"index_patterns": ["pattern2*"]},
                },
                {"name": ".kibana", "index_template": {"index_patterns": [".kibana*"]}},
            ]
        }

        yield mock_client


@pytest.fixture
def template_manager(mock_opensearch):
    """Create a template manager with a mock client."""
    env_config = {
        "host": "localhost",
        "port": 9200,
        "use_ssl": False,
        "verify_certs": False,
    }

    with tempfile.TemporaryDirectory() as templates_dir:
        ignore_patterns = [".kibana*"]
        manager = TemplateManager(env_config, templates_dir, ignore_patterns)
        yield manager


def test_list_templates(template_manager):
    """Test listing templates."""
    templates = template_manager.list_templates()

    # Should return 2 templates (excluding .kibana)
    assert len(templates) == 2

    # Check template names
    template_names = [t["name"] for t in templates]
    assert "template1" in template_names
    assert "template2" in template_names
    assert ".kibana" not in template_names


def test_list_templates_with_pattern(template_manager):
    """Test listing templates with a pattern."""
    templates = template_manager.list_templates("template1")

    # Should return only template1
    assert len(templates) == 1
    assert templates[0]["name"] == "template1"


def test_save_templates(template_manager):
    """Test saving templates."""
    saved_files = template_manager.save_templates()

    # Should save 2 templates
    assert len(saved_files) == 2

    # Check file names
    file_names = [os.path.basename(f) for f in saved_files]
    assert "template1.yaml" in file_names
    assert "template2.yaml" in file_names


def test_publish_template(template_manager):
    """Test publishing a template."""
    # Create a temporary template file with the new index template format
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("index_patterns: [test*]\n")
        template_file = f.name
        template_name = template_file.split(".")[0]
    try:
        success = template_manager.publish_template(template_name, template_file)

        # Check that the template was published
        assert success is True

        # Verify that put_template was called
        template_manager.client.indices.put_index_template.assert_called_once()
    finally:
        os.unlink(template_file)


def test_delete_template(template_manager):
    """Test deleting a template."""
    success = template_manager.delete_template("template1")

    # Check that the template was deleted
    assert success is True

    # Verify that delete_template was called
    template_manager.client.indices.delete_index_template.assert_called_once_with(name="template1")
