# src/quacktool/llm_settings.py
"""
LLM settings and environment configuration.

This module uses pydantic-settings to manage environment variables
and initialize the LLM environment (e.g., OpenAI credentials).
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Optional: provide a default for development/testing
MOCK_OPENAI_API_KEY = "mock_openai_api_key_12345"


class LLMSettings(BaseSettings):
    """
    Configuration for LLM access.

    In production, set OPENAI_API_KEY in your environment.
    This class pulls it automatically via pydantic-settings.
    """

    openai_api_key: str = Field(default=MOCK_OPENAI_API_KEY)

    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix needed; uses OPENAI_API_KEY directly
        extra="ignore"
    )


def setup_llm_environment() -> LLMSettings:
    """
    Set up the environment variables and return the LLM settings.

    This sets the OPENAI_API_KEY environment variable so that
    OpenAI's Python SDK can find it.

    Returns:
        LLMSettings: Parsed settings object
    """
    settings = LLMSettings()

    # Inject into environment so OpenAI SDK can pick it up
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    return settings
