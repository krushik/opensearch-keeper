"""
Tests for the ISM policy manager module.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, ANY

from opensearch_keeper.ism_policy_manager import ISMPolicyManager


@pytest.fixture
def mock_opensearch():
    """Create a mock OpenSearch client."""
    with patch("opensearch_keeper.ism_policy_manager.OpenSearch") as mock_client:
        # Mock the client instance
        instance = MagicMock()
        mock_client.return_value = instance

        # Mock the IndexManagementClient
        with patch(
            "opensearch_keeper.ism_policy_manager.IndexManagementClient"
        ) as mock_ism_client_class:
            mock_ism_client = MagicMock()
            mock_ism_client_class.return_value = mock_ism_client

            # Mock the get_policy method
            mock_ism_client.get_policy.return_value = {
                "policies": [
                    {
                        "policy": {
                            "policy_id": "policy1",
                            "description": "Test policy 1",
                            "default_state": "hot",
                            "states": [{"name": "hot", "actions": [], "transitions": []}],
                            "last_updated_time": 1727172147906,
                        },
                        "policy_metadata": {},
                    },
                    {
                        "policy": {
                            "policy_id": "policy2",
                            "description": "Test policy 2",
                            "default_state": "hot",
                            "states": [{"name": "hot", "actions": [], "transitions": []}],
                            "last_updated_time": 1727172147906,
                        },
                        "policy_metadata": {},
                    },
                    {
                        "policy": {
                            "policy_id": ".internal_policy",
                            "description": "Internal policy",
                            "default_state": "hot",
                            "states": [{"name": "hot", "actions": [], "transitions": []}],
                            "last_updated_time": 1727172147906,
                        },
                        "policy_metadata": {},
                    },
                ]
            }

            yield mock_client


@pytest.fixture
def policy_manager(mock_opensearch):
    """Create a policy manager with a mock client."""
    env_config = {
        "host": "localhost",
        "port": 9200,
        "use_ssl": False,
        "verify_certs": False,
    }

    with tempfile.TemporaryDirectory() as policies_dir:
        ignore_patterns = [".internal*"]
        manager = ISMPolicyManager(env_config, policies_dir, ignore_patterns)
        yield manager


def test_list_policies(policy_manager):
    """Test listing ISM policies."""
    policies = policy_manager.list_policies()

    # Should return 2 policies (excluding .internal_policy)
    assert len(policies) == 2

    # Check policy names
    policy_names = [p["name"] for p in policies]
    assert "policy1" in policy_names
    assert "policy2" in policy_names
    assert ".internal_policy" not in policy_names


def test_list_policies_with_pattern(policy_manager):
    """Test listing ISM policies with a pattern."""
    policies = policy_manager.list_policies("policy1")

    # Should return only policy1
    assert len(policies) == 1
    assert policies[0]["name"] == "policy1"


def test_save_policies(policy_manager):
    """Test saving ISM policies."""
    saved_files = policy_manager.save_policies()

    # Should save 2 policies
    assert len(saved_files) == 2

    # Check file names
    file_names = [os.path.basename(f) for f in saved_files]
    assert "policy1.yaml" in file_names
    assert "policy2.yaml" in file_names


def test_publish_policy(policy_manager):
    """Test publishing an ISM policy."""
    # Create a temporary policy file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "policy_id: test_policy\ndefault_state: hot\nstates:\n- name: hot\n  actions: []\n  transitions: []\n"
        )
        policy_file = f.name
        policy_name = policy_file.split(".")[0]
    try:
        success = policy_manager.publish_policy(policy_name, policy_file)

        # Check that the policy was published
        assert success is True

        # Verify that the put_policy method was called with the correct arguments
        policy_manager.ism_client.put_policy.assert_called_with(policy=policy_name, body=ANY)
    finally:
        os.unlink(policy_file)


def test_delete_policy(policy_manager):
    """Test deleting an ISM policy."""
    success = policy_manager.delete_policy("policy1")

    # Check that the policy was deleted
    assert success is True

    # Verify that the delete_policy method was called with the correct arguments
    policy_manager.ism_client.delete_policy.assert_called_with(policy="policy1")
