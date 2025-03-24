#!/usr/bin/env python3
"""
Advanced content analysis tool for text documents.

This standalone script provides specialized content analysis using LLMs,
without relying on the QuackTool plugin system.

Usage:
  python content_analyzer.py sentiment file.txt
  python content_analyzer.py entities file.txt
  python content_analyzer.py key_points file.txt
  python content_analyzer.py structure file.txt
  python content_analyzer.py action_items file.txt
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("content_analyzer")

# Ensure we can import from quacktool
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, src_dir)

try:
    # Import the necessary modules
    from quacktool.llm_settings import setup_llm_environment
    import openai
    from openai import OpenAIError
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running this script from the project directory")
    sys.exit(1)

# Analysis types and their system prompts
ANALYSIS_TYPES = {
    "sentiment": {
        "description": "Analyze sentiment and emotional tone",
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
        "description": "Extract named entities and key concepts",
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
        "description": "Extract main points and supporting evidence",
        "system_prompt": """You are an expert content analyst. Given the content of a document, extract the key points and supporting evidence.
Provide:
1. A list of the main points or arguments in the content
2. For each main point, a list of supporting evidence, quotes, or details from the text

Return your analysis as a valid JSON object with these keys:
main_points (a list of strings), supporting_evidence (a dictionary mapping each main point to a list of supporting evidence)"""
    },
    "structure": {
        "description": "Analyze document structure and flow",
        "system_prompt": """You are an expert content structure analyst. Given the content of a document, analyze its structure.
Provide:
1. A breakdown of the content's sections (with titles and key elements in each)
2. An analysis of the logical flow between sections
3. Suggestions for structural improvements

Return your analysis as a valid JSON object with these keys:
sections (a list of section objects with title and key_elements), flow_analysis (a string), suggestions (a list of strings)"""
    },
    "action_items": {
        "description": "Extract action items, deadlines, and responsibilities",
        "system_prompt": """You are an expert at extracting action items from text. Given the content of a document, identify all action items, deadlines, and responsible parties.
Provide:
1. A list of action items (with description, priority if mentioned, and context)
2. A list of deadlines mentioned (with the associated action and date)
3. A list of responsible parties (people or teams mentioned as responsible for actions)

