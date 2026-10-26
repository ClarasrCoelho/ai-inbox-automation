"""Classify incoming emails with an LLM."""
import json
from typing import Literal

from pydantic import BaseModel, Field

from src.llm import call_structured


# Literal restricts each field to fixed values, so the model
# cannot invent a new category like "spam" or "payment".
class EmailClassification(BaseModel):
    reason: str = Field(description="First, briefly explain what the email is about and which rules apply")
    category: Literal["invoice", "customer_request", "complaint", "other"]
    urgency: Literal["low", "medium", "high"]


# Clear definitions and explicit rules for the ambiguous cases
# are what make the classification accurate.
SYSTEM_PROMPT = """You classify incoming business emails for a small company.

Categories:
- invoice: the email is about a bill or payment: a new invoice, a payment
  reminder or an overdue notice. A payment reminder is an invoice, even if
  the tone is firm.
- customer_request: a customer asks for something: a quote, information,
  or a change to an order or delivery.
- complaint: a customer is unhappy with a product or service and expects
  it to be fixed.
- other: anything else (internal messages, newsletters, social events).

Urgency:
- high: needs action within 1-2 days: threats to cancel or take legal action,
  overdue payments, explicit deadlines of 1-2 days, or a change that affects
  an order that has not shipped yet.
- medium: needs a reply or action this week.
- low: no action needed, or the deadline is more than a week away.
  Marketing or spam with fake urgency is always low.

Examples:
- A new invoice payable in 30 days -> low.
- An overdue payment notice, in any language -> high.
- A change to an order that has not shipped yet -> high.

Always use the classify_email tool."""


def classify_email(subject: str, body: str) -> EmailClassification:
    return call_structured(
        output_model=EmailClassification,
        system=SYSTEM_PROMPT,
        user=f"Subject: {subject}\n\n{body}",
        tool_name="classify_email",
        tool_description="Records the category and urgency of an incoming email.",
        temperature=0,  # the same email should always get the same label
    )


if __name__ == "__main__":
    # Quick demo on a single email. For the full evaluation: python -m src.evaluate
    result = classify_email(
        "Reminder: payment overdue",
        "Our invoice 1187 of €340.50 is now 25 days overdue. Please arrange payment.",
    )
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
