"""
Entry point aplikasi FastAPI — IT Helpdesk Assistant (Reference Implementation).
"""

import time
from fastapi import FastAPI
from pydantic import BaseModel

from app.router import handle_query
from app.rag import build_index

from fastapi import FastAPI, HTTPException

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
    # Mengukur LATENCY TOTAL untuk monitoring performa keseluruhan
    start = time.perf_counter()
    result = await handle_query(request.query)
    end = time.perf_counter()
    print(f"\n[LATENCY] Total: {end - start:.3f} detik")

    # Validasi input query untuk memastikan tidak kosong atau hanya berisi spasi
    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Mohon masukkan pertanyaan yang berkaitan dengan layanan perusahaan."
        )
    return AskResponse(**result)
