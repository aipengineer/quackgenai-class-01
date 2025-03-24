# tests/test_llm_metadata.py
"""
Unit tests for LLM metadata generation module.
"""

from pathlib import Path

import pytest

from quacktool.llm_metadata import generate_llm_metadata
from quacktool.models import AssetConfig, AssetType, ProcessingMode, ProcessingOptions


@pytest.fixture
def sample_txt_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("""
    QuackTool is a modular automation tool.
    It simplifies processing for documents, images, and more.
    This file demonstrates how LLMs can be used to extract metadata.
    """)
    return file_path


def test_generate_llm_metadata_returns_dict(sample_txt_file: Path):
    asset_config = AssetConfig(
        input_path=sample_txt_file,
        asset_type=AssetType.DOCUMENT,
        options=ProcessingOptions(mode=ProcessingMode.GENERATE),
    )

    result = generate_llm_metadata(asset_config)

    assert isinstance(result, dict)
    assert "summary" in result
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


def test_generate_llm_metadata_handles_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")

    asset_config = AssetConfig(
        input_path=empty_file,
        asset_type=AssetType.DOCUMENT,
        options=ProcessingOptions(mode=ProcessingMode.GENERATE),
    )

    result = generate_llm_metadata(asset_config)

    assert isinstance(result, dict)
    assert result["summary"] == "No content to summarize."


def test_generate_llm_metadata_ignores_non_document_type(sample_txt_file: Path):
    asset_config = AssetConfig(
        input_path=sample_txt_file,
        asset_type=AssetType.IMAGE,
        options=ProcessingOptions(mode=ProcessingMode.GENERATE),
    )

    result = generate_llm_metadata(asset_config)

    assert result == {"summary": "LLM metadata not supported for this asset type."}
