"""
Command-line interface for opensearch-keeper.
"""

import logging
import sys

import click

from opensearch_keeper.config import Config
from opensearch_keeper.template_manager import TemplateManager
from opensearch_keeper.utils import setup_logging, format_template_list

logger = logging.getLogger(__name__)


def get_template_manager(config: Config, env: str):
    """
    Create a template manager for the specified environment.

    Args:
        config: Configuration object.
        env: Environment name.

    Returns:
        TemplateManager instance.
    """
    try:
        env_config = config.get_environment_config(env)
        templates_dir = config.get_templates_dir()
        ignore_patterns = config.get_ignore_patterns()
        return TemplateManager(env_config, templates_dir, ignore_patterns)
    except Exception as e:
        logger.error(f"Failed to create template manager: {e}")
        sys.exit(1)


@click.group()
@click.option("--config", "-c", help="Path to configuration file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
@click.pass_context
def cli(ctx, config, verbose):
    """
    Manage OpenSearch index templates.

    This tool allows you to list, save, and publish OpenSearch index templates.
    """
    setup_logging(verbose)

    try:
        ctx.ensure_object(dict)
        ctx.obj["config"] = Config(config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


@cli.command("list")
@click.option("--env", "-e", required=True, help="Environment to use (qa, prod, etc.).")
@click.option("--pattern", "-p", help="Pattern to filter templates.")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format.",
)
@click.pass_context
def list_templates(ctx, env, pattern, fmt):
    """List templates in OpenSearch."""
    config = ctx.obj["config"]
    template_manager = get_template_manager(config, env)

    try:
        templates = template_manager.list_templates(pattern)
        click.echo(format_template_list(templates, fmt))
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        sys.exit(1)


@cli.command("save")
@click.option("--env", "-e", required=True, help="Environment to use (qa, prod, etc.).")
@click.option("--pattern", "-p", help="Pattern to filter templates.")
@click.pass_context
def save_templates(ctx, env, pattern):
    """Save templates from OpenSearch to local files."""
    config = ctx.obj["config"]
    template_manager = get_template_manager(config, env)

    try:
        saved_files = template_manager.save_templates(pattern)
        if saved_files:
            click.echo(f"Saved {len(saved_files)} templates to {config.get_templates_dir()}")
        else:
            click.echo("No templates were saved.")
    except Exception as e:
        logger.error(f"Failed to save templates: {e}")
        sys.exit(1)


@cli.command("publish")
@click.option("--env", "-e", required=True, help="Environment to use (qa, prod, etc.).")
@click.option("--pattern", "-p", help="Pattern to filter templates.")
@click.pass_context
def publish_templates(ctx, env, pattern):
    """Publish templates from local files to OpenSearch."""
    config = ctx.obj["config"]
    template_manager = get_template_manager(config, env)

    try:
        results = template_manager.publish_templates(pattern)

        if not results:
            click.echo("No templates were published.")
            return

        success_count = sum(1 for success in results.values() if success)
        fail_count = len(results) - success_count

        click.echo(f"Published {success_count} templates to OpenSearch")
        if fail_count > 0:
            click.echo(f"Failed to publish {fail_count} templates")

            # Show failed templates
            click.echo("\nFailed templates:")
            for name, success in results.items():
                if not success:
                    click.echo(f"- {name}")
    except Exception as e:
        logger.error(f"Failed to publish templates: {e}")
        sys.exit(1)


@cli.command("delete")
@click.option("--env", "-e", required=True, help="Environment to use (qa, prod, etc.).")
@click.argument("template_name")
@click.pass_context
def delete_template(ctx, env, template_name):
    """Delete a template from OpenSearch."""
    config = ctx.obj["config"]
    template_manager = get_template_manager(config, env)

    try:
        if click.confirm(f"Are you sure you want to delete template '{template_name}'?"):
            success = template_manager.delete_template(template_name)
            if success:
                click.echo(f"Template '{template_name}' was deleted.")
            else:
                click.echo(f"Failed to delete template '{template_name}'.")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        sys.exit(1)


@cli.command("environments")
@click.pass_context
def list_environments(ctx):
    """List available environments from the configuration."""
    config = ctx.obj["config"]

    try:
        environments = config.get_available_environments()
        if environments:
            click.echo("Available environments:")
            for env in environments:
                click.echo(f"- {env}")
        else:
            click.echo("No environments configured.")
    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli(obj={})
