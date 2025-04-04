"""
Template management module for OpenSearch.
"""

import fnmatch
import logging
import os
from typing import Dict, Any, List, Optional

import yaml
from opensearchpy import OpenSearch

from opensearch_keeper.auth import get_connection_params

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manager for OpenSearch index templates."""

    def __init__(self, env_config: Dict[str, Any], templates_dir: str, ignore_patterns: List[str]):
        """Initialize the template manager.

        :param env_config: Environment configuration.
        :param templates_dir: Directory where templates will be saved.
        :param ignore_patterns: List of template name patterns to ignore.
        """
        self.env_config = env_config
        self.templates_dir = templates_dir
        self.ignore_patterns = ignore_patterns
        self.client = self._create_client()

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

    def _should_ignore(self, template_name: str) -> bool:
        """Check if a template should be ignored based on ignore patterns.

        :param template_name: Name of the template.
        :return: True if the template should be ignored, False otherwise.
        """
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(template_name, pattern):
                return True
        return False

    def list_templates(self, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """List templates in OpenSearch.

        :param pattern: Optional pattern to filter templates.
        :return: List of templates.
        """
        try:
            # Get all templates using the new index template API
            response = self.client.indices.get_index_template(name="*")

            # Filter templates
            templates = []

            # The new API response is different - it contains an 'index_templates' array
            # Each item has 'name' and 'index_template' fields
            for template_item in response["index_templates"]:
                name = template_item["name"]
                template = template_item["index_template"]

                if self._should_ignore(name):
                    continue
                if pattern and not fnmatch.fnmatch(name, pattern):
                    continue
                templates.append({"name": name, "template": template})
            return templates
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            raise

    def save_templates(self, pattern: Optional[str] = None) -> List[str]:
        """Save templates from OpenSearch to local files.

        :param pattern: Optional pattern to filter templates.
        :return: List of saved template file paths.
        """
        templates = self.list_templates(pattern)
        saved_files = []

        for template_info in templates:
            name = template_info["name"]
            template = template_info["template"]

            # Create file path
            file_path = os.path.join(self.templates_dir, f"{name}.yaml")

            try:
                with open(file_path, "w") as f:
                    yaml.dump(template, f, default_flow_style=False)
                logger.info(f"Saved template '{name}' to {file_path}")
                saved_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to save template '{name}': {e}")

        return saved_files

    def publish_template(self, template_name: str, template_file: str) -> bool:
        """Publish a template from a local file to OpenSearch.

        :param template_name: Name of the template
        :param template_file: Path to the template file.
        :return: True if the template was published successfully, False otherwise.
        """
        try:
            with open(template_file, "r") as f:
                template_data = yaml.safe_load(f)

            if not template_data or not isinstance(template_data, dict):
                logger.error(f"Invalid template file format: {template_file}")
                return False

            # The new API expects the body to be structured differently
            # Ensure the content is formatted correctly for the new API
            if "index_patterns" not in template_data:
                logger.error(f"invalid template format for '{template_name}'. skipping...")
                return False

            # Publish the template using the new index template API
            self.client.indices.put_index_template(name=template_name, body=template_data)
            logger.info(f"Published template '{template_name}' to OpenSearch")
            return True
        except Exception as e:
            logger.error(f"Failed to publish template '{template_name}': {e}")
            return False

    def publish_templates(self, pattern: Optional[str] = None) -> Dict[str, bool]:
        """Publish templates from local files to OpenSearch.

        :param pattern: Optional pattern to filter template files.
        :return: Dictionary mapping template names to success status.
        """
        results = {}
        # Get all template files
        for file in os.listdir(self.templates_dir):
            if file.endswith((".yaml", ".yml")):
                # Extract template name from filename
                template_name = file.split(".")[0]
                if pattern and not fnmatch.fnmatch(template_name, pattern):
                    continue
                template_file = os.path.join(self.templates_dir, file)
                success = self.publish_template(template_name, template_file)
                results[template_name] = success

        return results

    def delete_template(self, template_name: str) -> bool:
        """Delete a template from OpenSearch.

        :param template_name: Name of the template to delete.
        :return: True if the template was deleted, False otherwise.
        """
        try:
            self.client.indices.delete_index_template(name=template_name)
            logger.info(f"Deleted template '{template_name}' from OpenSearch")
            return True
        except Exception as e:
            logger.error(f"Failed to delete template '{template_name}': {e}")
            return False
