"""
ISM policy management module for OpenSearch.
"""

import fnmatch
import logging
import os
from typing import Dict, Any, List, Optional

import yaml
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from opensearchpy.plugins.index_management import IndexManagementClient

from opensearch_keeper.auth import get_connection_params

logger = logging.getLogger(__name__)


class ISMPolicyManager:
    """Manager for OpenSearch Index State Management policies."""

    def __init__(self, env_config: Dict[str, Any], policies_dir: str, ignore_patterns: List[str]):
        """Initialize the ISM policy manager.

        :param env_config: Environment configuration.
        :param policies_dir: Directory where ISM policies will be saved.
        :param ignore_patterns: List of policy name patterns to ignore.
        """
        self.env_config = env_config
        self.policies_dir = policies_dir
        self.ignore_patterns = ignore_patterns
        self.client = self._create_client()
        self.ism_client = IndexManagementClient(self.client)

    def _create_client(self) -> OpenSearch:
        """Create an OpenSearch client.

        :return: OpenSearch client.
        """
        connection_params = get_connection_params(self.env_config)
        try:
            client = OpenSearch(**connection_params)
            # Test the connection
            client.info()
            logger.info(
                f"Connected to OpenSearch at {self.env_config['host']}:{self.env_config['port']}"
            )
            return client
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            raise

    def _should_ignore(self, policy_name: str) -> bool:
        """Check if a policy should be ignored based on ignore patterns.

        :param policy_name: Name of the policy.
        :return: True if the policy should be ignored, False otherwise.
        """
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(policy_name, pattern):
                return True
        return False

    def list_policies(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """List ISM policies in OpenSearch, cleaning up metadata.

        Retrieves policies, filters them based on an optional pattern and
        internal ignore list, and cleans up metadata fields before returning.

        :param pattern: Optional fnmatch pattern to filter policies by name.
        :return: A list of dictionaries, where each dictionary represents a policy
                 and contains:
                 - 'name': The name of the policy (str).
                 - 'policy': The cleaned policy definition (Dict[str, Any]).
                 - 'last_updated_time': The top-level update time in seconds (int)
        :raises Exception: If the API call fails or the response format is invalid.
        :raises ValueError: If the response structure from the API is unexpected.
        """
        try:
            # Get all policies using the Index Management plugin client
            response = self.ism_client.get_policy()
            policies: List[Dict[str, Any]] = []
            raw_policies = response.get("policies")

            # Validate the structure of the response
            if not isinstance(raw_policies, list):
                logger.error(
                    "Failed to list ISM policies: 'policies' key missing or not a list in response."
                )
                raise ValueError("Invalid response format from get_policy API")

            for policy_item in raw_policies:
                # Basic validation of the policy item structure
                if not isinstance(policy_item, dict) or "policy" not in policy_item:
                    logger.error(f"Skipping invalid policy item format: {policy_item}")
                    continue
                policy_data = policy_item.get("policy")
                if not isinstance(policy_data, dict):
                    logger.error(
                        f"Skipping policy item with invalid 'policy' data type: {policy_item}"
                    )
                    continue
                policy_name = policy_data.pop("policy_id", policy_item.get("_id"))

                # filtering
                if self._should_ignore(policy_name):
                    continue
                if pattern and not fnmatch.fnmatch(policy_name, pattern):
                    continue

                # drop milliseconds to get standard unix timestamp
                last_updated_time = policy_data.get("last_updated_time", 0) // 1000

                # cleanup
                policy_data.pop("last_updated_time", None)
                policy_data.pop("schema_version", None)
                ism_template_list = policy_data.get("ism_template")
                if isinstance(ism_template_list, list):
                    for ism_template_item in ism_template_list:
                        if isinstance(ism_template_item, dict):
                            ism_template_item.pop("last_updated_time", None)

                policies.append(
                    {
                        "name": policy_name,
                        "policy": policy_data,  # policy_data is now cleaned up from metadata
                        "last_updated_time": last_updated_time,  # top-level, converted to seconds
                    }
                )

            return policies
        except Exception as e:
            logger.error(f"Failed to list ISM policies: {e}")
            raise

    def save_policies(self, pattern: Optional[str] = None) -> List[str]:
        """Save ISM policies from OpenSearch to local files.

        :param pattern: Optional pattern to filter policies.
        :return: List of saved policy file paths.
        """
        policies = self.list_policies(pattern)
        saved_files = []

        for policy_info in policies:
            name = policy_info["name"]
            policy = policy_info["policy"]
            saved_files.append(self.save_policy(name, policy))

        return saved_files

    def save_policy(self, name, policy) -> str:
        """Save ISM policy to local files.

        :param name: Name of the policy.
        :param policy: Policy data to save.
        :return: Path to the policy file.
        """
        # Create file path
        file_path = os.path.join(self.policies_dir, f"{name}.yaml")
        try:
            with open(file_path, "w") as f:
                yaml.dump(policy, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved ISM policy '{name}' to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save ISM policy '{name}': {e}")
        return file_path

    def publish_policy(self, policy_name: str, policy_file: str) -> bool:
        """Publish an ISM policy from a local file to OpenSearch.

        :param policy_name: Name of the policy.
        :param policy_file: Path to the policy file.
        :return: True if the policy was published successfully, False otherwise.
        """
        try:
            with open(policy_file, "r") as f:
                policy_data = yaml.safe_load(f)

            if not policy_data or not isinstance(policy_data, dict):
                logger.error(f"Invalid policy file format: {policy_file}")
                return False

            # Check if the policy already exists to get sequence numbers for update
            seq_no = None
            primary_term = None
            try:
                existing_policy = self.ism_client.get_policy(policy=policy_name)
                seq_no = existing_policy.get("_seq_no")
                primary_term = existing_policy.get("_primary_term")
                logger.debug(
                    f"Policy '{policy_name}' found. Using seq_no={seq_no}, primary_term={primary_term} for update."
                )
            except NotFoundError:
                logger.debug(f"Policy '{policy_name}' not found. Creating new policy.")
            except Exception as e:
                logger.warning(
                    f"Failed to get existing policy '{policy_name}', proceeding without sequence numbers: {e}"
                )
                # Decide if we should proceed or fail here. Proceeding might overwrite changes.
                # For now, let's proceed as if it's a create operation.

            # Publish the policy using the Index Management client
            if seq_no is not None and primary_term is not None:
                params = {"if_seq_no": seq_no, "if_primary_term": primary_term}
                self.ism_client.put_policy(
                    policy=policy_name, body={"policy": policy_data}, params=params
                )
                logger.info(f"Updated ISM policy '{policy_name}' in OpenSearch.")
            else:
                self.ism_client.put_policy(policy=policy_name, body={"policy": policy_data})
                logger.info(f"Created ISM policy '{policy_name}' in OpenSearch.")

        except Exception as e:
            logger.error(f"Failed to publish ISM policy '{policy_name}': {e}")
            return False
        return True

    def publish_policies(self, pattern: Optional[str] = None) -> Dict[str, bool]:
        """Publish ISM policies from local files to OpenSearch.

        :param pattern: Optional pattern to filter policy files.
        :return: Dictionary mapping policy names to success status.
        """
        results = {}
        # Get all policy files
        for file in os.listdir(self.policies_dir):
            if file.endswith((".yaml", ".yml")):
                # Extract policy name from filename
                policy_name = file.split(".")[0]
                if pattern and not fnmatch.fnmatch(policy_name, pattern):
                    continue
                policy_file = os.path.join(self.policies_dir, file)
                success = self.publish_policy(policy_name, policy_file)
                results[policy_name] = success

        return results

    def delete_policy(self, policy_name: str) -> bool:
        """Delete an ISM policy from OpenSearch.

        :param policy_name: Name of the policy to delete.
        :return: True if the policy was deleted, False otherwise.
        """
        try:
            self.ism_client.delete_policy(policy=policy_name)
            logger.info(f"Deleted ISM policy '{policy_name}' from OpenSearch")
            return True
        except Exception as e:
            logger.error(f"Failed to delete ISM policy '{policy_name}': {e}")
            return False

    def diff_policy(self, policy_name: str) -> Optional[Dict[str, Any]]:
        """Compare local policy file with the one in OpenSearch.

        :param policy_name: Name of the policy to compare.
        :return: Dictionary with diff information or None if policy doesn't exist remotely.
        """
        from deepdiff import DeepDiff

        # Construct file path for local policy
        policy_file = os.path.join(self.policies_dir, f"{policy_name}.yaml")

        if not os.path.exists(policy_file):
            logger.error(f"Local policy file not found: {policy_file}")
            return None

        # Load local policy
        try:
            with open(policy_file, "r") as f:
                local_policy = yaml.safe_load(f)

            if not local_policy or not isinstance(local_policy, dict):
                logger.error(f"Invalid local policy file format: {policy_file}")
                return None
        except Exception as e:
            logger.error(f"Failed to load local policy file '{policy_file}': {e}")
            return None

        # Try to get remote policy
        try:
            remote_response = self.ism_client.get_policy(policy=policy_name)
            if not remote_response or "policy" not in remote_response:
                logger.error(f"Invalid response format from get_policy API for '{policy_name}'")
                return None

            remote_policy = remote_response.get("policy", {})

            # Clean metadata from remote policy for comparison
            remote_policy.pop("last_updated_time", None)
            remote_policy.pop("schema_version", None)
            remote_policy.pop("policy_id", None)
            ism_template_list = remote_policy.get("ism_template")
            if isinstance(ism_template_list, list):
                for ism_template_item in ism_template_list:
                    if isinstance(ism_template_item, dict):
                        ism_template_item.pop("last_updated_time", None)

            # Get the diff
            diff = DeepDiff(remote_policy, local_policy, ignore_order=True)

            if not diff:
                return {"has_changes": False}

            return {
                "has_changes": True,
                "diff": diff,
                "remote_policy": remote_policy,
                "local_policy": local_policy,
                "seq_no": remote_response.get("_seq_no"),
                "primary_term": remote_response.get("_primary_term"),
            }

        except NotFoundError:
            # Policy doesn't exist in OpenSearch
            return None
        except Exception as e:
            logger.error(f"Failed to diff policy '{policy_name}': {e}")
            raise
