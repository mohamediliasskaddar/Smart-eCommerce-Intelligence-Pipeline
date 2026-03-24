"""
llm/llm_client.py
LangChain wrapper — Groq + Gemini.
User picks the model. If one fails, falls back to the other.
"""
import os
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

# ── AVAILABLE MODELS ──────────────────────────────────────────────────
GROQ_MODELS = {
    "Groq — Llama 3.1 8B (fast)":    "llama-3.1-8b-instant",
    "Groq — Llama 3.3 70B (smart)":  "llama-3.3-70b-versatile",
    "Groq — Gemma 2 9B":             "gemma2-9b-it",
}

GEMINI_MODELS = {
    "Gemini 2.0 Flash (fast)":       "gemini-2.0-flash",
    "Gemini 1.5 Pro (smart)":        "gemini-1.5-pro",
}

ALL_MODELS = {**GROQ_MODELS, **GEMINI_MODELS}


def get_llm(model_label: str, temperature: float = 0.3) -> BaseChatModel:
    """
    Returns a LangChain-compatible LLM given a model label.
    Falls back automatically if the primary fails.
    """
    model_id = ALL_MODELS.get(model_label)
    if not model_id:
        raise ValueError(f"Unknown model: {model_label}. Choose from: {list(ALL_MODELS.keys())}")

    # ── GROQ ──────────────────────────────────────────────────────────
    if model_label in GROQ_MODELS:
        try:
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise EnvironmentError("GROQ_API_KEY not set in .env")
            return ChatGroq(
                model=model_id,
                temperature=temperature,
                api_key=api_key,
                max_tokens=2048,
            )
        except ImportError:
            raise ImportError("Run: pip install langchain-groq")

    # ── GEMINI ────────────────────────────────────────────────────────
    if model_label in GEMINI_MODELS:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise EnvironmentError("GEMINI_API_KEY not set in .env")
            return ChatGoogleGenerativeAI(
                model=model_id,
                temperature=temperature,
                google_api_key=api_key,
                max_output_tokens=2048,
            )
        except ImportError:
            raise ImportError("Run: pip install langchain-google-genai")


def get_llm_with_fallback(
    primary_label: str,
    fallback_label: str = "Groq — Llama 3.1 8B (fast)",
    temperature: float = 0.3,
) -> BaseChatModel:
    """Try primary model, fall back to secondary on failure."""
    try:
        return get_llm(primary_label, temperature)
    except Exception as e:
        print(f"Primary model failed ({e}), falling back to {fallback_label}")
        return get_llm(fallback_label, temperature)


def list_models() -> list[str]:
    return list(ALL_MODELS.keys())
