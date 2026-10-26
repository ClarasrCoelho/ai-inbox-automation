"""HTTP API used by the n8n workflow.

Run locally:  uvicorn src.api:app --reload --port 8000
Interactive docs: http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.classification import EmailClassification, classify_email
from src.extraction import Invoice, extract_invoice

app = FastAPI(
    title="AI Inbox Automation",
    description="Classifies emails and extracts invoice data with an LLM.",
)


class EmailIn(BaseModel):
    subject: str = ""
    body: str


@app.get("/health")
def health() -> dict:
    """Lets n8n (or you) check that the service is running."""
    return {"status": "ok"}


@app.post("/classify", response_model=EmailClassification)
def classify(email: EmailIn) -> EmailClassification:
    try:
        return classify_email(email.subject, email.body)
    except Exception as error:
        # 502 = the service is fine, but the LLM behind it failed.
        raise HTTPException(status_code=502, detail=f"LLM error: {error}")


@app.post("/extract-invoice", response_model=Invoice)
def extract(email: EmailIn) -> Invoice:
    try:
        return extract_invoice(f"Subject: {email.subject}\n\n{email.body}")
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"LLM error: {error}")
