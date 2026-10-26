"""Classify incoming emails with an LLM."""
import json
from typing import Literal

from pydantic import BaseModel, Field

from src.llm import call_structured


# Literal restricts each field to fixed values, so the model
# cannot invent a new category like "spam" or "payment".
class EmailClassification(BaseModel):
    category: Literal["invoice", "customer_request", "complaint", "other"]
    urgency: Literal["low", "medium", "high"]
    reason: str = Field(description="One short sentence explaining the decision")


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
- high: needs action within 1-2 days: threats to cancel, overdue payments,
  or a change that affects an order that has not shipped yet.
- medium: needs a reply this week.
- low: no action needed, or no deadline.

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
    # Quick evaluation on the sample emails, comparing with the expected labels.
    with open("data/sample_emails.json", encoding="utf-8") as f:
        emails = json.load(f)

    correct = 0
    for email in emails:
        result = classify_email(email["subject"], email["body"])
        ok = result.category == email["expected_category"]
        correct += ok
        print(f"{'OK  ' if ok else 'MISS'} {email['subject'][:40]:<40} -> {result.category} ({result.urgency})")
        print(f"     reason: {result.reason}")

    print(f"\nAccuracy: {correct}/{len(emails)}")
