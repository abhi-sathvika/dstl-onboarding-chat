import os
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv
from openai import OpenAI

# Try to load backend/.env explicitly (so local .env is respected)
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))
else:
    load_dotenv()


def _make_client() -> OpenAI:
    api_key = os.environ.get("NRP_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("NRP_API_KEY / OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key, base_url="https://ellm.nrp-nautilus.io/v1")


def generate_llm_response(messages: List[dict[str, Any]], model: str = "gemma3") -> str:
    """Generate a response from the NRP LLM using the provided conversation messages."""
    client = _make_client()
    # call the NRP chat completions API
    completion = client.chat.completions.create(model=model, messages=messages)  # type: ignore

    # Try to extract content robustly across client versions
    try:
        response_content = completion.choices[0].message.content
    except Exception:
        response_content = getattr(completion.choices[0].message, "content", None)

    if response_content is None:
        raise ValueError("LLM returned empty response")

    return response_content
