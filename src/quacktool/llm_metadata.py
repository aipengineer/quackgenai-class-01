# src/quacktool/llm_metadata.py
"""
LLM-based metadata generation for text documents.

This module provides functionality to generate summaries, keywords,
and other metadata from textual assets using a language model.
"""

import json
from pathlib import Path
from typing import Any

import openai
from openai import OpenAIError

from quacktool.llm_settings import setup_llm_environment
from quacktool.models import AssetConfig

# Choose model — you can switch to "gpt-4" if needed
DEFAULT_MODEL = "gpt-3.5-turbo"

# Max tokens for text input (approx. conservative for gpt-3.5-turbo)
MAX_TEXT_TOKENS = 4000

# System prompt to guide the LLM output format
SYSTEM_PROMPT = """You are a metadata generation assistant for documents.

Given the full content of a document, generate structured JSON metadata
with the following keys:

- "title": A short, descriptive title of the document.
- "summary": A concise paragraph summarizing the document content.
- "keywords": A list of 5-10 keywords (single words or short phrases).
- "topics": A list of higher-level topics or domains related to the content.

The output MUST be a valid JSON object with those keys.
"""


def generate_llm_metadata(asset_config: AssetConfig) -> dict[str, Any]:
    """
    Generate metadata for a document using a language model.

    Args:
        asset_config: The asset configuration containing input path and options

    Returns:
        Dictionary with generated metadata (e.g., summary, keywords, title)
    """
    from quacktool.config import get_logger  # ⬅️ Delayed import
    logger = get_logger()
    input_path: Path = asset_config.input_path

    try:
        # Ensure OpenAI API key is set
        setup_llm_environment()

        # Read and truncate file content
        text = input_path.read_text(encoding="utf-8")
        truncated_text = truncate_text(text)

        logger.info(f"Generating LLM metadata using OpenAI API for: {input_path}")

        # Prepare the chat prompt
        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": truncated_text},
            ],
            temperature=0.3,
            max_tokens=512,
        )

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
        logger.exception("Unexpected error in LLM metadata generation")
        return {"error": f"LLM metadata generation failed: {str(e)}"}


def truncate_text(text: str, max_tokens: int = MAX_TEXT_TOKENS) -> str:
    """
    Truncate text to a reasonable length to fit LLM input limits.

    Args:
        text: Full document text
        max_tokens: Rough upper bound for tokens

    Returns:
        Truncated text string
    """
    # Approximate token = ~4 characters (safe for gpt-3.5)
    max_chars = max_tokens * 4
    return text[:max_chars]
