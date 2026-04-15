"""
Amenify AI Customer Support Bot - Backend API
Uses RAG (Retrieval-Augmented Generation) with OpenAI + NumPy
"""

import os
import json
import uuid
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set. Add it to the .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL  = "gpt-4o-mini"
TOP_K       = 4               # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.40   # cosine-similarity cutoff (0-1)

# ---------------------------------------------------------------------------
# Load & index knowledge base at startup
# ---------------------------------------------------------------------------
KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "amenify_data.json"

with open(KB_PATH, "r", encoding="utf-8") as f:
    raw_chunks: list[dict] = json.load(f)

# Build plain-text documents for embedding
documents: list[str] = [
    f"Section: {c['section']}\n{c['content']}" for c in raw_chunks
]


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return (N, D) float32 array of embeddings."""
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vecs = [e.embedding for e in response.data]
    return np.array(vecs, dtype="float32")


logger.info("Embedding %d knowledge-base chunks…", len(documents))
corpus_embeddings = embed_texts(documents)

# L2-normalise so dot-product == cosine similarity
norms = np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)
corpus_embeddings_norm = corpus_embeddings / np.maximum(norms, 1e-10)
logger.info("Embeddings ready (dim=%d).", corpus_embeddings_norm.shape[1])

# ---------------------------------------------------------------------------
# In-memory session store  {session_id: [{"role": ..., "content": ...}]}
# ---------------------------------------------------------------------------
sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """You are a helpful customer support assistant for Amenify — an AI-powered resident commerce and home-services platform.

STRICT RULES:
1. Answer ONLY using the context provided below. Do NOT use any outside knowledge.
2. If the answer cannot be found in the context, respond EXACTLY with: "I don't know."
3. Be concise, friendly, and professional.
4. Never mention that you are using a knowledge base or context.
5. Do not hallucinate services, prices, or features not mentioned in the context.
"""

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Amenify Support Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend from the /static directory
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[str]


# ---------------------------------------------------------------------------
# Helper: retrieve relevant chunks
# ---------------------------------------------------------------------------
def retrieve(query: str) -> tuple[list[str], list[str]]:
    """Return (context_texts, source_urls) for the query."""
    q_vec = embed_texts([query])                        # (1, D)
    q_norm = q_vec / np.maximum(np.linalg.norm(q_vec), 1e-10)

    # Cosine similarities: shape (N,)
    scores = (corpus_embeddings_norm @ q_norm.T).flatten()

    # Take top-K indices sorted by descending score
    top_indices = np.argsort(scores)[::-1][:TOP_K]

    retrieved_texts: list[str] = []
    retrieved_sources: list[str] = []

    for idx in top_indices:
        if scores[idx] >= SIMILARITY_THRESHOLD:
            retrieved_texts.append(documents[idx])
            retrieved_sources.append(raw_chunks[idx]["source"])

    return retrieved_texts, retrieved_sources


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Create or retrieve session
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]

    # Step 1 – Retrieve relevant context
    context_chunks, sources = retrieve(req.message)

    if context_chunks:
        context_text = "\n\n---\n\n".join(context_chunks)
        context_block = f"\n\nContext from Amenify knowledge base:\n{context_text}"
    else:
        context_block = "\n\nContext from Amenify knowledge base: (no relevant information found)"

    # Step 2 – Build messages for the LLM
    system_message = {"role": "system", "content": SYSTEM_PROMPT + context_block}

    messages = [system_message] + history + [
        {"role": "user", "content": req.message}
    ]

    # Step 3 – Call OpenAI
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.0,  # keeps answers grounded
            max_tokens=512,
        )
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        raise HTTPException(status_code=502, detail="OpenAI API error.")

    reply = response.choices[0].message.content.strip()

    # Step 4 – Update session history (keep last 10 turns to avoid token bloat)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        sessions[session_id] = history[-20:]

    unique_sources = list(dict.fromkeys(sources))  # deduplicate, preserve order
    return ChatResponse(session_id=session_id, reply=reply, sources=unique_sources)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Clear chat history for a session."""
    sessions.pop(session_id, None)
    return {"message": "Session cleared."}


@app.get("/health")
def health():
    return {"status": "ok", "chunks_indexed": len(documents)}
