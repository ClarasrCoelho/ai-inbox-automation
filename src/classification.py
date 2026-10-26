"""Classify incoming emails with an LLM.

YOUR TASK: complete the TODOs below. Use src/extraction.py as a reference:
the pattern (tool + tool_choice + Pydantic validation + retries) is the same.
"""
import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from src.llm import MODEL, client


class EmailClassification(BaseModel):
    category: Literal["invoice", "customer_request", "complaint", "other"]
    urgency: Literal["low", "medium", "high"]
    reason: str = Field(description="One short sentence explaining the decision")


# TODO 1: define the tool, like TOOL in extraction.py.
#   Hint: the schema comes from EmailClassification.model_json_schema().
TOOL = None


def classify_email(subject: str, body: str, max_attempts: int = 3) -> EmailClassification:
    # TODO 2: write a system prompt that defines each category and each urgency
    #   level clearly. This is where most of the accuracy comes from.
    #   Think: what makes an email "high" urgency? Is a late invoice a complaint?
    system_prompt = ""

    # TODO 3: call client.messages.create(...) forcing your tool,
    #   validate the result with EmailClassification.model_validate(...)
    #   and retry on ValidationError (same loop as extraction.py).
    #   Question to think about: which temperature should you use here, and why?
    raise NotImplementedError


if __name__ == "__main__":
    # Quick test on the sample emails, comparing with the expected labels.
    with open("data/sample_emails.json", encoding="utf-8") as f:
        emails = json.load(f)

    correct = 0
    for email in emails:
        result = classify_email(email["subject"], email["body"])
        ok = result.category == email["expected_category"]
        correct += ok
        print(f"{'OK  ' if ok else 'MISS'} {email['subject'][:40]:<40} -> {result.category} ({result.urgency})")

    print(f"\nAccuracy: {correct}/{len(emails)}")
