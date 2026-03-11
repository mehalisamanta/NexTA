"""
backend/openai_client.py

"""

import os
import streamlit as st
from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-mini"

# Module-level cached client — initialised once, reused for every call
_client: OpenAI | None = None


def _get_api_key() -> str:
    """
    Read the API key from environment or Streamlit secrets.
    Priority: environment variable → Streamlit secrets.
    Raises a clear error if neither is set.
    """
    # 1. Standard environment variable (.env loaded by python-dotenv in app.py)
    key = os.getenv("OPENAI_API_KEY", "")

    # 2. Streamlit secrets (used on Streamlit Cloud)
    if not key:
        try:
            key = st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            pass

    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set.\n"
            "• Local dev  : add OPENAI_API_KEY=sk-... to your .env file\n"
            "• Streamlit Cloud : add it under Settings → Secrets"
        )
    return key


def init_openai_client() -> OpenAI:
    """
    Initialise the OpenAI client from environment / Streamlit secrets.

    """
    global _client
    if _client is None:
        _client = OpenAI(api_key=_get_api_key())
    return _client


def create_openai_completion(
    client: OpenAI,
    messages: list,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 1000,
) -> object:
    """
    Thin wrapper around client.chat.completions.create.
    Returns the full ChatCompletion object so callers can do:
        resp.choices[0].message.content
    """
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )