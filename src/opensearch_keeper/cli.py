"""
Command-line interface for opensearch-keeper.
"""

import datetime
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from opensearch_keeper.config import Config
from opensearch_keeper.template_manager import TemplateManager
from opensearch_keeper.ism_policy_manager import ISMPolicyManager
from opensearch_keeper.utils import setup_logging, format_template_list

logger = logging.getLogger(__name__)

# Create Typer app
app = typer.Typer(help="Manage OpenSearch index templates and ISM policies.")
templates_app = typer.Typer(help="Manage OpenSearch index templates.")
ism_policies_app = typer.Typer(help="Manage OpenSearch ISM policies.")

# Add subcommands
app.add_typer(templates_app, name="templates")
app.add_typer(ism_policies_app, name="ism-policies")

# Global state for configuration
config_instance = None
console = Console()


def get_config(config_path: Optional[str] = None) -> Config:
    """Get or create a Config instance.

    :param config_path: Path to the configuration file.
    :return: Config instance.
    """
    global config_instance
    if config_instance is None:
        try:
            config_instance = Config(config_path)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    return config_instance


def get_template_manager(config: Config, env: str) -> TemplateManager:
    """Create a template manager for the specified environment.

    :param config: Configuration object.
    :param env: Environment name.
    :return: TemplateManager instance.
    """
    try:
        env_config = config.get_environment_config(env)
        templates_dir = config.get_templates_dir(env)
        ignore_patterns = config.get_ignore_patterns()
        return TemplateManager(env_config, templates_dir, ignore_patterns)
    except Exception as e:
        logger.error(f"Failed to create template manager: {e}")
        sys.exit(1)


def get_ism_policy_manager(config: Config, env: str) -> ISMPolicyManager:
    """Create an ISM policy manager for the specified environment.

    :param config: Configuration object.
    :param env: Environment name.
    :return: ISMPolicyManager instance.
    """
    try:
        env_config = config.get_environment_config(env)
        policies_dir = config.get_ism_policies_dir(env)
        ignore_patterns = config.get_ignore_patterns()
        return ISMPolicyManager(env_config, policies_dir, ignore_patterns)
    except Exception as e:
        logger.error(f"Failed to create ISM policy manager: {e}")
        sys.exit(1)


@app.callback()
def main(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to configuration file."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
):
    """Manage OpenSearch index templates and ISM policies.

    :param config: Path to configuration file.
    :param verbose: Enable verbose logging.
    """
    setup_logging(verbose)
    get_config(config)


@app.command("environments")
def list_environments():
    """List available environments from the configuration."""
    config = get_config()

    try:
        environments = config.get_available_environments()
        if environments:
            table = Table(title="Available Environments")
            table.add_column("Environment")

            for env in environments:
                table.add_row(env)

            console.print(table)
        else:
            typer.echo("No environments configured.")
    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        sys.exit(1)


@app.command("completions")
def install_completions(
    shell: str = typer.Argument(
        ..., help="Shell type (bash, zsh, fish) for which to install completions."
    ),
):
    """Install shell completions.

    :param shell: Shell type (bash, zsh, fish) for which to install completions.
    """
    import subprocess
    from pathlib import Path

    shells = ["bash", "zsh", "fish"]
    if shell not in shells:
        typer.echo(f"Unsupported shell: {shell}. Supported shells: {', '.join(shells)}")
        sys.exit(1)

    try:
        # Create the appropriate completions directory if it doesn't exist
        if shell == "bash":
            completions_dir = Path.home() / ".bash_completion.d"
        elif shell == "zsh":
            completions_dir = Path.home() / ".zsh" / "completions"
        elif shell == "fish":
            completions_dir = Path.home() / ".config" / "fish" / "completions"

        completions_dir.mkdir(parents=True, exist_ok=True)

        # Generate completion script
        completion_file = completions_dir / f"opensearch-keeper.{shell}"

        if shell == "bash":
            command = (
                f"_OPENSEARCH_KEEPER_COMPLETE=bash_source opensearch-keeper > {completion_file}"
            )
        elif shell == "zsh":
            command = (
                f"_OPENSEARCH_KEEPER_COMPLETE=zsh_source opensearch-keeper > {completion_file}"
            )
        elif shell == "fish":
            command = (
                f"_OPENSEARCH_KEEPER_COMPLETE=fish_source opensearch-keeper > {completion_file}"
            )

        subprocess.run(command, shell=True, check=True)

        # Instructions for the user
        if shell == "bash":
            instructions = f"Add this to your ~/.bashrc:\n  source {completion_file}"
        elif shell == "zsh":
            instructions = f"Make sure {completions_dir} is in your fpath in your ~/.zshrc"
        elif shell == "fish":
            instructions = "Completions should work automatically"

        typer.echo(f"Installed {shell} completions to {completion_file}")
        typer.echo(instructions)

    except Exception as e:
        logger.error(f"Failed to install completions: {e}")
        sys.exit(1)


