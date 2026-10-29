"""Shared, provider-agnostic LLM helper.

Uses the OpenAI SDK against any OpenAI-compatible endpoint (Gemini, Ollama,
OpenAI...). To switch provider, edit .env; no code changes are needed.
"""
import os
from typing import TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value or value == "your-key-here":
        raise RuntimeError(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return value


MODEL = _require("LLM_MODEL")
client = OpenAI(
    api_key=_require("LLM_API_KEY"),
    base_url=_require("LLM_BASE_URL"),
    timeout=180,
    max_retries=5,
)
T = TypeVar("T", bound=BaseModel)

# Some providers reject these JSON Schema keys in tool definitions.
# Pydantic still enforces the rules (e.g. gt=0) when we validate the answer.
_UNSUPPORTED_SCHEMA_KEYS = {"title", "exclusiveMinimum", "exclusiveMaximum"}


def _clean_schema(schema):
    if isinstance(schema, dict):
        return {k: _clean_schema(v) for k, v in schema.items() if k not in _UNSUPPORTED_SCHEMA_KEYS}
    if isinstance(schema, list):
        return [_clean_schema(v) for v in schema]
    return schema


def call_structured(
    output_model: type[T],
    system: str,
    user: str,
    tool_name: str,
    tool_description: str,
    temperature: float = 0,
    max_attempts: int = 3,
    seed: int | None = 42,
) -> T:
    """Ask the LLM for an answer shaped like `output_model`, using function calling.

    1. The Pydantic model becomes the tool's parameters (JSON Schema).
    2. tool_choice="required" forces the model to call the tool.
    3. The arguments are validated; on error, the model is told what to fix.
    """
    tool = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_description,
            "parameters": _clean_schema(output_model.model_json_schema()),
        },
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for _ in range(max_attempts):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=[tool],
            tool_choice="required",
            temperature=temperature,
            seed=seed,
        )
        message = response.choices[0].message

        # The model answered in free text instead of calling the tool.
        if not message.tool_calls:
            messages += [
                {"role": "assistant", "content": message.content or ""},
                {"role": "user", "content": f"Please answer by calling the {tool_name} tool."},
            ]
            continue

        call = message.tool_calls[0]
        try:
            # Arguments arrive as a JSON string; this parses AND validates.
            return output_model.model_validate_json(call.function.arguments)
        except ValidationError as error:
            print(f"Invalid response, asking for a fix: {error.error_count()} error(s)")
            print(f"  raw arguments: {call.function.arguments}")
            print(f"  error: {error}")
            messages += [
                message.model_dump(exclude_none=True),
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": (
                        f"Invalid data, please fix: {error}\n"
                        "Include every field. If a value is not stated in the text, "
                        "set it explicitly to null. Never make up a value to pass validation."
                    ),
                },
            ]

    raise RuntimeError(f"Could not get a valid {output_model.__name__} after {max_attempts} attempts.")
