"""
Tests for the ISM policy manager module.
"""

import os
import tempfile
import pytest
import yaml
from unittest.mock import MagicMock, patch

from opensearchpy.exceptions import NotFoundError
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


def test_publish_policy_create(policy_manager):
    """Test publishing a new ISM policy."""
    # Mock get_policy to raise NotFoundError (policy doesn't exist)
    policy_manager.ism_client.get_policy.side_effect = NotFoundError(404, "Not Found", {})

    policy_name = "new_policy"
    policy_content = {
        "policy": {
            "policy_id": policy_name,
            "default_state": "hot",
            "states": [{"name": "hot", "actions": [], "transitions": []}],
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(policy_content["policy"], f)
        policy_file = f.name

    try:
        success = policy_manager.publish_policy(policy_name, policy_file)

        assert success is True
        policy_manager.ism_client.get_policy.assert_called_once_with(policy=policy_name)
        # Verify put_policy called without sequence numbers
        policy_manager.ism_client.put_policy.assert_called_once_with(
            policy=policy_name, body={"policy": policy_content["policy"]}
        )
    finally:
        os.unlink(policy_file)


def test_publish_policy_update(policy_manager):
    """Test updating an existing ISM policy."""
    policy_name = "existing_policy"
    existing_seq_no = 10
    existing_primary_term = 1

    # Mock get_policy to return an existing policy
    policy_manager.ism_client.get_policy.return_value = {
        "_id": policy_name,
        "_version": 2,
        "_seq_no": existing_seq_no,
        "_primary_term": existing_primary_term,
        "policy": {
            "policy_id": policy_name,
            "description": "Old description",
            # ... other fields
        },
    }

    updated_policy_content = {
        "policy": {
            "policy_id": policy_name,
            "description": "Updated description",
            "default_state": "warm",
            "states": [{"name": "warm", "actions": [], "transitions": []}],
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(updated_policy_content["policy"], f)
        policy_file = f.name

    try:
        success = policy_manager.publish_policy(policy_name, policy_file)

        assert success is True
        policy_manager.ism_client.get_policy.assert_called_once_with(policy=policy_name)
        # Verify put_policy called WITH sequence numbers in params
        expected_params = {
            "if_seq_no": existing_seq_no,
            "if_primary_term": existing_primary_term,
        }
        policy_manager.ism_client.put_policy.assert_called_once_with(
            policy=policy_name,
            body={"policy": updated_policy_content["policy"]},
            params=expected_params,
        )
    finally:
        os.unlink(policy_file)


def test_delete_policy(policy_manager):
    """Test deleting an ISM policy."""
    success = policy_manager.delete_policy("policy1")

    # Check that the policy was deleted
    assert success is True

    # Verify that the delete_policy method was called with the correct arguments
    policy_manager.ism_client.delete_policy.assert_called_once_with(policy="policy1")
