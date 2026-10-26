"""Shared LLM client and settings."""
import anthropic
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env

# Fast, cheap model, well suited to extraction and classification.
# Check the current name at https://docs.claude.com/en/api/overview
MODEL = "claude-haiku-5-5"

client = anthropic.Anthropic()
