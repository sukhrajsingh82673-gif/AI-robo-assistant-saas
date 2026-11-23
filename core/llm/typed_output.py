"""
ZONATA Universal AI Operating System — Pydantic Typed Output Schema Validator
Enforces Rule 16: Model output is a proposal. Every action-driving output must strictly validate.
"""

import json
import logging
import re
from typing import Type, TypeVar, Tuple, Optional
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("zonata.llm.typed_output")

T = TypeVar("T", bound=BaseModel)


class LLMOutputValidationError(ValueError):
    """Raised when an LLM fails schema validation after the allowed retry."""
    def __init__(self, schema_name: str, raw_output: str, validation_error: str):
        self.schema_name = schema_name
        self.raw_output = raw_output
        self.validation_error = validation_error
        super().__init__(
            f"LLM output failed validation against schema '{schema_name}': {validation_error}"
        )


def clean_json_text(raw_text: str) -> str:
    """Extract and clean JSON payload from markdown fences or surrounding chatter."""
    text = raw_text.strip()
    # Strip ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return text


def parse_and_validate(raw_text: str, schema_cls: Type[T]) -> Tuple[Optional[T], Optional[str]]:
    """Parse JSON and validate against the provided Pydantic model.
    
    Returns (validated_instance, None) on success, or (None, error_message) on failure.
    """
    cleaned = clean_json_text(raw_text)
    try:
        data = json.loads(cleaned)
    except Exception as e:
        return None, f"Invalid JSON syntax: {e}"

    if not isinstance(data, dict):
        return None, f"Expected JSON object, got {type(data).__name__}"

    try:
        instance = schema_cls.parse_obj(data)
        return instance, None
    except ValidationError as ve:
        return None, str(ve)
    except Exception as e:
        return None, f"Validation exception: {e}"
