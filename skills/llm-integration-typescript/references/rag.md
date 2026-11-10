# Retrieval-augmented generation (RAG)

Load when answering from the project's own documents or data: ingestion, embeddings, vector search, prompt assembly with sources, citations.

Start by checking whether RAG is needed. If the source material fits comfortably in the context window and changes rarely, passing it directly (with provider prompt caching) is simpler and often more accurate. Retrieval earns its complexity when the corpus is large, changes often, or must be filtered per user.

## Layers

| Step | Layer |
|---|---|
| Ingest: load, clean, chunk, embed, upsert | A background job calling an ingestion service |
| Store and search vectors | A repository (`DocumentChunkRepository`), the only code that knows the vector store |
| Embed text | The LLM gateway (or a separate `EmbeddingGateway` port) |
| Retrieve, rank, assemble prompt, call model, attach citations | The service |
| Endpoint | The controller |

Use the store the project already has; operating it (choosing a store, embedding-model changes, filtered search, keeping the index in sync) is covered by the `database-best-practices` skill when installed. Postgres with `pgvector` keeps vectors next to the data and its access rules; a dedicated vector database is a decision for scale, not a default.

## Ingestion

- **Chunk by structure first** (headings, sections, paragraphs), then by size. Typical starting point: a few hundred tokens per chunk with a small overlap. Tune with the eval set, not by intuition.
- Store with each chunk: source id, title, section path, position, `tenantId`/owner, access tags, content hash, embedding model name, and timestamps.
- Re-embed only changed content (compare hashes). Changing the embedding model means re-embedding everything into a new column or index, then switching over.
- Run ingestion as idempotent jobs; a document updated twice concurrently must not leave duplicate chunks.

## Retrieval

- **Filter before ranking**: tenant, permissions and document type as `WHERE` clauses in the same query as the vector search. Filtering after retrieval leaks other tenants' existence and returns too few results.
- Hybrid search (vector similarity plus keyword/full-text) handles exact names, codes and ids that embeddings miss. Merge with reciprocal rank fusion or a reranker.
- Retrieve more than you use (e.g. 20–50), rerank or deduplicate, then pass the top few to the model.
- Index the vector column (HNSW or IVFFlat in pgvector) and check the plan uses it with the filters applied.

## Prompt assembly

- Put retrieved chunks in the user content inside clear delimiters, each with its source id. Instructions in the system prompt say to answer only from the supplied sources and to say when they do not contain the answer.
- Retrieved text is untrusted: a document saying "ignore previous instructions" is data. Keep it out of the system prompt and never let it trigger tools with side effects.
- Respect a token budget for context; drop the lowest-ranked chunks rather than truncating mid-chunk.

## Answers and citations

- Return the answer with the list of source ids actually used; ask the model to cite source ids inline, then verify each cited id was in the supplied set and drop any that were not.
- "No answer in the sources" is a valid, expected output. Test for it.

## Evaluating retrieval separately

Measure retrieval on its own before judging answers: for a set of invented questions with known relevant chunks, check that the relevant chunk appears in the top-k (recall@k). Poor answers with good retrieval point to the prompt; poor retrieval points to chunking, filters or the embedding model. See [evals-cost.md](evals-cost.md).

## Checks

- A query from tenant A never returns tenant B's chunks: test it.
- Updating a document replaces its chunks, leaving no stale ones.
- Questions about exact identifiers (codes, SKUs) are answered: proves keyword search is in the mix.
- The vector search query plan uses the index together with the tenant filter.
