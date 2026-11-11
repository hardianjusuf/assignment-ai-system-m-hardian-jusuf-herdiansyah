"""
Entry point aplikasi FastAPI — IT Helpdesk Assistant (Reference Implementation).
"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.router import handle_query
from app.rag import build_index

app = FastAPI(title="IT Helpdesk Assistant API")


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    status: str
    intent: str
    data: str


@app.on_event("startup")
async def startup_event():
    """Membangun index FAISS sekali saat aplikasi start, bukan di setiap request."""
    build_index()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    result = await handle_query(request.query)
    return AskResponse(**result)