Return your analysis as a valid JSON object with these keys:
action_items (a list of action item objects), deadlines (a list of deadline objects), responsible_parties (a list of strings)"""
    }
}


def truncate_text(text: str, max_tokens: int = 4000) -> str:
    """Truncate text to fit within token limits."""
    # Approximate tokens (4 chars per token is a rough estimate)
    max_chars = max_tokens * 4
    return text[:max_chars]


def analyze_content(
        file_path: Path,
        analysis_type: Literal[
            "sentiment", "entities", "key_points", "structure", "action_items"],
        model: str = "gpt-3.5-turbo"
) -> dict[str, Any]:
    """
    Perform specialized content analysis on a document.

    Args:
        file_path: Path to the document
        analysis_type: Type of analysis to perform
        model: LLM model to use

    Returns:
        Analysis results as a dictionary
    """
    try:
        # Check analysis type
        if analysis_type not in ANALYSIS_TYPES:
            return {"error": f"Invalid analysis type: {analysis_type}"}

        # Get system prompt
        system_prompt = ANALYSIS_TYPES[analysis_type]["system_prompt"]

        # Configure OpenAI
        setup_llm_environment()

        # Read the file
        text = file_path.read_text(encoding="utf-8")
        truncated_text = truncate_text(text)

        # Call the API
        logger.info(f"Performing {analysis_type} analysis...")
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": truncated_text},
            ],
            temperature=0.3,
            max_tokens=800,
        )

        # Parse the result
        raw_output = response.choices[0].message.content
        result = json.loads(raw_output)

        return result

    except OpenAIError as api_error:
        logger.error(f"OpenAI API error: {api_error}")
        return {"error": f"OpenAI API error: {str(api_error)}"}

    except json.JSONDecodeError as json_error:
        logger.error(f"Invalid JSON returned by LLM: {json_error}")
        return {"error": "Invalid JSON returned by the LLM"}

    except Exception as e:
        logger.exception(f"Error in {analysis_type} analysis")
        return {"error": f"Analysis failed: {str(e)}"}


def print_sentiment_analysis(result: dict[str, Any]) -> None:
    """Format and print sentiment analysis results."""
    print("\n===== SENTIMENT ANALYSIS =====")
    print(f"Polarity: {result.get('polarity', 'N/A')} ({result.get('valence', 'N/A')})")
    print(f"Confidence: {result.get('confidence', 'N/A')}")
    print(f"Dominant emotions: {', '.join(result.get('dominant_emotions', []))}")
    print("\nAnalysis:")
    print(result.get('analysis', 'N/A'))


def print_entity_extraction(result: dict[str, Any]) -> None:
    """Format and print entity extraction results."""
    print("\n===== ENTITY EXTRACTION =====")
    entities = result.get('entities', {})
    for entity_type, items in entities.items():
        print(f"\n{entity_type.upper()}:")
        for item in items:
            print(f"  - {item}")


def print_key_points(result: dict[str, Any]) -> None:
    """Format and print key points analysis."""
    print("\n===== KEY POINTS ANALYSIS =====")
    points = result.get('main_points', [])
    evidence = result.get('supporting_evidence', {})

    for i, point in enumerate(points, 1):
        print(f"\n{i}. {point}")
        if point in evidence:
            print("   Supporting evidence:")
            for item in evidence[point]:
                print(f"   - {item}")


def print_structure_analysis(result: dict[str, Any]) -> None:
    """Format and print structure analysis."""
    print("\n===== STRUCTURE ANALYSIS =====")
    sections = result.get('sections', [])

    print("Document structure:")
    for i, section in enumerate(sections, 1):
        title = section.get('title', f"Section {i}")
        elements = section.get('key_elements', [])
        print(f"\n{i}. {title}")
        for element in elements:
            print(f"   - {element}")

    print("\nFlow analysis:")
    print(result.get('flow_analysis', 'N/A'))

    print("\nSuggestions:")
    for suggestion in result.get('suggestions', []):
        print(f"- {suggestion}")


def print_action_items(result: dict[str, Any]) -> None:
    """Format and print action items extraction."""
    print("\n===== ACTION ITEMS EXTRACTION =====")

    print("Action items:")
    for i, item in enumerate(result.get('action_items', []), 1):
        print(f"\n{i}. {item.get('description', 'Unnamed action')}")
        if 'priority' in item:
            print(f"   Priority: {item['priority']}")
        if 'context' in item:
            print(f"   Context: {item['context']}")

    print("\nDeadlines:")
    for deadline in result.get('deadlines', []):
        print(
            f"- {deadline.get('action', 'Action')}: {deadline.get('date', 'No date')}")

    print("\nResponsible parties:")
    for party in result.get('responsible_parties', []):
        print(f"- {party}")


def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Advanced content analysis for text documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Analysis types:\n" +
               "\n".join(
                   [f"  {k}: {v['description']}" for k, v in ANALYSIS_TYPES.items()])
    )

    parser.add_argument(
        "analysis_type",
        choices=list(ANALYSIS_TYPES.keys()),
        help="Type of analysis to perform"
    )
    parser.add_argument(
        "file_path",
        help="Path to the document to analyze"
    )
    parser.add_argument(
        "--model",
        default="gpt-3.5-turbo",
        help="OpenAI model to use (default: gpt-3.5-turbo)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON"
    )

    args = parser.parse_args()
    file_path = Path(args.file_path)

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1

    # Perform the analysis
    print(f"Analyzing {file_path.name} with {args.analysis_type} analyzer...")
    result = analyze_content(
        file_path=file_path,
        analysis_type=args.analysis_type,  # type: ignore
        model=args.model
    )

    # Check for errors
    if "error" in result:
        logger.error(result["error"])
        return 1

    # Output the results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Format the output based on analysis type
        if args.analysis_type == "sentiment":
            print_sentiment_analysis(result)
        elif args.analysis_type == "entities":
            print_entity_extraction(result)
        elif args.analysis_type == "key_points":
            print_key_points(result)
        elif args.analysis_type == "structure":
            print_structure_analysis(result)
        elif args.analysis_type == "action_items":
            print_action_items(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())