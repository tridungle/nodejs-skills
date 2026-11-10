# Vector stores

Load when choosing, configuring or operating a vector index: `pgvector`, a document database's vector search, or a dedicated vector database (Qdrant, Weaviate, Pinecone, Milvus and similar). The retrieval pipeline that uses it (chunking, prompt assembly, citations) belongs to `llm-integration-typescript`.

## Choosing

| Option | Fits when | Watch for |
|---|---|---|
| `pgvector` in the existing PostgreSQL | Postgres is already the system of record; up to millions of vectors; filters on relational data and per-tenant security matter | Index build time and memory on large sets; tune per [postgres-queries.md](postgres-queries.md) |
| The document database's vector search | MongoDB (or similar) is already the system of record and offers it on the hosting tier in use | Feature availability depends on version and hosting |
| A dedicated vector database | Very large collections, high query volume, or features the general database lacks | A second system to secure, back up, monitor and keep in sync |

Default to the store the project already runs; move to a dedicated one when measurements (latency, recall, cost) show the need.

## The vector index is derived data

- The system of record holds the source text and metadata; the vector index can always be rebuilt from it. Document how long a full rebuild takes.
- Every vector stores, alongside it: source id, chunk position, tenant/owner id, access tags, content hash, **embedding model name and version**, and dimension.
- Writes are idempotent upserts keyed by a deterministic id (source id + chunk position), so retries and re-runs never duplicate.
- Deletions and permission changes in the source propagate to the index: a sync job or event handler, plus a periodic reconciliation that removes orphans.

## Embedding model changes

- Vectors from different models or dimensions are not comparable. Changing the model means re-embedding everything into a **new** index or collection, verifying it with the retrieval evals, then switching reads and deleting the old one.
- Use the distance metric the model is designed for (cosine, dot product or Euclidean), and normalise vectors when the metric requires it.

## Filtering and tenancy

- Apply tenant and permission filters **inside** the vector query (pre-filtering or the store's filtered search), never by discarding results afterwards; post-filtering leaks existence and returns too few results.
- Use namespaces, partitions or collections per tenant where the store supports them and the tenant count is manageable; otherwise an indexed metadata filter.
- Index the metadata fields used in filters, as with any query.

## Index configuration

- Approximate indexes (HNSW, IVF and variants) trade recall for speed. Measure recall@k against an exact search on a sample of invented queries before and after changing parameters (graph connectivity and build effort for HNSW, list and probe counts for IVF), and record the setting with its recall and latency.
- Quantisation or reduced dimensions cut memory and cost at some recall loss; adopt only with a measured recall check.
- Hybrid search (vector + keyword) handles exact names and codes that embeddings miss; merge with reciprocal rank fusion or a reranker.

## Layers

- A repository port (`VectorIndexRepository`: upsert, delete by source, search with filters) is the only code importing the vector database client; services and the retrieval pipeline depend on the port.
- Embedding calls go through the LLM gateway, not the repository.

## Operations and security

- Batch upserts within the store's rate and payload limits; back off on throttling.
- API keys from the secret store; network access restricted; one key per environment.
- Embeddings can leak information about their source text: protect them like the source data, and include them in deletion requests for personal data.
- Monitor index size, query latency percentiles, error rate and the lag between source changes and index updates.

## Checks

- A query as tenant A never returns tenant B's vectors: test it.
- Deleting a source removes its vectors within the agreed delay.
- Each stored vector records its embedding model; no index mixes two models.
- Recall@k against exact search is measured and recorded for the current index settings.