# Template commands
@templates_app.command("list")
def list_templates(
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter templates."
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table, json, yaml).",
        show_choices=True,
        case_sensitive=False,
    ),
):
    """List templates in OpenSearch.

    :param env: Environment to use (qa, prod, etc.).
    :param pattern: Pattern to filter templates.
    :param format: Output format (table, json, yaml).
    """
    config = get_config()
    template_manager = get_template_manager(config, env)

    try:
        templates = template_manager.list_templates(pattern)
        typer.echo(format_template_list(templates, format))
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        sys.exit(1)


@templates_app.command("save")
def save_templates(
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter templates."
    ),
):
    """Save templates from OpenSearch to local files.

    :param env: Environment to use (qa, prod, etc.).
    :param pattern: Pattern to filter templates.
    """
    config = get_config()
    template_manager = get_template_manager(config, env)

    try:
        saved_files = template_manager.save_templates(pattern)
        templates_dir = config.get_templates_dir(env)

        if saved_files:
            typer.echo(f"Saved {len(saved_files)} templates to {templates_dir}")
        else:
            typer.echo("No templates were saved.")
    except Exception as e:
        logger.error(f"Failed to save templates: {e}")
        sys.exit(1)


@templates_app.command("publish")
def publish_templates(
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter templates."
    ),
):
    """Publish templates from local files to OpenSearch.

    :param env: Environment to use (qa, prod, etc.).
    :param pattern: Pattern to filter templates.
    """
    config = get_config()
    template_manager = get_template_manager(config, env)

    try:
        results = template_manager.publish_templates(pattern)

        if not results:
            typer.echo("No templates were published.")
            return

        success_count = sum(1 for success in results.values() if success)
        fail_count = len(results) - success_count

        typer.echo(f"Published {success_count} templates to OpenSearch")
        if fail_count > 0:
            typer.echo(f"Failed to publish {fail_count} templates")

            # Show failed templates
            typer.echo("\nFailed templates:")
            for name, success in results.items():
                if not success:
                    typer.echo(f"- {name}")
    except Exception as e:
        logger.error(f"Failed to publish templates: {e}")
        sys.exit(1)


@templates_app.command("delete")
def delete_template(
    template_name: str = typer.Argument(..., help="Name of the template to delete."),
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
):
    """Delete a template from OpenSearch.

    :param template_name: Name of the template to delete.
    :param env: Environment to use (qa, prod, etc.).
    :param force: Skip confirmation prompt.
    """
    config = get_config()
    template_manager = get_template_manager(config, env)

    try:
        if force or typer.confirm(f"Are you sure you want to delete template '{template_name}'?"):
            success = template_manager.delete_template(template_name)
            if success:
                typer.echo(f"Template '{template_name}' was deleted.")
            else:
                typer.echo(f"Failed to delete template '{template_name}'.")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        sys.exit(1)


