# Amenify AI Customer Support Bot

A RAG-based (Retrieval-Augmented Generation) AI chatbot for Amenify, built with:

- **Backend**: Python · FastAPI · OpenAI (embeddings + GPT-4o-mini) · FAISS
- **Frontend**: Vanilla HTML · CSS (glassmorphism dark mode) · JavaScript

---

## Project Structure

```
Amenify-Assignment/
├── backend/
│   └── main.py              # FastAPI app (RAG pipeline)
├── frontend/
│   ├── index.html           # Chat UI
│   ├── style.css            # Premium dark-mode styles
│   └── app.js               # Frontend logic & API calls
├── knowledge_base/
│   └── amenify_data.json    # Pre-scraped Amenify content (29 chunks)
├── .env.example             # Template for environment variables
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| pip | latest |
| Git | any |

You also need an **OpenAI API key** (get one at [platform.openai.com](https://platform.openai.com)).

---

## Setup & Run (Local)

### 1 — Clone / open the project

```bash
# If you haven't already, navigate to the project folder
cd Amenify-Assignment
```

### 2 — Create and activate a virtual environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Add your OpenAI API key

Copy `.env.example` to `.env` and fill in your key:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Then open `.env` and replace `your_openai_api_key_here` with your real key:

```
OPENAI_API_KEY=sk-...
```

### 5 — Start the server

```bash
# Run from the project root (Amenify-Assignment/)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You will see log output like:

```
INFO:root:Building FAISS index from 29 chunks…
INFO:root:FAISS index ready (dim=1536).
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 6 — Open the chat UI

Visit **http://localhost:8000** in your browser.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the chat UI |
| `POST` | `/chat` | Send a message, get a reply |
| `DELETE` | `/session/{id}` | Clear session history |
| `GET` | `/health` | Health check + chunk count |

### POST /chat — Request body

```json
{
  "session_id": "optional-uuid-string",
  "message": "What services does Amenify offer?"
}
```

### POST /chat — Response

```json
{
  "session_id": "abc123",
  "reply": "Amenify offers cleaning, handyman, dog walking...",
  "sources": ["https://amenify.com"]
}
```

---

## How It Works (RAG Pipeline)

```
User message
     │
     ▼
[ OpenAI Embeddings ]  ← text-embedding-3-small
     │
     ▼
[ FAISS Cosine Search ]  ← top-4 most relevant chunks (threshold 0.40)
     │
     ▼
[ Context Injection ]  ← injected into system prompt
     │
     ▼
[ GPT-4o-mini ]  ← temperature=0, strict knowledge-base-only instructions
     │
     ▼
JSON response → Chat UI
```

---

## Example Queries & Outputs

| Query | Expected Reply |
|-------|----------------|
| "What services does Amenify provide?" | Lists cleaning, handyman, chores, dog walking, food & grocery delivery, etc. |
| "Are cleaners background-checked?" | Yes — Amenify vets all professionals and monitors performance. |
| "How do I get the $50 sign-up bonus?" | Residents get $50 by signing up via the Amenify Resident App. |
| "Who is the CEO of Amenify?" | Everett Lynn is the Founder and CEO. |
| "What is the stock price of Amenify?" | "I don't know." (not in knowledge base) |
| "Do you offer pool cleaning?" | Yes, Amenify offers pool cleaners as part of its services. |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI secret key |

---

## Deployment (Optional — Render.com)

1. Push this project to a GitHub repo.
2. Go to [render.com](https://render.com) → **New Web Service**.
3. Connect your repo, set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port 10000`
   - **Environment variable**: `OPENAI_API_KEY=sk-...`
4. Deploy — Render gives you a public HTTPS URL.
