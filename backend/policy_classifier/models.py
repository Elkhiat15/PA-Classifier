"""LLM factories for the policy alignment classifier."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI

from policy_classifier.schemas import PolicyDecision

load_dotenv()

def build_model(
    provider: str = "gemini",
    *,
    google_api_key: str | None = None,
    mistral_api_key: str | None = None,
    groq_api_key: str | None = None,
):
    """Build a chat model for the given provider at temperature 0."""
    llm = ChatGoogleGenerativeAI(
            # model="gemini-3.5-flash",
            model="gemini-3.1-flash-lite",
            temperature=0,
            google_api_key=google_api_key or os.environ.get("GOOGLE_API_KEY"),
        )
    if provider == "mistral":
        llm = ChatMistralAI(
            model="ministral-8b-2512",
            temperature=0,
            api_key=mistral_api_key or os.environ.get("MISTRAL_API_KEY"),
        )
    if provider == "groq":
        llm= ChatGroq(
            model="qwen/qwen3.8-27b",
            temperature=0,
            api_key=groq_api_key or os.environ.get("GROQ_API_KEY"),
        )
    return llm.with_structured_output(PolicyDecision)  
    # raise ValueError(f"Unknown provider: {provider!r}")


def structured_models(
    *,
    google_api_key: str | None = None,
    mistral_api_key: str | None = None,
    groq_api_key: str | None = None,
) -> dict:
    """Return the structured-output models for every supported provider."""
    models = {}
    for provider in ("gemini", "mistral", "groq"):
        llm = build_model(
            provider,
            google_api_key=google_api_key,
            mistral_api_key=mistral_api_key,
            groq_api_key=groq_api_key,
        )
        models[provider] = llm.with_structured_output(PolicyDecision)
    return models