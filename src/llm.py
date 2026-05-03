import os
import time
from functools import lru_cache
from typing import Dict, List, Optional

from src.retriever import RetrievedChunk

try:
    import google.genai as genai 
except Exception: 
    genai = None 

try:
    import google.generativeai as legacy_genai 
except Exception:
    legacy_genai = None


SYSTEM_PROMPT = """You are a GitLab knowledge assistant.
Answer only from the provided context snippets from GitLab Handbook/Direction pages.
If the answer is uncertain or missing, clearly say you do not have enough context.
Always keep the response concise and practical for employees or candidates.
"""


@lru_cache(maxsize=1)
def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your environment or .env file."
        )
    return key


def _get_model_candidates() -> List[str]:
    preferred = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    return [
        preferred,
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-pro",
    ]


@lru_cache(maxsize=1)
def _get_usable_new_sdk_models() -> List[str]:
    """Fetch models that support generateContent for current API key"""
    if genai is None:
        return []

    client = genai.Client(api_key=_get_api_key())  
    usable_models: List[str] = []

    for model in client.models.list():
        actions = getattr(model, "supported_actions", []) or []

        if "generateContent" not in actions:
            continue

        name = getattr(model, "name", None)
        if name:
            usable_models.append(str(name))

    return usable_models


def _select_preferred_model(available: List[str]) -> str:
    if not available:
        raise RuntimeError("No usable Gemini models found for generateContent.")

    override = os.getenv("GEMINI_MODEL", "").strip()
    if override:
        target = override if override.startswith("models/") else f"models/{override}"

        if target in available:
            return target

        suffix = target.split("models/")[-1]
        for name in available:
            if name.endswith(suffix):
                return name

    priority = [
        "models/gemini-2.5-flash",
        "models/gemini-2.5-pro",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-pro",
    ]

    for candidate in priority:
        if candidate in available:
            return candidate

    return available[0]


def _build_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return ""

    lines = []
    for entry in history[-6:]:  
        role = entry.get("role", "user").title()
        content = entry.get("content", "")
        lines.append(f"{role}: {content}")

    return "\n".join(lines)




def build_prompt(
    question: str,
    chunks: List[RetrievedChunk],
    history: List[Dict[str, str]],
) -> str:
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Source {i}] URL: {chunk.url}\nContent: {chunk.content}"
        )
    context = "\n\n".join(context_blocks)
    history_text = _build_history(history)

    return (
        f"{SYSTEM_PROMPT}\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        "Provide:\n"
        "1) Direct answer.\n"
        "2) 2-4 key points.\n"
        "3) Mention uncertainty if needed.\n"
    )


def _generate_answer_new_sdk(
    prompt: str,
    model_candidates: List[str],
) -> str:
    client = genai.Client(api_key=_get_api_key())  
    usable_models = _get_usable_new_sdk_models()
    # build prioritized model list
    preferred_order: List[str] = []
    for p in [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.5-pro",
        "models/gemini-2.0-pro",
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro",
    ]:
        if p in usable_models:
            preferred_order.append(p)
    for m in usable_models:
        if m not in preferred_order:
            preferred_order.append(m)

    last_exc: Optional[Exception] = None

    def is_unavailable_503(exc: Exception) -> bool:
        msg = str(exc).lower()
        return "503" in msg or "unavailable" in msg or "high demand" in msg

   # try multiple models with retry fallback
    for model_name in preferred_order:
        for attempt in range(2):  
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                text = getattr(resp, "text", None)
                if text:
                    return str(text).strip()
                return str(resp).strip()
            except Exception as exc:
                last_exc = exc
                if is_unavailable_503(exc) and attempt == 0:
                    time.sleep(1.5)
                    continue
                break

    raise RuntimeError(
        f"Gemini generation failed (all models). Last error: {last_exc}"
    )


def _generate_answer_legacy_sdk(
    prompt: str,
    model_candidates: List[str],
) -> str:
    legacy_genai.configure(api_key=_get_api_key()) 
    last_exc: Optional[Exception] = None
    for model_name in model_candidates:
        try:
            model = legacy_genai.GenerativeModel(model_name) 
            response = model.generate_content(prompt)
            return (getattr(response, "text", "") or "").strip()
        except Exception as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"Gemini generation failed with all model candidates. Last error: {last_exc}")


def generate_answer(
    question: str,
    chunks: List[RetrievedChunk],
    history: List[Dict[str, str]] | None = None,
) -> str:
    prompt = build_prompt(question, chunks, history or [])
    model_candidates = _get_model_candidates()

  # use new SDK if available
    if genai is not None:
        return _generate_answer_new_sdk(prompt, model_candidates)

# fallback to legacy SDK
    if legacy_genai is not None:
        return _generate_answer_legacy_sdk(prompt, model_candidates)

    raise RuntimeError(
        "No Gemini SDK available. Install `google-genai` or `google-generativeai`."
    )
