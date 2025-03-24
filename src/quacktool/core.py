# src/quacktool/core.py
"""
Core functionality for QuackTool.

This module contains the main business logic for the QuackTool application,
implementing the asset processing capabilities.
"""

import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

from quackcore.fs import service as fs
from quackcore.paths import resolver

from quacktool.models import (
    AssetConfig,
    AssetType,
    ProcessingMode,
    ProcessingResult,
)

# Setup module-level logger
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_tool_config() -> Dict[str, Any]:
    """
    Get the tool configuration in a way that avoids circular imports.
    Cache the result to avoid repeated imports.

    Returns:
        Dictionary containing tool configuration
    """
    from quacktool.config import get_tool_config
    return get_tool_config()


def process_asset(
        asset_config: AssetConfig,
) -> ProcessingResult:
    """
    Process an asset based on the provided configuration.

    This function orchestrates the asset processing workflow, delegating to
    specialized functions based on the asset type and processing mode.

    Args:
        asset_config: Configuration for the asset to process

    Returns:
        ProcessingResult containing the result of the processing operation
    """
    start_time = time.time()
    logger.info(f"Processing asset: {asset_config.input_path}")

    try:
        if not asset_config.input_path.exists():
            duration_ms = max(1, int((time.time() - start_time) * 1000))
            return ProcessingResult(
                success=False,
                error=f"Input file not found: {asset_config.input_path}",
                duration_ms=duration_ms,
            )

        asset_type = asset_config.asset_type
        if asset_type == AssetType.OTHER:
            asset_type = _detect_asset_type(asset_config.input_path)

        output_path = asset_config.output_path
        if output_path is None:
            output_path = _generate_output_path(
                asset_config.input_path, asset_config.options.format
            )

        result = _process_by_type_and_mode(asset_config, asset_type, output_path)
        result.duration_ms = max(1, int((time.time() - start_time) * 1000))

        if result.success:
            logger.info(
                f"Successfully processed asset {asset_config.input_path} "
                f"to {result.output_path} in {result.duration_ms}ms"
            )
        else:
            logger.error(
                f"Failed to process asset {asset_config.input_path}: {result.error}"
            )

        return result

    except Exception as e:
        logger.exception(f"Error processing asset: {str(e)}")
        duration_ms = max(1, int((time.time() - start_time) * 1000))
        return ProcessingResult(
            success=False,
            error=f"Processing error: {str(e)}",
            duration_ms=duration_ms,
        )


def _detect_asset_type(file_path: Path) -> AssetType:
    """
    Detect the type of asset based on file extension.

    Args:
        file_path: Path to the asset

    Returns:
        AssetType enum value representing the detected type
    """
    # First check if the file exists
    file_info = fs.get_file_info(file_path)
    if not file_info.success or not file_info.exists:
        return AssetType.OTHER

    # Try to detect by MIME type first
    asset_type = _detect_by_mime_type(file_path)
    if asset_type != AssetType.OTHER:
        return asset_type

    return _detect_by_extension(file_path)


def _detect_by_mime_type(file_path: Path) -> AssetType:
    """
    Detect asset type based on MIME type.

    Args:
        file_path: Path to the asset

    Returns:
        Detected AssetType or AssetType.OTHER if not detected
    """

    mime_type = fs.get_mime_type(file_path)

    if not mime_type:
        return AssetType.OTHER

    if mime_type.startswith("image/"):
        return AssetType.IMAGE
    if mime_type.startswith("video/"):
        return AssetType.VIDEO
    if mime_type.startswith("audio/"):
        return AssetType.AUDIO
    if mime_type.startswith(("text/", "application/pdf", "application/vnd.")):
        return AssetType.DOCUMENT

    return AssetType.OTHER


def _detect_by_extension(file_path: Path) -> AssetType:
    """
    Detect asset type based on file extension.

    Args:
        file_path: Path to the asset

    Returns:
        Detected AssetType or AssetType.OTHER if not detected
    """
    suffix = file_path.suffix.lower()
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".svg",
        ".tiff",
    }
    video_extensions = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"}
    audio_extensions = {".mp3", ".wav", ".ogg", ".aac", ".flac", ".m4a"}
    document_extensions = {".pdf", ".doc", ".docx", ".txt", ".md", ".html", ".xml"}

    if suffix in image_extensions:
        return AssetType.IMAGE
    if suffix in video_extensions:
        return AssetType.VIDEO
    if suffix in audio_extensions:
        return AssetType.AUDIO
    if suffix in document_extensions:
        return AssetType.DOCUMENT

    return AssetType.OTHER


def _generate_output_path(input_path: Path, file_format: str | None = None) -> Path:
    """
    Generate an output path based on the input path and optional format.

    Args:
        input_path: Path to the input asset
        file_format: Optional output format (file extension)

    Returns:
        Path object for the generated output path
    """
    # Get configuration using the cached function to avoid circular imports
    tool_config = _get_tool_config()
    output_dir = "./output"

    if isinstance(tool_config, dict):
        output_dir = tool_config.get("output_dir", "./output")
    else:
        output_dir = getattr(tool_config, "output_dir", "./output")

    output_dir_path = resolver.resolve_project_path(output_dir)
    fs.create_directory(output_dir_path, exist_ok=True)

    stem = input_path.stem
    extension = f".{file_format}" if file_format else input_path.suffix
    output_path = output_dir_path / f"{stem}{extension}"
    counter = 1

    while output_path.exists():
        output_path = output_dir_path / f"{stem}_{counter}{extension}"
        counter += 1

    return output_path


