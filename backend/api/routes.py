from fastapi import APIRouter, BackgroundTasks

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_service import handle_chat

router = APIRouter()


@router.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


def perform_ingestion():
    from backend.src.ingest import build_dataset, build_index
    from backend.services.chat_service import reset_retriever
    try:
        df = build_dataset(max_pages=100)
        build_index(df)
        reset_retriever()  # force reload of the new index
        print(f"Successfully indexed {len(df)} chunks")
    except Exception as e:
        print(f"Ingestion error: {e}")


@router.get("/ingest")
def run_ingestion(background_tasks: BackgroundTasks):
    """Triggers the ingestion process on the server"""
    background_tasks.add_task(perform_ingestion)
    return {"status": "started", "message": "Ingestion started in background. Check back in 5 minutes."}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Handles chat requests and returns response."""
    return handle_chat(request)