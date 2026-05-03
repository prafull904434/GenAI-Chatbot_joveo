from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.core.config import load_environment

load_environment() # load environment variables before app startup

app = FastAPI(
    title="GitLab GenAI Chatbot API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gen-ai-chatbot-joveo.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# register all API routes
app.include_router(router)
