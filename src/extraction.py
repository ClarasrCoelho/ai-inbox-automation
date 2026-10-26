"""Extract structured invoice data from text with an LLM.

Concepts: system prompt, temperature, structured outputs via tool use,
Pydantic validation and automatic retries when the response is invalid.
"""
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from src.llm import MODEL, client


class Invoice(BaseModel):
    supplier: str
    date: date
    total_amount: float = Field(gt=0, description="Total including VAT")
    currency: str = Field(min_length=3, max_length=3, description="ISO code, e.g. EUR")
    category: Literal["software", "travel", "supplies", "services", "other"]


# The "tool" forces the model to answer with JSON in this exact shape.
TOOL = {
    "name": "record_invoice",
    "description": "Records the data extracted from an invoice.",
    "input_schema": Invoice.model_json_schema(),
}


def extract_invoice(text: str, max_attempts: int = 3) -> Invoice:
    messages = [{"role": "user", "content": f"Extract the data from this invoice:\n\n{text}"}]

    for _ in range(max_attempts):
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            temperature=0,  # extraction: we want consistency, not creativity
            system=(
                "You are an accounting assistant. Always use the record_invoice "
                "tool. Dates must be in YYYY-MM-DD format."
            ),
            tools=[TOOL],
            tool_choice={"type": "tool", "name": "record_invoice"},
            messages=messages,
        )
        block = next(b for b in response.content if b.type == "tool_use")

        try:
            return Invoice.model_validate(block.input)
        except ValidationError as error:
            # Send the error back to the model so it can fix its answer.
            print(f"Invalid response, asking for a fix: {error.error_count()} error(s)")
            messages += [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "is_error": True,
                            "content": f"Invalid data, please fix: {error}",
                        }
                    ],
                },
            ]

    raise RuntimeError("Could not extract a valid invoice.")


if __name__ == "__main__":
    sample = """
    TechSoft Ltd — Invoice no. 2026/481
    Date: 14 October 2026
    Annual design software licence: €1,200.00
    VAT (23%): €276.00
    Total due: €1,476.00
    """
    invoice = extract_invoice(sample)
    print(json.dumps(invoice.model_dump(mode="json"), indent=2, ensure_ascii=False))
