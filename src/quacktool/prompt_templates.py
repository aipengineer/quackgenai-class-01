# src/quacktool/prompt_templates.py
"""
Simple prompt template system for building effective prompts.

This module provides utilities for creating, storing, and using
parameterized prompt templates for consistent LLM interactions.
"""

import json
import os
from pathlib import Path
from string import Template
from typing import Any, Optional

from pydantic import BaseModel, Field

# Define the base template location
DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"


class PromptTemplate(BaseModel):
    """A parameterized prompt template."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template: str = Field(...,
                          description="Template string with $parameter placeholders")
    parameters: dict[str, str] = Field(default_factory=dict,
                                       description="Parameter descriptions")
    system_message: Optional[str] = Field(None,
                                          description="System message to use with this template")
    tags: list[str] = Field(default_factory=list,
                            description="Tags for organizing templates")
    examples: list[dict[str, Any]] = Field(default_factory=list,
                                           description="Example usages of the template")
    version: str = Field(default="1.0", description="Template version")

    def format(self, **kwargs: Any) -> str:
        """
        Format the template with the provided parameters.

        Args:
            **kwargs: Parameter values to substitute

        Returns:
            Formatted prompt string
        """
        template = Template(self.template)
        return template.safe_substitute(**kwargs)

    def to_chat_messages(self, **kwargs: Any) -> list[dict[str, str]]:
        """
        Convert the template to chat messages format for OpenAI API.

        Args:
            **kwargs: Parameter values to substitute

        Returns:
            list of message dictionaries
        """
        messages = []

        # Add system message if present
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})

        # Add user message with formatted template
        messages.append({"role": "user", "content": self.format(**kwargs)})

        return messages

    def save(self, directory: Optional[Path] = None) -> Path:
        """
        Save the template to a file.

        Args:
            directory: Directory to save to (defaults to the default template directory)

        Returns:
            Path to the saved template file
        """
        directory = directory or DEFAULT_TEMPLATE_DIR
        directory.mkdir(parents=True, exist_ok=True)

        # Create a safe filename
        safe_name = self.name.lower().replace(" ", "_")
        file_path = directory / f"{safe_name}.json"

        # Save as JSON
        with open(file_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

        return file_path


class TemplateManager:
    """Manager for prompt templates."""

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the template manager.

        Args:
            template_dir: Directory containing templates
        """
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self.templates: dict[str, PromptTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the template directory."""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            return

        for file_path in self.template_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    template_data = json.load(f)
                    template = PromptTemplate(**template_data)
                    self.templates[template.name] = template
            except Exception as e:
                print(f"Error loading template {file_path}: {e}")

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            PromptTemplate if found, None otherwise
        """
        return self.templates.get(name)

    def list_templates(self) -> list[dict[str, Any]]:
        """
        list all available templates.

        Returns:
            list of template summaries
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": list(t.parameters.keys()),
                "tags": t.tags,
                "version": t.version,
            }
            for t in self.templates.values()
        ]

    def save_template(self, template: PromptTemplate) -> Path:
        """
        Save a template and add it to the manager.

        Args:
            template: Template to save

        Returns:
            Path to the saved template file
        """
        file_path = template.save(self.template_dir)
        self.templates[template.name] = template
        return file_path

    def remove_template(self, name: str) -> bool:
        """
        Remove a template.

        Args:
            name: Template name

        Returns:
            True if removed, False if not found
        """
        if name not in self.templates:
            return False

        template = self.templates[name]
        safe_name = template.name.lower().replace(" ", "_")
        file_path = self.template_dir / f"{safe_name}.json"

        if file_path.exists():
            os.remove(file_path)

        del self.templates[name]
        return True

    def filter_by_tags(self, tags: list[str]) -> list[PromptTemplate]:
        """
        Filter templates by tags.

        Args:
            tags: list of tags to filter by

        Returns:
            list of matching templates
        """
        return [
            template
            for template in self.templates.values()
            if any(tag in template.tags for tag in tags)
        ]


# Create and populate the default template directory with example templates
def initialize_default_templates() -> None:
    """Create and initialize default prompt templates."""
    default_dir = DEFAULT_TEMPLATE_DIR
    default_dir.mkdir(parents=True, exist_ok=True)

    # Only create templates if directory is empty
    if list(default_dir.glob("*.json")):
        return

    # Create example templates
    templates = [
        # Document Summarization Template
        PromptTemplate(
            name="Document Summary",
            description="Summarize a document with key points and main ideas",
            system_message="You are an expert document summarizer. Your task is to create concise, accurate summaries that capture the most important information and main ideas.",
            template="Please summarize the following document, focusing on the key points, main arguments, and important conclusions. Keep the summary clear and concise.\n\n$document",
            parameters={
                "document": "The full text of the document to summarize"
            },
            tags=["summarization", "content", "general"],
            examples=[
                {
                    "parameters": {
                        "document": "This is a sample document that discusses climate change..."
                    },
                    "output": "This document explores the causes and impacts of climate change..."
                }
            ]
        ),

        # Code Review Template
        PromptTemplate(
            name="Code Review",
            description="Analyze code for bugs, improvements, and best practices",
            system_message="You are an expert software engineer conducting a thorough code review. Focus on identifying bugs, security vulnerabilities, performance issues, and opportunities for improvement.",
            template="Please review the following $language code for potential issues, bugs, security vulnerabilities, and areas for improvement. Focus on both functionality and adherence to best practices.\n\n```$language\n$code\n```",
            parameters={
                "language": "The programming language of the code",
                "code": "The code to review"
            },
            tags=["programming", "code", "review"],
            examples=[
                {
                    "parameters": {
                        "language": "python",
                        "code": "def calculate_average(numbers):\n    total = 0\n    for num in numbers:\n        total += num\n    return total / len(numbers)"
                    },
                    "output": "The code correctly calculates an average but doesn't handle empty lists which would cause a division by zero error..."
                }
            ]
        ),

        # Data Analysis Template
        PromptTemplate(
            name="Data Analysis",
            description="Analyze and extract insights from structured data",
            system_message="You are a data analysis expert skilled at interpreting data and extracting meaningful insights. Focus on patterns, anomalies, and actionable conclusions.",
            template="Below is a dataset in $format format. Please analyze this data and provide insights on:\n1. Key trends and patterns\n2. Notable anomalies or outliers\n3. Meaningful correlations or relationships\n4. Actionable insights for business decisions\n\n$data",
            parameters={
                "format": "The format of the data (CSV, JSON, etc.)",
                "data": "The structured data to analyze"
            },
            tags=["data", "analysis", "business"],
            examples=[
                {
                    "parameters": {
                        "format": "CSV",
                        "data": "date,revenue,customers\n2023-01-01,5000,120\n2023-01-02,5200,125\n..."
                    },
                    "output": "Analysis of the sales data reveals a clear upward trend in both revenue and customer count..."
                }
            ]
        ),

        # Content Classification Template
        PromptTemplate(
            name="Content Classification",
            description="Classify content into predefined categories",
            system_message="You are a content classification expert. Your task is to accurately categorize content based on its characteristics and subject matter.",
            template="Please classify the following content into the most appropriate category from the list provided. Explain your reasoning briefly.\n\nCategories: $categories\n\nContent to classify:\n$content",
            parameters={
                "categories": "Comma-separated list of classification categories",
                "content": "The content to classify"
            },
            tags=["classification", "content", "categorization"],
            examples=[
                {
                    "parameters": {
                        "categories": "Technology, Business, Health, Entertainment, Politics",
                        "content": "Apple announced its new iPhone model yesterday, featuring improvements to the camera system and battery life."
                    },
                    "output": "Category: Technology\nReasoning: The content describes a product announcement from a technology company (Apple) about a technological device (iPhone)."
                }
            ]
        ),

        # Product Description Generator
        PromptTemplate(
            name="Product Description",
            description="Generate compelling product descriptions for e-commerce",
            system_message="You are a skilled copywriter specializing in e-commerce product descriptions. Create compelling, accurate, and SEO-friendly product descriptions that highlight benefits and features.",
            template="Please write a compelling product description for an e-commerce site based on the following information:\n\nProduct Name: $name\nProduct Category: $category\nKey Features: $features\nTarget Audience: $audience\nPrice Point: $price\nBrand Tone: $tone",
            parameters={
                "name": "The name of the product",
                "category": "The product category",
                "features": "The key features and specifications",
                "audience": "Description of the target customers",
                "price": "Price point (budget, mid-range, premium)",
                "tone": "The brand's tone of voice"
            },
            tags=["marketing", "e-commerce", "copywriting"],
            examples=[
                {
                    "parameters": {
                        "name": "UltraFlex Pro Running Shoes",
                        "category": "Athletic Footwear",
                        "features": "Lightweight mesh upper, responsive foam cushioning, durable rubber outsole, reflective elements",
                        "audience": "Serious runners aged 25-45",
                        "price": "Premium ($120-150)",
                        "tone": "Professional, performance-focused, inspiring"
                    },
                    "output": "Elevate your running performance with the UltraFlex Pro Running Shoes, engineered for serious athletes who demand excellence..."
                }
            ]
        ),

        # Chain of Thought Reasoning
        PromptTemplate(
            name="Chain of Thought Reasoning",
            description="Solve complex problems using step-by-step reasoning",
            system_message="You are an expert problem solver with a methodical approach. Break down complex problems into step-by-step reasoning to arrive at well-reasoned conclusions.",
            template="Please solve the following $domain problem. Use chain-of-thought reasoning to work through the solution step by step, explaining your thought process clearly.\n\nProblem: $problem",
            parameters={
                "domain": "The problem domain (e.g., math, logic, business)",
                "problem": "The problem statement to solve"
            },
            tags=["reasoning", "problem-solving", "step-by-step"],
            examples=[
                {
                    "parameters": {
                        "domain": "mathematical",
                        "problem": "A store is offering a 20% discount on a product that originally costs $85. There is also a 5% sales tax applied after the discount. What is the final price?"
                    },
                    "output": "I'll solve this step by step:\n1. Original price: $85\n2. 20% discount: $85 × 0.20 = $17\n3. Discounted price: $85 - $17 = $68\n4. 5% sales tax: $68 × 0.05 = $3.40\n5. Final price: $68 + $3.40 = $71.40\nTherefore, the final price is $71.40."
                }
            ]
        )
    ]

    # Save each template
    for template in templates:
        template.save(default_dir)
        print(f"Created template: {template.name}")