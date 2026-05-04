from backend.schemas.chat import ChatRequest, ChatResponse, Source
from backend.core.guardrails import guardrail
from backend.src.llm import generate_answer
from backend.src.retriever import EmbeddingRetriever


_retriever = None


def get_retriever() -> EmbeddingRetriever:
    global _retriever
    if _retriever is None:
        _retriever = EmbeddingRetriever()
    return _retriever


def reset_retriever():
    """Call this after ingestion so the retriever reloads the new index."""
    global _retriever
    _retriever = None


def handle_chat(request: ChatRequest) -> ChatResponse:
    message = guardrail(request.question)
    if message:
        return ChatResponse(answer=message, sources=[])

    retriever = get_retriever()
    chunks = retriever.search(request.question, k=request.top_k)

    # aggregate unique sources with highest relevance score
    source_map = {}
    for chunk in chunks:
        source_map[chunk.url] = max(source_map.get(chunk.url, 0.0), chunk.score)

    sources = [Source(url=url, score=score) for url, score in source_map.items()]
    sources.sort(key=lambda x: x.score, reverse=True)

    answer = generate_answer(request.question, chunks, history=request.history)

    return ChatResponse(answer=answer, sources=sources[:5])