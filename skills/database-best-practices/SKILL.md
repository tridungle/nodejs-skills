---
name: database-best-practices
description: "Database work for TypeScript backends on PostgreSQL, MongoDB or a vector store: schema and document design, integrity rules, indexes, safe migrations, query tuning, transactions and concurrency, connection pools, access control. Use when changing a schema or diagnosing database performance."
license: MIT
metadata:
  tags: ["database", "postgres", "mongodb", "vector-database", "migrations", "performance"]
---

# Database Best Practices

Data that stays correct when application code forgets a rule, schema changes that deploy without downtime, and queries that stay fast as data grows, whichever database the project uses. The principles below hold for every engine; the engine-specific detail lives in one set of references per engine, and a run reads only the set it needs.

How application code reaches the database (repository classes, ORM/ODM wiring, transaction handles in services) belongs to `nestjs-best-practices` or `nodejs-typescript-best-practices`. This skill owns what happens inside the database.

## Cost rules

- **Identify the engine first, then read only its references.** Look at dependencies (`pg`, `postgres`, Prisma's `provider`, TypeORM/Drizzle/Knex config, `mongoose`, `mongodb`, a vector database client) and the local container setup. A project may use more than one; handle each store with its own rules.
- **Check the real state before advising**: existing migrations or schema files, the engine version, the hosting (self-managed or a managed service). Behaviour differs between versions.
- **Never propose switching databases** unless asked. Work with the engine the project chose.
- **Use the project's migration and schema tooling.** Never introduce a second one.
- **Measure before tuning**: a query plan or the engine's slow-query statistics are evidence; "this might be slow" is not.
- **Add no extension, index type, service or infrastructure** (a pooler, a replica, a new vector database) without asking.

## Choosing a store (only when asked, or for a new project)

| Data and access pattern | Fits |
|---|---|
| Related entities, joins, multi-row transactions, reporting | Relational (PostgreSQL) |
| Self-contained documents read and written as a whole, flexible shape per record | Document (MongoDB) |
| Similarity search over embeddings | A vector index: `pgvector` or the document database's vector search when that database is already there; a dedicated vector database at scale |
| Ephemeral data, rate limits, sessions | A cache or key-value store, never the system of record |

Each additional store is another thing to back up, secure, monitor and keep consistent. One store that fits well enough usually beats two that fit perfectly.

## Where the database sits in the layers

| Layer | Database concern |
|---|---|
| Model | Mirrors the stored shape; the store is the source of truth for types, required fields and uniqueness |
| Repository | The only code that issues queries; owns pagination, locking or atomic updates, upserts, and translation of engine errors into domain errors (a unique violation, Postgres `23505` or MongoDB `11000`, becomes `ConflictError`) |
| Service | Decides transaction boundaries; never writes queries; business rules never hide in database hooks or ODM middleware |
| Migrations / schema scripts | Versioned, applied by the project's tool, reviewed like code |

## Non-negotiables (every engine)

1. **Integrity in the store**: required fields, uniqueness and allowed values enforced by the database (constraints, schema validators, unique indexes), not only by application validation.
2. **Index by query pattern**: every filter, join/lookup and sort used on a large collection or table has an index that matches it; unused indexes are removed, because each one slows every write.
3. **Schema changes are safe while the old code still runs**: expand, migrate data in batches, switch reads, contract later. No rename or removal in the same deploy as the code that stops using it.
4. **Every list query is bounded**: a capped limit, and range (keyset) pagination on large or growing data instead of deep skips.
5. **Read-modify-write is protected**: an atomic update, a version check, or a lock. Never read, change in memory and write back unguarded.
6. **Input never becomes query structure**: parameters in SQL; in MongoDB, reject objects and `$`-prefixed keys where a scalar is expected; allow-list sort and filter fields.
7. **Every user-scoped query carries the owner or tenant** as a parameter of the repository method.
8. **Connection count is planned**: pool size per process × processes stays inside the server's connection limit, with a margin.
9. **The application connects with a least-privilege account**, never an admin or root user; schema changes run with a separate account.
10. **Every query has a time limit**, and every backup has been proven by a restore.

## Pick the reference for the task

| Engine | Task | Read |
|---|---|---|
| PostgreSQL | Tables, types, keys, constraints, tenancy layout | [postgres-schema.md](references/postgres-schema.md) |
| PostgreSQL | Slow query, `EXPLAIN`, index choice, pagination, full-text search | [postgres-queries.md](references/postgres-queries.md) |
| PostgreSQL | Writing or reviewing a migration, backfills | [postgres-migrations.md](references/postgres-migrations.md) |
| PostgreSQL | Lost updates, deadlocks, job queues, isolation, pools, PgBouncer | [postgres-concurrency.md](references/postgres-concurrency.md) |
| PostgreSQL | Roles, row-level security, sensitive data, backups | [postgres-security.md](references/postgres-security.md) |
| MongoDB | Document modelling, embed vs reference, validation, Mongoose schemas | [mongodb-schema.md](references/mongodb-schema.md) |
| MongoDB | Slow query, `explain`, index order, aggregation, pagination | [mongodb-queries.md](references/mongodb-queries.md) |
| MongoDB | Transactions, concurrency, schema evolution, connections, security | [mongodb-operations.md](references/mongodb-operations.md) |
| Vector store | Choosing and running a vector index, embeddings lifecycle, filtering, sync | [vector-stores.md](references/vector-stores.md) |

For another engine (MySQL, SQL Server, DynamoDB, …), apply the non-negotiables above with that engine's own documentation; the Postgres references are the closest guide for relational engines.

Retrieval pipelines (chunking, prompt assembly, citations) belong to `llm-integration-typescript`; this skill covers the store underneath.

## Review checklist

Report each as pass or fail with `file:line` or the query that proves it.

- [ ] Required fields, uniqueness and allowed values enforced by the store
- [ ] Every new filter, join or sort on large data has a matching index
- [ ] Schema change safe against the currently deployed code; large backfills batched separately
- [ ] List queries capped; no deep skip/offset on large data
- [ ] Read-modify-write paths use an atomic update, a version check or a lock
- [ ] No query built from raw input (SQL strings, MongoDB operator objects)
- [ ] User-scoped repository methods take the owner/tenant
- [ ] Pool size × processes fits the server's connection limit
- [ ] Application account is least-privilege; queries have time limits

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| Rules enforced only in application code | Constraints, validators and unique indexes in the store as well |
| Renaming or dropping a field in the same release as the code change | Expand → migrate → contract over several deploys |
| Business logic in database triggers or ODM middleware | Explicit service code; hooks only for mechanical concerns such as timestamps |
| `skip(100000)` / `OFFSET 100000` | Range pagination on an indexed sort key plus a unique tie-breaker |
| Counting all matches on every list request | `hasMore` from fetching `limit + 1` |
| Admin credentials in the application's connection string | A dedicated least-privilege account |
| A second database added for one feature | Use the existing store's capability (e.g. `pgvector`) until measurements say otherwise |
