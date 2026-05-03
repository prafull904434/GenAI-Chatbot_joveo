from functools import lru_cache

from backend.schemas.chat import ChatRequest, ChatResponse, Source
from backend.core.guardrails import guardrail

from backend.src.llm import generate_answer
from backend.src.retriever import EmbeddingRetriever


def build_fallback_answer(question: str, chunks, exc: Exception | None = None) -> str:
    if not chunks:
        return (
            "I could not find matching GitLab handbook or direction content for that question yet. "
            "Try rephrasing the question or rebuilding the index with more pages."
        )

    top = chunks[0]
    snippet = top.content[:700].strip()

    exc_str = str(exc).lower() if exc else ""

    if "503" in exc_str or "unavailable" in exc_str or "high demand" in exc_str:
        prefix = "Gemini is temporarily unavailable. Showing retrieved context instead."
    else:
        prefix = "Gemini generation failed. Showing retrieved context instead."

    return prefix + "\n\n" + snippet


@lru_cache(maxsize=1)
def get_retriever() -> EmbeddingRetriever:
    return EmbeddingRetriever()


def handle_chat(request: ChatRequest) -> ChatResponse:
    message = guardrail(request.question)      # early exit if request violates guardrails
    if message:
        return ChatResponse(answer=message, sources=[])

    try:
        retriever = get_retriever()
        chunks = retriever.search(request.question, k=request.top_k)

    except FileNotFoundError:
        return ChatResponse(
            answer=(
                "The backend is running, but the search index is missing. "
                "Run `python -m src.ingest --max-pages 120` from the project root first."
            ),
            sources=[],
        )

    except Exception as e:
        return ChatResponse(
            answer=f"Error during search: {e}",
            sources=[],
        )

  # aggregate unique sources with highest relevance score
    source_map = {}
    for chunk in chunks:
        source_map[chunk.url] = max(source_map.get(chunk.url, 0.0), chunk.score)

    sources = [Source(url=url, score=score) for url, score in source_map.items()]
    sources.sort(key=lambda x: x.score, reverse=True)

    try:
        answer = generate_answer(request.question, chunks, history=request.history)

    except RuntimeError as exc:
        if "Missing GEMINI_API_KEY" in str(exc):
            return ChatResponse(
                answer=(
                    "Gemini generation failed because the API key is missing/invalid.\n\n"
                    "Set `GEMINI_API_KEY` in `.env`, then restart the backend."
                ),
                sources=sources[:5],
            )

        answer = build_fallback_answer(request.question, chunks, exc)

    except Exception as exc:
        answer = build_fallback_answer(request.question, chunks, exc)

    return ChatResponse(answer=answer, sources=sources[:5])