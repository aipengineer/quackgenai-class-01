# examples/template_cli.py
"""
Command-line interface for working with prompt templates.

This script demonstrates how to use the prompt template system to create,
manage, and execute parameterized prompts for LLM interactions.

Usage:
  python template_cli.py list
  python template_cli.py show "Template Name"
  python template_cli.py run "Template Name" param1=value1 param2=value2
  python template_cli.py create
"""

import argparse
import os
import sys

# Ensure we can import from quacktool
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, src_dir)

try:
    # Import the necessary modules
    from quacktool.prompt_templates import PromptTemplate, TemplateManager, \
        initialize_default_templates
    from quacktool.llm.settings import setup_llm_environment
    import openai
    from openai import OpenAIError
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this script from the project directory")
    sys.exit(1)


def parse_param_args(args: list[str]) -> dict[str, str]:
    """
    Parse parameter arguments in the format param=value.

    Args:
        args: list of parameter strings

    Returns:
        Dictionary mapping parameter names to values
    """
    params = {}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            params[key] = value
        else:
            print(f"Warning: Ignoring invalid parameter format: {arg}")
    return params


def list_templates(manager: TemplateManager) -> None:
    """
    list all available templates.

    Args:
        manager: Template manager instance
    """
    templates = manager.list_templates()

    if not templates:
        print("No templates found.")
        return

    print(f"\nFound {len(templates)} templates:\n")

    for i, template in enumerate(templates, 1):
        print(f"{i}. {template['name']}")
        print(f"   Description: {template['description']}")
        if template['parameters']:
            params_str = ", ".join(f"${p}" for p in template['parameters'])
            print(f"   Parameters: {params_str}")
        if template['tags']:
            tags_str = ", ".join(template['tags'])
            print(f"   Tags: {tags_str}")
        print()


def show_template(manager: TemplateManager, template_name: str) -> None:
    """
    Show details of a specific template.

    Args:
        manager: Template manager instance
        template_name: Name of the template to show
    """
    template = manager.get_template(template_name)

    if not template:
        print(f"Template not found: {template_name}")
        return

    print(f"\n===== {template.name} =====")
    print(f"Description: {template.description}")
    print(f"Version: {template.version}")

    if template.tags:
        print(f"Tags: {', '.join(template.tags)}")

    print("\nParameters:")
    if template.parameters:
        for param, desc in template.parameters.items():
            print(f"  ${param}: {desc}")
    else:
        print("  None")

    print("\nSystem Message:")
    if template.system_message:
        print(f"  {template.system_message}")
    else:
        print("  None")

    print("\nTemplate:")
    print(f"  {template.template}")

    if template.examples:
        print("\nExamples:")
        for i, example in enumerate(template.examples, 1):
            print(f"  Example {i}:")
            print(f"    Parameters: {example.get('parameters', {})}")
            if 'output' in example:
                print(f"    Output: {example['output'][:100]}...")

    print()


def run_template(
        manager: TemplateManager,
        template_name: str,
        params: dict[str, str],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 500
) -> None:
    """
    Run a template with the provided parameters.

    Args:
        manager: Template manager instance
        template_name: Name of the template to run
        params: Parameter values
        model: LLM model to use
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
    """
    template = manager.get_template(template_name)

    if not template:
        print(f"Template not found: {template_name}")
        return

    # Check for missing parameters
    missing_params = []
    for param in template.parameters.keys():
        if param not in params:
            missing_params.append(param)

    if missing_params:
        print(
            f"Missing required parameters: {', '.join('$' + p for p in missing_params)}")
        return

    # Set up environment
    setup_llm_environment()

    # Format messages
    messages = template.to_chat_messages(**params)

    print(f"\nRunning template: {template.name}")
    print(f"Model: {model}, Temperature: {temperature}\n")

    print("===== PROMPT =====")
    formatted_prompt = template.format(**params)
    print(formatted_prompt[:500] + ("..." if len(formatted_prompt) > 500 else ""))
    print("\n===== RESPONSE =====")

    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Print response
        print(response.choices[0].message.content)

        # Print usage information
        print("\n===== USAGE =====")
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print(f"Total tokens: {response.usage.total_tokens}")

    except OpenAIError as e:
        print(f"OpenAI API error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def create_template_interactive() -> None:
    """Create a new template interactively."""
    print("\n===== CREATE NEW TEMPLATE =====\n")

    name = input("Template name: ")
    if not name:
        print("Template name is required.")
        return

    description = input("Description: ")

    print("\nSystem message (optional, for chat models):")
    print("Enter text below, finish with a line containing only '.'")
    system_lines = []
    while True:
        line = input()
        if line == ".":
            break
        system_lines.append(line)
    system_message = "\n".join(system_lines) if system_lines else None

    print("\nTemplate text (use $parameter or ${parameter} for variables):")
    print("Enter text below, finish with a line containing only '.'")
    template_lines = []
    while True:
        line = input()
        if line == ".":
            break
        template_lines.append(line)
    template_text = "\n".join(template_lines)

    # Extract parameters
    import re
    param_pattern = r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)'
    matches = re.findall(param_pattern, template_text)
    params = set()

    for match in matches:
        # Each match is a tuple of (braced, unbraced)
        param = match[0] or match[1]
        params.add(param)

    # Collect parameter descriptions
    parameters = {}
    if params:
        print("\nParameter descriptions:")
        for param in params:
            desc = input(f"Description for ${param}: ")
            parameters[param] = desc

    # Collect tags
    tags_input = input("\nTags (comma-separated): ")
    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

    # Create the template
    template = PromptTemplate(
        name=name,
        description=description,
        template=template_text,
        system_message=system_message,
        parameters=parameters,
        tags=tags
    )

    # Save the template
    manager = TemplateManager()
    file_path = manager.save_template(template)

    print(f"\nTemplate saved to {file_path}")


def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Command-line interface for prompt templates")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list command
    list_parser = subparsers.add_parser("list", help="list all available templates")

    # Show command
    show_parser = subparsers.add_parser("show",
                                        help="Show details of a specific template")
    show_parser.add_argument("name", help="Template name")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a template with parameters")
    run_parser.add_argument("name", help="Template name")
    run_parser.add_argument("params", nargs="*",
                            help="Parameters in the format param=value")
    run_parser.add_argument("--model", default="gpt-3.5-turbo",
                            help="OpenAI model to use")
    run_parser.add_argument("--temperature", type=float, default=0.7,
                            help="Temperature for generation")
    run_parser.add_argument("--max-tokens", type=int, default=500,
                            help="Maximum tokens to generate")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new template")

    # Parse arguments
    args = parser.parse_args()

    # Initialize default templates
    initialize_default_templates()

    # Create template manager
    manager = TemplateManager()

    # Execute command
    if args.command == "list":
        list_templates(manager)
    elif args.command == "show":
        show_template(manager, args.name)
    elif args.command == "run":
        params = parse_param_args(args.params)
        run_template(
            manager,
            args.name,
            params,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
    elif args.command == "create":
        create_template_interactive()
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())