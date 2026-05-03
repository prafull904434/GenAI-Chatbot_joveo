# GitLab Handbook & Direction GenAI Chatbot (React + FastAPI)

A production-style GenAI chatbot that answers questions from GitLab's public **Handbook** and **Direction** pages using a Retrieval-Augmented Generation (RAG) pipeline.

## Features
- Data ingestion from GitLab handbook + direction sitemaps
- Chunking and Semantic Embedding retrieval for relevant context
- Gemini-powered grounded answer generation
- FastAPI backend with `/chat` and `/health` endpoints
- React frontend with:
  - polished chat experience
  - follow-up support
  - source citations + relevance scores
  - loading and error states
  - clear, accessible layout

## Tech Stack
- **Frontend:** React (Vite)
- **Backend:** FastAPI (Python)
- **LLM:** Gemini 1.5 Flash
- **Retrieval:** Semantic Embeddings (Gemini) + cosine similarity

## Project Structure
```text
.
|-- backend/
|   |-- __init__.py
|   |-- main.py
|   |-- api/
|   |-- core/
|   |-- schemas/
|   `-- services/
|-- requirements.txt
|-- PROJECT_WRITEUP.md
|-- src/
|   |-- config.py
|   |-- ingest.py
|   |-- retriever.py
|   `-- llm.py
|-- frontend/
|   |-- package.json
|   |-- index.html
|   |-- vite.config.js
|   `-- src/
|       |-- App.jsx
|       |-- main.jsx
|       `-- styles.css
`-- .env.example
```

## 1) Backend Setup

### Prerequisites
- Python 3.10+
- Gemini API key ([Google AI Studio](https://aistudio.google.com))

### Install dependencies
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### Configure backend env
Copy `.env.example` to `.env` and set:
```env
GEMINI_API_KEY=your_key_here
MAX_PAGES=120
CHUNK_SIZE=1100
CHUNK_OVERLAP=180
TOP_K=5
```

## 2) Build Retrieval Index
```bash
python -m src.ingest --max-pages 120
```

Expected output:
```text
Indexed <N> chunks from <M> pages.
```

## 3) Run Backend API
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:
```bash
curl http://127.0.0.1:8000/health
```

## 4) Run React Frontend
```bash
cd frontend
npm install
```

Copy `frontend/.env.example` to `frontend/.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start app:
```bash
npm run dev
```

Open the URL from terminal (usually `http://127.0.0.1:5173`).

## 5) Deployment

### Recommended: Vercel (Frontend) + Render/Railway (Backend)
1. Deploy `backend.py` FastAPI app on Render/Railway.
2. Deploy `frontend` on Vercel.
3. Set `VITE_API_BASE_URL` in Vercel to deployed backend URL.
4. Set `GEMINI_API_KEY` on backend platform secrets.

