"""
Utility functions for opensearch-keeper.
"""

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=log_level, format=log_format, handlers=[logging.StreamHandler(sys.stdout)]
    )


def format_template_list(templates: list, output_format: str = "table") -> str:
    """
    Format a list of templates for display.

    Args:
        templates: List of template dictionaries.
        output_format: Output format ('table', 'json', or 'yaml').

    Returns:
        Formatted string representation of templates.
    """
    if output_format == "json":
        import json

        return json.dumps([t["name"] for t in templates], indent=2)

    elif output_format == "yaml":
        import yaml

        return yaml.dump([t["name"] for t in templates], default_flow_style=False)

    else:  # table format
        if not templates:
            return "No templates found."

        result = "Templates:\n"
        for template in templates:
            result += f"- {template['name']}\n"
        return result
