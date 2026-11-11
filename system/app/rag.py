"""
Modul RAG — implementasi lengkap: embedding, FAISS, semantic search, LLM answer generation.

Ini adalah REFERENCE IMPLEMENTATION (sistem yang sudah berfungsi penuh), digunakan
sebagai starter system untuk Assignment 5 (AI System Evaluation, Safety & Optimization).
"""

import os
import pandas as pd
import numpy as np
import faiss
from google import genai
from google.genai import types

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "it_helpdesk_knowledge_base.csv")

_index = None
_df = None


def _get_embedding(text: str):
    result = _client.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )
    return result.embeddings[0].values


def build_index():
    """Memuat knowledge base, membuat embedding, dan membangun index FAISS."""
    global _index, _df

    _df = pd.read_csv(KNOWLEDGE_BASE_PATH)
    _df["content"] = "Q: " + _df["question"] + " A: " + _df["answer"]

    embeddings = [_get_embedding(doc) for doc in _df["content"].tolist()]
    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    _index = faiss.IndexFlatL2(dimension)
    _index.add(embeddings)

    return _index


def semantic_search(query: str, top_k: int = 3):
    """Mencari entri FAQ paling relevan terhadap query menggunakan semantic search."""
    global _index, _df

    if _index is None:
        build_index()

    query_embedding = np.array([_get_embedding(query)]).astype("float32")
    distances, indices = _index.search(query_embedding, top_k)

    results = []
    for rank, idx in enumerate(indices[0]):
        results.append({
            "rank": rank + 1,
            "question": _df.iloc[idx]["question"],
            "answer": _df.iloc[idx]["answer"],
            "category": _df.iloc[idx]["category"],
            "distance": float(distances[0][rank]),
        })
    return results


def _build_prompt(query: str, search_results: list) -> str:
    context = "\n\n".join(
        f"FAQ: {r['question']}\nJawaban: {r['answer']}" for r in search_results
    )
    prompt = f"""Kamu adalah asisten IT Helpdesk internal perusahaan yang ramah dan membantu.

Tugas: Jawab pertanyaan karyawan HANYA berdasarkan informasi FAQ berikut. Jika informasi tidak ditemukan dalam FAQ, katakan bahwa kamu belum memiliki informasi tersebut dan sarankan menghubungi tim IT/HR terkait.

Konteks FAQ relevan:
{context}

Pertanyaan karyawan: {query}

Jawaban:"""
    return prompt


async def answer_from_knowledge_base(query: str) -> str:
    """Menjalankan semantic search, menyusun prompt, dan menghasilkan jawaban via LLM."""
    search_results = semantic_search(query, top_k=3)
    prompt = _build_prompt(query, search_results)

    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text
