# ai-inbox-automation

LLM-powered email workflow: classifies incoming messages, extracts invoice data,
summarizes requests and routes them, built with n8n, Python and FastAPI.

## The problem

<!-- 2-3 sentences, written for a non-technical client. Example:
A small company spends hours every week reading emails, copying invoice data
into spreadsheets and forwarding requests by hand. -->

## How it works

<!-- Diagram of the flow: email -> classification -> extraction / summary -> sheet + alerts -->

## Technical decisions

<!-- Structured outputs (tool use + Pydantic), temperature choices, retries,
webhooks between n8n and FastAPI, OAuth for Gmail / Google Sheets -->

## Evaluation

<!-- Results on the sample emails in data/sample_emails.json -->

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your API key
python -m src.extraction
python -m src.classification
```
