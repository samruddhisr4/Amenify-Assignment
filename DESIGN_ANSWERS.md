# Design & Architecture Questions — Amenify AI Support Bot

---

## 1. How did you ingest and structure the data from the website?

I manually curated content from several pages on amenify.com — the homepage, about page, service pages, provider page, and a few others. I chose to do this by hand rather than scraping automatically because scrapers tend to pull in a lot of junk: nav menus, cookie banners, repeated footers. For a support bot, the quality of what goes into the knowledge base matters more than the quantity.

The data lives in a JSON file where each entry has three fields: a `source` URL (so the bot can cite where it got its answer), a `section` label like "FAQ - Background Checks", and the actual `content`. Each chunk maps to one coherent topic rather than being split at some arbitrary character count. That way, when a chunk is retrieved, it actually contains a complete, useful answer. At startup, each chunk is embedded using OpenAI's `text-embedding-3-small` model and stored in memory as a NumPy matrix for fast similarity lookups.

---

## 2. How did you reduce hallucinations?

Honestly, I attacked this from a few different angles. The most important one is the system prompt — the model is told upfront to only answer using the context it's given and to say "I don't know." if the answer isn't there. No room for improvisation.

On top of that, there's a similarity threshold: only knowledge base chunks with a cosine similarity score above 0.40 actually get sent to the model. If nothing clears that bar, the model explicitly sees "no relevant information found" in its context, which makes the "I don't know" response far more reliable. I also set temperature to zero, so the model isn't being creative — it sticks to the most probable, grounded answer. And since the knowledge base was hand-written from real site content, there's no bad source material feeding the retriever in the first place.

---

## 3. What are the limitations of your approach?

The biggest one is that the knowledge base is static. The moment Amenify updates their website, the bot is out of date, and someone has to manually fix the JSON and restart the server. There's no auto-sync.

Beyond that, 26 chunks is pretty thin coverage. It handles the common questions well, but anything specific — like pricing for a particular community or detailed escalation steps — just isn't there. The session store is also in-memory, so a server restart wipes all conversation history. And the brute-force similarity search works fine now, but would slow down significantly if the corpus ever grew to thousands of documents. The 0.40 threshold is also just a rough heuristic — I'd want a proper test set to validate whether it's actually the right cutoff.

---

## 4. How would you scale this system?

The first thing I'd change is to stop relying on a hand-maintained JSON file and build a proper ingestion pipeline — something that watches amenify.com for changes, re-embeds only what changed, and updates the knowledge base automatically. For the retrieval side, I'd swap the NumPy matrix for a real vector database like Pinecone or Qdrant, which handles millions of vectors efficiently and supports filtering by metadata like community ID or service type.

Sessions would move to Redis so they survive restarts and can be shared across multiple server instances. The API itself would be containerized and deployed behind a load balancer, with replicas scaling up based on traffic. Since the embedding call on each user query is the main latency cost, caching embeddings for common or repeated queries would also help a lot.

---

## 5. What improvements would you make for production use?

The most impactful change would be the live ingestion pipeline — keeping the knowledge base in sync with the actual website is what makes the bot trustworthy long-term. I'd also want a real evaluation framework: a set of test questions with known answers, so any change to the prompt, threshold, or chunking strategy can be validated before it ships.

A feedback mechanism would be valuable too — letting residents give a thumbs up or down after each response, and having a human review the failures. That data would quickly reveal the patterns the bot is getting wrong. For a platform like Amenify with thousands of communities, I'd also add multi-tenant support so the retrieval layer can be filtered to show only content relevant to a specific property. And finally, when the bot genuinely can't answer, it shouldn't just leave the user hanging — there should be a clear path to a human agent or a support ticket.
