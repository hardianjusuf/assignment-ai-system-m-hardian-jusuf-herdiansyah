"""
Router — implementasi lengkap: intent detection berbasis LLM + routing ke RAG atau tool call.
"""

import os
import re
import time
from google import genai
from google.genai import types

from app.rag import answer_from_knowledge_base
from app.tools import get_ticket_status

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

TICKET_ID_PATTERN = re.compile(r"TICKET-\d{4}", re.IGNORECASE)


async def detect_intent(query: str) -> str:
    """
    Menentukan intent dari query user menggunakan LLM: 'faq' atau 'ticket_status'.
    Menggunakan shortcut berbasis pattern-matching terlebih dahulu (jika ticket_id
    eksplisit disebut dalam query), baru fallback ke LLM classification.
    """
    if TICKET_ID_PATTERN.search(query):
        return "ticket_status"

    prompt = f"""Klasifikasikan pertanyaan berikut ke dalam salah satu kategori:
'faq' (pertanyaan informasi/kebijakan umum seputar cuti, akses, perangkat, HR, dsb)
atau 'ticket_status' (permintaan mengecek status tiket tertentu).

Jawab HANYA dengan satu kata: faq atau ticket_status.

Pertanyaan: {query}"""

    response = _client.models.generate_content(
        model="gemini-3.1-flash-lite", # sesuaikan model LLM yang digunakan
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0),
    )
    intent = response.text.strip().lower()

    if intent not in ("faq", "ticket_status"):
        return "faq"  # default fallback yang lebih aman daripada 'unknown'
    return intent


def extract_ticket_id(query: str) -> str:
    """Mengekstrak ticket_id dari teks query menggunakan regex."""
    match = TICKET_ID_PATTERN.search(query)
    if match:
        return match.group(0).upper()
    return ""


async def handle_query(query: str) -> dict:
    """Fungsi utama yang dipanggil oleh endpoint /ask."""
    try:
        # Mengukur latency router (intent detection) untuk monitoring performa router
        start_router = time.perf_counter()
        intent = await detect_intent(query)
        router_latency = time.perf_counter() - start_router
        print(f"[LATENCY] Router: {router_latency:.3f} detik")

        if intent == "ticket_status":
            ticket_id = extract_ticket_id(query)
            if not ticket_id:
                return {
                    "status": "error",
                    "intent": "ticket_status",
                    "data": "Mohon sertakan ID tiket (format: TICKET-XXXX) pada pertanyaan Anda.",
                }
            data = get_ticket_status(ticket_id)
            return {"status": "success", "intent": "ticket_status", "data": data}

        else:  # intent == "faq"
            data = await answer_from_knowledge_base(query)
            return {"status": "success", "intent": "faq", "data": data}

    except Exception as e:
        return {
            "status": "error",
            "intent": "unknown",
            "data": f"Terjadi kesalahan saat memproses permintaan Anda. Silakan coba lagi. ({type(e).__name__})",
        }
