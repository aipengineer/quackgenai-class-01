# examples/quick_metadata.py
"""
A standalone script to quickly test LLM metadata functionality without using the plugin system.

Usage:
  python quick_metadata.py /path/to/document.txt [--json]
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("quick_metadata")

# Ensure we can import from quacktool
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, src_dir)

try:
    # Import the necessary modules
    from quacktool.llm.settings import setup_llm_environment
    from quacktool.models import AssetConfig
    import openai
    from openai import OpenAIError
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running this script from the project directory")
    sys.exit(1)

# System prompt for the LLM
SYSTEM_PROMPT = """You are a metadata generation assistant for documents.

Given the full content of a document, generate structured JSON metadata
with the following keys:

- "title": A short, descriptive title of the document.
- "summary": A concise paragraph summarizing the document content.
- "keywords": A list of 5-10 keywords (single words or short phrases).
- "topics": A list of higher-level topics or domains related to the content.

The output MUST be a valid JSON object with those keys.
"""

# Maximum tokens for LLM input
MAX_TEXT_TOKENS = 4000


def truncate_text(text: str, max_tokens: int = MAX_TEXT_TOKENS) -> str:
    """Truncate text to a reasonable length for LLM input."""
    # Approximate tokens (4 chars per token is a rough estimate)
    max_chars = max_tokens * 4
    return text[:max_chars]


def generate_metadata(file_path: Path) -> dict:
    """Generate metadata for a document using the OpenAI API."""
    try:
        # Configure the OpenAI API
        setup_llm_environment()

        # Read the file
        logger.info(f"Reading file: {file_path}")
        text = file_path.read_text(encoding="utf-8")
        truncated_text = truncate_text(text)

        # Call the API
        logger.info("Calling OpenAI API for analysis...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": truncated_text},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        # Parse the result
        raw_output = response.choices[0].message.content
        metadata = json.loads(raw_output)

        return metadata

    except OpenAIError as api_error:
        logger.error(f"OpenAI API error: {api_error}")
        return {"error": f"OpenAI API error: {str(api_error)}"}

    except json.JSONDecodeError as json_error:
        logger.error(f"Invalid JSON returned by LLM: {json_error}")
        return {"error": "Invalid JSON returned by the LLM"}

    except Exception as e:
        logger.exception("Unexpected error")
        return {"error": f"Metadata generation failed: {str(e)}"}


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate metadata from a document using LLM")
    parser.add_argument("file_path", help="Path to the document to analyze")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()
    file_path = Path(args.file_path)

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1

    print(f"Generating metadata for: {file_path}")
    metadata = generate_metadata(file_path)

    if "error" in metadata:
        logger.error(metadata["error"])
        return 1

    if args.json:
        print(json.dumps(metadata, indent=2))
    else:
        print("\n===== DOCUMENT METADATA =====")
        print(f"Title: {metadata.get('title', 'N/A')}")
        print("\nSummary:")
        print(metadata.get('summary', 'N/A'))
        print("\nKeywords:")
        for keyword in metadata.get('keywords', []):
            print(f"- {keyword}")
        print("\nTopics:")
        for topic in metadata.get('topics', []):
            print(f"- {topic}")

    return 0


if __name__ == "__main__":
    sys.exit(main())