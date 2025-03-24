# src/quacktool/llm_analyzer.py
"""
Specialized LLM-based content analysis tools.

This module extends the LLM capabilities of QuackTool with specialized
analyzers for different content analysis tasks.
"""

import json
from pathlib import Path
from typing import Any, Literal, Union

import openai
from openai import OpenAIError
from pydantic import BaseModel, Field

from quacktool.llm_settings import setup_llm_environment
from quacktool.models import AssetConfig


# Define analysis types with Pydantic for validation and documentation
class SentimentAnalysis(BaseModel):
    """Result of sentiment analysis."""
    polarity: float = Field(...,
                            description="Sentiment polarity from -1 (negative) to 1 (positive)")
    valence: str = Field(...,
                         description="Sentiment valence (negative, neutral, positive)")
    confidence: float = Field(..., description="Confidence score (0-1)")
    dominant_emotions: list[str] = Field(...,
                                         description="list of dominant emotions detected")
    analysis: str = Field(..., description="Textual analysis of the sentiment")


class EntityExtraction(BaseModel):
    """Result of entity extraction."""
    entities: dict[str, list[str]] = Field(
        ...,
        description="Dictionary mapping entity types to lists of extracted entities"
    )


class KeyPointsExtraction(BaseModel):
    """Result of key points extraction."""
    main_points: list[str] = Field(...,
                                   description="list of main points from the content")
    supporting_evidence: dict[str, list[str]] = Field(
        ...,
        description="Dictionary mapping main points to supporting evidence"
    )


class ContentStructure(BaseModel):
    """Analysis of content structure."""
    sections: list[dict[str, Union[str, list[str]]]] = Field(
        ...,
        description="list of content sections with titles and key elements"
    )
    flow_analysis: str = Field(..., description="Analysis of the logical flow")
    suggestions: list[str] = Field(...,
                                   description="Suggestions for structural improvements")


class ActionItemExtraction(BaseModel):
    """Extraction of action items from content."""
    action_items: list[dict[str, Any]] = Field(..., description="list of action items")
    deadlines: list[dict[str, Any]] = Field(...,
                                            description="list of deadlines mentioned")
    responsible_parties: list[str] = Field(...,
                                           description="list of responsible parties mentioned")


# Map of analysis types to their Pydantic models and prompts
ANALYSIS_CONFIGS = {
    "sentiment": {
        "model": SentimentAnalysis,
        "system_prompt": """You are an expert sentiment analyzer. Given the content of a document, analyze its sentiment in detail.
Provide:
1. A polarity score between -1.0 (extremely negative) and 1.0 (extremely positive)
2. The sentiment valence ("negative", "neutral", or "positive")
3. A confidence score between 0.0 and 1.0 for your analysis
4. A list of dominant emotions detected in the text
5. A brief qualitative analysis of the sentiment

Return your analysis as a valid JSON object with these keys: 
polarity, valence, confidence, dominant_emotions, analysis"""
    },
    "entities": {
        "model": EntityExtraction,
        "system_prompt": """You are an expert entity extraction system. Given the content of a document, extract all named entities.
Categorize entities into types such as:
- people
- organizations
- locations
- dates
- products
- technologies
- concepts
- other relevant entity types you identify

Return your analysis as a valid JSON object with an "entities" key mapping to a dictionary
where keys are entity types and values are lists of unique entities of that type."""
    },
    "key_points": {
        "model": KeyPointsExtraction,
        "system_prompt": """You are an expert content analyst. Given the content of a document, extract the key points and supporting evidence.
Provide:
1. A list of the main points or arguments in the content
2. For each main point, a list of supporting evidence, quotes, or details from the text

Return your analysis as a valid JSON object with these keys:
main_points (a list of strings), supporting_evidence (a dictionary mapping each main point to a list of supporting evidence)"""
    },
    "structure": {
        "model": ContentStructure,
        "system_prompt": """You are an expert content structure analyst. Given the content of a document, analyze its structure.
Provide:
1. A breakdown of the content's sections (with titles and key elements in each)
2. An analysis of the logical flow between sections
3. Suggestions for structural improvements

Return your analysis as a valid JSON object with these keys:
sections (a list of section objects with title and key_elements), flow_analysis (a string), suggestions (a list of strings)"""
    },
    "action_items": {
        "model": ActionItemExtraction,
        "system_prompt": """You are an expert at extracting action items from text. Given the content of a document, identify all action items, deadlines, and responsible parties.
Provide:
1. A list of action items (with description, priority if mentioned, and context)
2. A list of deadlines mentioned (with the associated action and date)
3. A list of responsible parties (people or teams mentioned as responsible for actions)

Return your analysis as a valid JSON object with these keys:
action_items (a list of action item objects), deadlines (a list of deadline objects), responsible_parties (a list of strings)"""
    }
}


def analyze_content(
        asset_config: AssetConfig,
        analysis_type: Literal[
            "sentiment", "entities", "key_points", "structure", "action_items"],
        model: str = "gpt-3.5-turbo",
) -> dict[str, Any]:
    """
    Analyze document content using a specialized LLM analyzer.

    Args:
        asset_config: Configuration for the asset to analyze
        analysis_type: Type of analysis to perform
        model: LLM model to use

    Returns:
        Dictionary with the analysis results
    """
    from quacktool.config import get_logger
    logger = get_logger()

    input_path: Path = asset_config.input_path

    try:
        # Validate analysis type
        if analysis_type not in ANALYSIS_CONFIGS:
            return {"error": f"Invalid analysis type: {analysis_type}"}

        # Get analysis configuration
        analysis_config = ANALYSIS_CONFIGS[analysis_type]
        system_prompt = analysis_config["system_prompt"]
        result_model = analysis_config["model"]

        # Ensure OpenAI API key is set
        setup_llm_environment()

        # Read and truncate file content
        text = input_path.read_text(encoding="utf-8")
        truncated_text = truncate_text(text)

        logger.info(f"Performing {analysis_type} analysis on: {input_path}")

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": truncated_text},
            ],
            temperature=0.3,
            max_tokens=800,
        )

        raw_output = response.choices[0].message.content

        # Parse and validate result with Pydantic
        result_dict = json.loads(raw_output)
        validated_result = result_model(**result_dict)

        return validated_result.model_dump()

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return {"error": f"OpenAI API error: {str(e)}"}

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON returned by LLM: {e}")
        return {"error": "Invalid JSON returned by the LLM"}

    except Exception as e:
        logger.exception(f"Error in {analysis_type} analysis")
        return {"error": f"Analysis failed: {str(e)}"}


def truncate_text(text: str, max_tokens: int = 4000) -> str:
    """
    Truncate text to fit within token limits.

    Args:
        text: Document text
        max_tokens: Maximum tokens to allow

    Returns:
        Truncated text
    """
    # Approximate token count (4 chars per token is a rough estimate)
    max_chars = max_tokens * 4
    return text[:max_chars]