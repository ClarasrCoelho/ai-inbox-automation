"""Extract structured invoice data from text with an LLM."""
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.llm import call_structured


class Invoice(BaseModel):
    supplier: str | None = Field(default=None, description="Company that issued the invoice, or null if not stated")
    date: date
    total_amount: float = Field(gt=0, description="Total including VAT")
    currency: str = Field(min_length=3, max_length=3, description="ISO code, e.g. EUR")
    category: Literal["software", "travel", "supplies", "services", "other"]




def extract_invoice(text: str) -> Invoice:
    system = (
        f"You are an accounting assistant. Today is {date.today().isoformat()}. "
        "Extract the invoice data and always use the record_invoice tool. "
        "Dates must be in YYYY-MM-DD format; if the year is missing, use the most recent past date. "
        "Never invent information: if the supplier is not stated, use null."
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
