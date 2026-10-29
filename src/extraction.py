"""Extract structured invoice data from text with an LLM."""
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.llm import call_structured


class Invoice(BaseModel):
    supplier: str | None = Field(description="Company that issued the invoice, or null if not stated")
    invoice_number: str | None = Field(description="Invoice identifier as written, e.g. '2026/481' or '4521', or null if not stated")
    invoice_date: date | None = Field(description="Date the invoice was issued, or null if not stated")
    due_date: date | None = Field(
        description="Explicit payment deadline date, e.g. 'due on 15 October' or 'pay by 2026-11-01'. "
                    "'Total due' is an amount, not a date. Null if no deadline date is written.",
    )
    total_amount: float = Field(gt=0, description="Total including VAT")
    currency: str = Field(min_length=3, max_length=3, description="ISO code, e.g. EUR")
    category: Literal["software", "travel", "supplies", "services", "other"]

def extract_invoice(text: str, reference_date: date | None = None) -> Invoice:
    ref = reference_date or date.today()
    system = (
        f"You are an accounting assistant. The document was received on {ref.isoformat()}. "
        "Extract the invoice data and always use the record_invoice tool. "
        "Dates must be in YYYY-MM-DD format; if the year is missing, use the most recent date "
        "on or before the received date for invoice_date, and the nearest matching date for due_date. "
        "invoice_date is when the invoice was issued; due_date is the payment deadline. "
        "Do not copy one into the other: if only one is stated, set the other to null. "
        "Extract every field that is stated in the text. "
        "Use null only when a field is truly absent; never invent values."
    )
    return call_structured(
        output_model=Invoice,
        system=system,
        user=f"Extract the data from this invoice:\n\n{text}",
        tool_name="record_invoice",
        tool_description="Records the data extracted from an invoice.",
        temperature=0,  # extraction: we want consistency, not creativity
    )


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