"""
Configuration module for opensearch-keeper.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATHS = [
    "./config.yaml",
    "~/.opensearch-keeper/config.yaml",
    "/etc/opensearch-keeper/config.yaml",
]


class Config:
    """Configuration handler for opensearch-keeper."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration.

        :param config_path: Path to the configuration file. If None, default paths will be checked.
        """
        self.config_data: dict[str, Any] = {}
        self.config_path: Optional[str] = None

        # Try to load config from specified path or default paths
        if config_path:
            self._load_config(config_path)
        else:
            for path in DEFAULT_CONFIG_PATHS:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    self._load_config(expanded_path)
                    break
            else:
                logger.warning(
                    f"No configuration file found in default paths: {DEFAULT_CONFIG_PATHS}"
                )

    def _load_config(self, config_path: str) -> None:
        """Load configuration from a YAML file.

        :param config_path: Path to the configuration file.
        """
        try:
            with open(config_path, "r") as f:
                self.config_data = yaml.safe_load(f)
            if self.config_data is None:
                self.config_data = {}
            self.config_path = config_path
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise

    def get_environment_config(self, env_name: str) -> Dict[str, Any]:
        """Get configuration for a specific environment.

        :param env_name: Name of the environment (e.g., 'qa', 'prod').
        :return: Dictionary with environment configuration.
        :raises ValueError: If the environment is not defined in the configuration.
        """
        environments = self.config_data.get("environments", {})
        if env_name not in environments:
            raise ValueError(
                f"Environment '{env_name}' not found in configuration. "
                f"Available environments: {list(environments.keys())}"
            )
        return environments[env_name]

    def get_storage_dir(self) -> str:
        """Get the base storage directory for all artifacts.

        :return: Path to the storage directory.
        """
        storage_dir = self.config_data.get("storage_dir", "./dump")
        # Create the directory if it doesn't exist
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        return storage_dir

    def get_templates_dir(self, env_name: str) -> str:
        """Get the directory where templates should be saved for a specific environment.

        :param env_name: Name of the environment.
        :return: Path to the templates directory.
        """
        storage_dir = self.get_storage_dir()
        templates_dir = os.path.join(storage_dir, env_name, "templates")
        # Create the directory if it doesn't exist
        Path(templates_dir).mkdir(parents=True, exist_ok=True)
        return templates_dir

    def get_ism_policies_dir(self, env_name: str) -> str:
        """Get the directory where ISM policies should be saved for a specific environment.

        :param env_name: Name of the environment.
        :return: Path to the ISM policies directory.
        """
        storage_dir = self.get_storage_dir()
        policies_dir = os.path.join(storage_dir, env_name, "ism_policies")
        # Create the directory if it doesn't exist
        Path(policies_dir).mkdir(parents=True, exist_ok=True)
        return policies_dir

    def get_ignore_patterns(self) -> List[str]:
        """Get the list of template name patterns to ignore.

        :return: List of patterns to ignore.
        """
        return self.config_data.get("ignore_patterns", [])

    def get_available_environments(self) -> List[str]:
        """Get a list of available environment names.

        :return: List of environment names.
        """
        return list(self.config_data.get("environments", {}).keys())
