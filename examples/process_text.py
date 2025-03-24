#!/usr/bin/env python3
"""
Direct text processing script that doesn't rely on the plugin system.
This can be used to quickly test LLM functionality.

Usage:
    python process_text.py path/to/document.txt [--json]
"""

import argparse
import json
import os
from pathlib import Path
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from quacktool
from quacktool.llm_metadata import generate_llm_metadata
from quacktool.models import AssetConfig


def main():
    """Process text files directly with the LLM."""
    parser = argparse.ArgumentParser(description="Process text with LLM")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    print(f"Processing {input_path}...")

    # Create asset config
    asset_config = AssetConfig(input_path=input_path)

    # Generate metadata
    metadata = generate_llm_metadata(asset_config)

    if "error" in metadata:
        print(f"Error: {metadata['error']}")
        return 1

    if args.json:
        print(json.dumps(metadata, indent=2))
    else:
        print(f"\nMetadata for {input_path}:")
        print(f"Title: {metadata.get('title', 'N/A')}")
        print(f"\nSummary:\n{metadata.get('summary', 'N/A')}")
        print(f"\nKeywords: {', '.join(metadata.get('keywords', []))}")
        print(f"\nTopics: {', '.join(metadata.get('topics', []))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())