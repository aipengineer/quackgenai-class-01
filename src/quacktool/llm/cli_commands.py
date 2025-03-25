# src/quacktool/llm/cli_commands.py
"""
LLM-related commands for QuackTool CLI.

This module provides CLI commands for LLM-based functionality,
including metadata generation for text documents.
"""

import json
import traceback
from pathlib import Path

import click
from quackcore.cli import print_error, print_info, print_success, handle_errors

from quacktool.llm.metadata import generate_llm_metadata
from quacktool.models import AssetConfig


@click.command("metadata")
@click.argument(
    "input_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Print raw JSON output instead of formatted view.",
)
@click.pass_context
def metadata_command(
        ctx: click.Context,
        input_file: str,
        json_output: bool,
) -> None:
    """
    Generate LLM-based metadata for a text document.

    This command analyzes the input file using an LLM to produce metadata
    including title, summary, keywords, and topics.

    Example:

        quacktool metadata ./docs/my_article.txt
    """
    try:
        # Use the logger from the context
        logger = ctx.obj.get("logger")
        if logger:
            logger.info(f"Generating LLM metadata for {input_file}")

        input_path = Path(input_file)

        print_info(f"Generating LLM metadata for {input_path}...")

        asset_config = AssetConfig(input_path=input_path)

        metadata = generate_llm_metadata(asset_config)

        if "error" in metadata:
            print_error(f"Metadata generation failed: {metadata['error']}", exit_code=1)
            return

        if json_output:
            print(json.dumps(metadata, indent=2))
        else:
            print_success(f"Metadata for {input_file}")
            print_info(f"Title: {metadata.get('title', 'N/A')}")
            print_info(f"Summary:\n{metadata.get('summary', 'N/A')}")
            print_info(f"Keywords: {', '.join(metadata.get('keywords', []))}")
            print_info(f"Topics: {', '.join(metadata.get('topics', []))}")

    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.exception(f"Error in metadata_command: {e}")
        print_error(f"Error in metadata_command: {e}", exit_code=1)
        traceback.print_exc()


def register_llm_commands(cli_group):
    """
    Register all LLM-related commands with the specified CLI group.

    Args:
        cli_group: Click group to register commands with
    """
    cli_group.add_command(metadata_command)