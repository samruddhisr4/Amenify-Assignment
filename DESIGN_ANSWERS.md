# Amenify Summer 2026 – Software Engineering Internship Assignment

## Section 3: Reasoning & Design

---

### 1. How did you ingest and structure the data from the website?

I used a two-phase approach:

**Phase 1 — Scraping**  
Fetched content from key Amenify pages: the homepage, About Us, and all major service pages (cleaning, handyman, chores, dog walking, food/grocery, move-out cleaning, etc.) using Python's `requests` + `BeautifulSoup`. Navigation links, footers, and HTML boilerplate were stripped, keeping only meaningful text.

**Phase 2 — Chunking & Structuring**  
The raw page text was split into semantically coherent chunks (each focused on one topic: a service, an FAQ, a company fact). Each chunk was stored as a JSON object with three fields:
```json
{
  "source": "https://amenify.com",
  "section": "FAQ - Background Checks",
  "content": "..."
}
```
This structure lets the retrieval system surface which source a chunk came from, making attribution transparent and supporting anti-hallucination strategies.

**Embedding & Indexing**  
Each chunk was embedded with OpenAI's `text-embedding-3-small` model (1536-dimensional vectors). The vectors were loaded into a **FAISS IndexFlatIP** (Inner Product index) after L2-normalisation, which makes inner-product equivalent to cosine similarity. This gives O(1) approximate nearest-neighbor lookup at query time.

---

### 2. How did you reduce hallucinations?

Three complementary safeguards:

| Layer | Technique |
|-------|-----------|
| **Retrieval threshold** | Only chunks with cosine similarity ≥ 0.40 are included in the prompt. If no chunk meets this bar the model is told "no relevant information found" and defaults to "I don't know." |
| **Strict system prompt** | The system message explicitly instructs the model: *"Answer ONLY using the context provided. If the answer cannot be found in the context, respond EXACTLY with: I don't know."* |
| **Temperature = 0** | Setting `temperature=0` makes GPT-4o-mini deterministic and eliminates creative/speculative generation. |

Additionally, the context is injected fresh on every request (including relevant retrieved chunks only), so the model cannot drift into confabulation based on prior conversational momentum.

---

### 3. What are the limitations of your approach?

| Limitation | Details |
|------------|---------|
| **Static knowledge base** | The scraped data is a snapshot. If Amenify updates their website (new services, pricing, FAQs), the bot remains unaware until the knowledge base is rebuilt. |
| **No real-time data** | Booking availability, live pricing, or user-account information cannot be sourced from a static JSON file. |
| **Chunk granularity** | Very long pages where multiple topics are mixed may cause imperfect chunk boundaries, leading to slightly irrelevant retrievals. |
| **Language support** | Currently English-only; multi-language support would require multilingual embeddings. |
| **Session memory limit** | Sessions are stored in-memory on the server; a restart loses all history. Under concurrent load, memory usage grows linearly. |
| **FAISS is in-memory only** | On server restart the index is rebuilt (adds ~5–10 s startup time). For large corpora this is not practical. |

---

### 4. How would you scale this system?

**Horizontal scaling:**
- Replace in-memory FAISS with a managed vector database (e.g., **Pinecone**, **Weaviate**, or **pgvector** on PostgreSQL) that is persistent and shareable across instances.
- Deploy the FastAPI app on **Kubernetes** (GKE / EKS) behind a load balancer so multiple replicas handle concurrent users.

**Session persistence:**
- Move `sessions{}` to **Redis** with TTL so horizontal scaling doesn't lose session history.

**Knowledge base freshness:**
- Set up a scheduled scraping job (e.g., **Cloud Scheduler** → Cloud Run) that re-scrapes Amenify pages nightly, diffs against the current knowledge base, and upserts only changed chunks.

**Observability:**
- Add **LangSmith** or **Langfuse** for LLM call tracing and latency monitoring.
- Track retrieval quality metrics (NDCG, precision@k) and set up alerts when "I don't know" rate spikes (a proxy for coverage gaps).

**Cost optimisation:**
- Cache embeddings for repeated queries using Redis.
- Use a cheaper model (GPT-4o-mini ✅ already chosen) for most responses; fall back to GPT-4o only for high-confidence complex queries.

---

### 5. What improvements would you make for production use?

| Category | Improvement |
|----------|-------------|
| **Retrieval quality** | Switch to a **hybrid search** (BM25 keyword + dense vector) using Weaviate or Elasticsearch to catch keyword-matched queries that embeddings can miss (e.g., exact product names). |
| **Re-ranking** | Add a cross-encoder re-ranker (e.g., Cohere Rerank or a fine-tuned BERT) between retrieval and generation to improve top-k precision. |
| **Streaming responses** | Stream the GPT response token-by-token via Server-Sent Events so the UI feels snappier. |
| **Auth & rate limiting** | Add API key auth and per-IP rate limiting (e.g., via FastAPI middleware + Redis) to prevent abuse. |
| **Feedback loop** | Add 👍/👎 buttons in the UI. Negative feedback is logged and routed to a human review queue, improving knowledge base gaps over time. |
| **Persistent sessions** | Use Redis + structured turn storage, enabling multi-day conversation memory and analytics on common questions. |
| **Multi-modal** | If Amenify adds booking screenshots or onboarding videos, extend to handle image context (GPT-4o vision). |
| **Automated testing** | Build a golden-set Q&A eval suite that runs on every knowledge-base update, using metrics like faithfulness and answer relevance (via `ragas`). |

---

## Deliverables Checklist

- [x] Source code (backend + frontend)
- [x] README with setup instructions
- [x] This document with Section 3 answers filled in
- [x] Example queries and outputs (see README)

---

*Submitted by: [Your Name]*  
*LinkedIn: [Your LinkedIn URL]*  
*Email: [Your Email]*