def _process_by_type_and_mode(
        asset_config: AssetConfig,
        asset_type: AssetType,
        output_path: Path,
) -> ProcessingResult:
    """
    Process an asset based on its type and the processing mode.

    Args:
        asset_config: Configuration for the asset
        asset_type: Type of the asset
        output_path: Path for the processed output

    Returns:
        ProcessingResult with the outcome of the processing
    """
    # Ensure the output directory exists
    fs.create_directory(output_path.parent, exist_ok=True)

    # Process based on asset type and mode
    if asset_type == AssetType.IMAGE:
        return _process_image(asset_config, output_path)
    elif asset_type == AssetType.VIDEO:
        return _process_video(asset_config, output_path)
    elif asset_type == AssetType.AUDIO:
        return _process_audio(asset_config, output_path)
    elif asset_type == AssetType.DOCUMENT:
        return _process_document(asset_config, output_path)
    else:
        return _copy_file(asset_config.input_path, output_path)


def _process_image(asset_config: AssetConfig, output_path: Path) -> ProcessingResult:
    """
    Process an image asset.

    Args:
        asset_config: Configuration for the image
        output_path: Path for the processed output

    Returns:
        ProcessingResult with the outcome of the processing
    """
    logger.info(f"Processing image {asset_config.input_path} to {output_path}")

    # For this skeleton implementation, simply copy the file
    # In a real implementation, you would use a library
    # like Pillow to process the image
    start_time = time.time()
    result = _copy_file(asset_config.input_path, output_path)
    # Ensure duration is always set
    result.duration_ms = max(1, int((time.time() - start_time) * 1000))
    return result


def _process_video(asset_config: AssetConfig, output_path: Path) -> ProcessingResult:
    """
    Process a video asset.

    Args:
        asset_config: Configuration for the video
        output_path: Path for the processed output

    Returns:
        ProcessingResult with the outcome of the processing
    """
    logger.info(f"Processing video {asset_config.input_path} to {output_path}")

    # For this skeleton implementation, simply copy the file
    # In a real implementation, you would use a
    # library like ffmpeg to process the video
    start_time = time.time()
    result = _copy_file(asset_config.input_path, output_path)
    result.duration_ms = max(1, int((time.time() - start_time) * 1000))
    return result


def _process_audio(asset_config: AssetConfig, output_path: Path) -> ProcessingResult:
    """
    Process an audio asset.

    Args:
        asset_config: Configuration for the audio
        output_path: Path for the processed output

    Returns:
        ProcessingResult with the outcome of the processing
    """
    logger.info(f"Processing audio {asset_config.input_path} to {output_path}")

    # For this skeleton implementation, simply copy the file
    # In a real implementation, you would use a
    # library like ffmpeg to process the audio
    start_time = time.time()
    result = _copy_file(asset_config.input_path, output_path)
    # Ensure duration is always set
    result.duration_ms = max(1, int((time.time() - start_time) * 1000))
    return result


def _process_document(asset_config: AssetConfig, output_path: Path) -> ProcessingResult:
    """
    Process a document asset.

    Args:
        asset_config: Configuration for the document
        output_path: Path for the processed output

    Returns:
        ProcessingResult with the outcome of the processing
    """
    logger.info(f"Processing document {asset_config.input_path} to {output_path}")
    start_time = time.time()

    try:
        if asset_config.options.mode == ProcessingMode.GENERATE:
            # Lazy import to avoid circular dependencies
            from quacktool.llm_metadata import generate_llm_metadata

            metadata = generate_llm_metadata(asset_config)
            return ProcessingResult(
                success=True,
                output_path=asset_config.input_path,
                metrics={"llm_metadata": metadata},
                duration_ms=max(1, int((time.time() - start_time) * 1000)),
            )

        result = _copy_file(asset_config.input_path, output_path)
        result.duration_ms = max(1, int((time.time() - start_time) * 1000))
        return result

    except Exception as e:
        logger.exception(f"Error processing document: {str(e)}")
        return ProcessingResult(
            success=False,
            error=f"Document processing error: {str(e)}",
            duration_ms=max(1, int((time.time() - start_time) * 1000)),
        )


def _copy_file(input_path: Path, output_path: Path) -> ProcessingResult:
    """
    Copy a file from input to output path.

    Args:
        input_path: Path to the input file
        output_path: Path for the output file

    Returns:
        ProcessingResult with the outcome of the copy operation
    """
    try:
        input_info = fs.get_file_info(input_path)
        if not input_info.success or not input_info.exists:
            return ProcessingResult(
                success=False,
                error=f"Input file not found: {input_path}",
            )

        input_size = input_info.size or 0
        copy_result = fs.copy(input_path, output_path, overwrite=True)
        if not copy_result.success:
            return ProcessingResult(
                success=False,
                error=f"Failed to copy file: {copy_result.error}",
            )

        output_info = fs.get_file_info(output_path)
        output_size = output_info.size or 0
        metrics = {
            "input_size": input_size,
            "output_size": output_size,
            "size_ratio": round(output_size / input_size if input_size > 0 else 1.0, 4),
        }

        return ProcessingResult(
            success=True,
            output_path=output_path,
            metrics=metrics,
        )
    except Exception as e:
        logger.exception(f"Error copying file: {str(e)}")
        return ProcessingResult(
            success=False,
            error=f"File copy error: {str(e)}",
        )