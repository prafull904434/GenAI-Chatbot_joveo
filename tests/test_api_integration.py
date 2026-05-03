import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.src.retriever import RetrievedChunk

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat_endpoint_validation_error():
    # Sending missing question
    response = client.post("/chat", json={"top_k": 5})
    assert response.status_code == 422

def test_chat_endpoint_short_question():
    # Because we set min_length=1, "hi" should pass Pydantic validation
    # If the index is missing, it returns a 200 with an error string.
    # If the index exists but Gemini fails, it returns a 200 with fallback string.
    # Either way, we expect a 200 status code from our robust service layer.
    response = client.post("/chat", json={"question": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data

@pytest.fixture
def mock_retriever(monkeypatch):
    class MockRetriever:
        def search(self, query, k=5):
            return [
                RetrievedChunk(url="https://handbook.gitlab.com/", content="Mock content", score=0.99)
            ]
    monkeypatch.setattr("backend.services.chat_service.get_retriever", lambda: MockRetriever())

@pytest.fixture
def mock_llm(monkeypatch):
    def mock_generate(*args, **kwargs):
        return "This is a mock answer from the LLM."
    monkeypatch.setattr("backend.services.chat_service.generate_answer", mock_generate)

def test_chat_endpoint_success(mock_retriever, mock_llm):
    response = client.post("/chat", json={"question": "What is the handbook?", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mock answer from the LLM."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["url"] == "https://handbook.gitlab.com/"
    assert data["sources"][0]["score"] == 0.99