# ISM Policy commands
@ism_policies_app.command("list")
def list_ism_policies(
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter policies."
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table, json, yaml).",
        show_choices=True,
        case_sensitive=False,
    ),
):
    """List ISM policies in OpenSearch.

    :param env: Environment to use (qa, prod, etc.).
    :param pattern: Pattern to filter policies.
    :param format: Output format (table, json, yaml).
    """
    config = get_config()
    policy_manager = get_ism_policy_manager(config, env)

    try:
        policies = policy_manager.list_policies(pattern)
        formatted_policies = [
            {"name": p["name"], "last_updated_time": p["last_updated_time"]} for p in policies
        ]

        # Format output similar to templates but for policies
        if format == "json":
            import json

            typer.echo(json.dumps(formatted_policies, indent=2))
        elif format == "yaml":
            import yaml

            typer.echo(yaml.dump(formatted_policies, default_flow_style=False, sort_keys=False))
        else:  # table format
            if not policies:
                typer.echo("No ISM policies found.")
            else:
                table = Table(title="ISM Policies")
                table.add_column("Policy Name")
                table.add_column("Last updated time, UTC")

                for policy in policies:
                    table.add_row(
                        policy["name"],
                        datetime.datetime.fromtimestamp(
                            policy["last_updated_time"], datetime.UTC
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    )
                console.print(table)
    except Exception as e:
        logger.exception(f"Failed to list ISM policies: {e}")
        sys.exit(1)


@ism_policies_app.command("save")
def save_ism_policies(
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter policies."
    ),
):
    """Save ISM policies from OpenSearch to local files.

    :param env: Environment to use (qa, prod, etc.).
    :param pattern: Pattern to filter policies.
    """
    config = get_config()
    policy_manager = get_ism_policy_manager(config, env)

    try:
        saved_files = policy_manager.save_policies(pattern)
        policies_dir = config.get_ism_policies_dir(env)

        if saved_files:
            typer.echo(f"Saved {len(saved_files)} ISM policies to {policies_dir}")
        else:
            typer.echo("No ISM policies were saved.")
    except Exception as e:
        logger.error(f"Failed to save ISM policies: {e}")
        sys.exit(1)


@ism_policies_app.command("publish")
def publish_ism_policies(
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Pattern to filter policies."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
):
    """Publish ISM policies from local files to OpenSearch.

    :param env: Environment to use (qa, prod, etc.).
    :param pattern: Pattern to filter policies.
    :param force: Skip confirmation prompt.
    """
    config = get_config()
    policy_manager = get_ism_policy_manager(config, env)

    try:
        # Get all local policy names that match the pattern
        policy_names = policy_manager.list_local_policies_names(pattern)

        if not policy_names:
            typer.echo("No local ISM policy files found matching the pattern.")
            return

        successful = {}
        skipped = []

        # Process each policy
        for policy_name in policy_names:
            # Check if policy exists and get diff
            diff_result = policy_manager.diff_policy(policy_name)

            if diff_result is None:
                # Policy doesn't exist in OpenSearch yet - no confirmation needed
                typer.echo(f"Creating new policy: {policy_name}")
                success = policy_manager.publish_policy(policy_name)
                if success:
                    successful[policy_name] = True

            elif diff_result["has_changes"]:
                # Policy exists and has changes
                typer.echo(f"\nChanges for policy '{policy_name}':")
                typer.echo(diff_result["diff"].pretty())

                if force or typer.confirm("Apply these changes?"):
                    success = policy_manager.publish_policy(policy_name)
                    if success:
                        successful[policy_name] = True
                else:
                    typer.echo(f"Skipping policy '{policy_name}'")
                    skipped.append(policy_name)

            else:
                # Policy exists but no changes
                typer.echo(f"No changes for policy '{policy_name}' - skipping")
                skipped.append(policy_name)

        # Show summary
        if successful:
            typer.echo(f"\nPublished {len(successful)} ISM policies to OpenSearch")
        if skipped:
            typer.echo(f"Skipped {len(skipped)} ISM policies")

    except Exception as e:
        logger.error(f"Failed to publish ISM policies: {e}")
        sys.exit(1)


@ism_policies_app.command("delete")
def delete_ism_policy(
    policy_name: str = typer.Argument(..., help="Name of the ISM policy to delete."),
    env: str = typer.Option(..., "--env", "-e", help="Environment to use (qa, prod, etc.)."),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
):
    """Delete an ISM policy from OpenSearch.

    :param policy_name: Name of the ISM policy to delete.
    :param env: Environment to use (qa, prod, etc.).
    :param force: Skip confirmation prompt.
    """
    config = get_config()
    policy_manager = get_ism_policy_manager(config, env)

    try:
        if force or typer.confirm(f"Are you sure you want to delete ISM policy '{policy_name}'?"):
            success = policy_manager.delete_policy(policy_name)
            if success:
                typer.echo(f"ISM policy '{policy_name}' was deleted.")
            else:
                typer.echo(f"Failed to delete ISM policy '{policy_name}'.")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to delete ISM policy: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
