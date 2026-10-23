---
name: postgres-database
description: "Designs and tunes PostgreSQL behind a TypeScript repository layer: schema and types, constraints, indexes, zero-downtime migrations, EXPLAIN-driven query tuning, locking and isolation, connection pooling, row-level security. Use when changing a Postgres schema or diagnosing database performance."
license: MIT
metadata:
  tags: ["postgres", "postgresql", "database", "sql", "migrations", "performance"]
---

# PostgreSQL

Make schema changes that deploy without downtime, queries that stay fast as tables grow, and data rules the database enforces even when application code forgets them. Everything here applies to Postgres running anywhere: self-hosted, a managed cloud service or a container.

How application code reaches the database (repository classes, ORM wiring, transaction handles in services) belongs to `nestjs-best-practices` or `nodejs-typescript-best-practices`. This skill owns what happens inside the database.

## Cost rules

- **Read only the reference the task needs** (table below).
- **Check the real state before advising.** Read the migrations folder and the ORM schema, and the Postgres major version (`SELECT version()` or the container image). Advice differs between versions.
- **Use the project's migration tool** (Prisma Migrate, TypeORM, Drizzle Kit, Knex, node-pg-migrate, plain SQL files). Never introduce a second one.
- **Measure before tuning.** A query plan or `pg_stat_statements` output is evidence; "this might be slow" is not.
- **Add no extension or infrastructure** (PgBouncer, a read replica, partitioning, `pg_trgm`) without asking; each is an operational commitment.

## Where Postgres sits in the layers

| Layer | Postgres concern |
|---|---|
| Model | Mirrors the schema; the database is the source of truth for types, nullability and constraints |
| Repository | The only code that issues SQL or ORM queries; owns pagination queries, locking clauses, upserts, error-code translation (`23505` unique violation → `ConflictError`, `23503` foreign-key violation → `ValidationError` or `ConflictError`) |
| Service | Decides transaction boundaries and isolation; never writes SQL |
| Migrations | Versioned files, applied by the migration tool, reviewed like code |

## Non-negotiables

1. **Constraints in the database**: `NOT NULL` by default, foreign keys, `UNIQUE`, `CHECK`. Application validation is a second layer, not the only one. See [schema-design.md](references/schema-design.md).
2. **Index every foreign key column and every column combination used to filter, join or sort** on large tables. Postgres does not index foreign keys automatically.
3. **Every migration is safe while the old code is still running**: expand → migrate → contract, never a rename or drop in the same deploy as the code change. See [migrations.md](references/migrations.md).
4. **Migrations set `lock_timeout`**, and build indexes on existing tables with `CREATE INDEX CONCURRENTLY`.
5. **Parameterized queries only**, including in ORM raw-SQL escape hatches. Identifiers (sort columns, table names) come from an allow-list.
6. **`timestamptz` for points in time**, `numeric` or integer minor units for money, `jsonb` (not `json`) for documents, `text` with a `CHECK` instead of `varchar(n)` when length matters.
7. **Every list query is bounded**: `LIMIT` with a cap, keyset pagination on large tables. See [indexes-queries.md](references/indexes-queries.md).
8. **Read-modify-write is protected**: a row lock, an atomic `UPDATE … SET x = x + 1`, or an optimistic version column. See [concurrency-connections.md](references/concurrency-connections.md).
9. **Connection count is planned**: pool size per instance × number of instances stays below `max_connections` minus a margin for admin and migrations.
10. **The application role is not a superuser** and does not own the tables; migrations run as a separate role. See [security-rls.md](references/security-rls.md).

## Pick the reference for the task

| Task | Read |
|---|---|
| New tables, column types, keys, constraints, enums, JSONB, soft delete, multi-tenant layout | [schema-design.md](references/schema-design.md) |
| Slow query, `EXPLAIN`, choosing an index, pagination, N+1, full-text search, counts | [indexes-queries.md](references/indexes-queries.md) |
| Writing or reviewing a migration, backfills, zero-downtime changes, ORM migration quirks | [migrations.md](references/migrations.md) |
| Lost updates, deadlocks, job queues in Postgres, isolation levels, pool sizing, PgBouncer, timeouts | [concurrency-connections.md](references/concurrency-connections.md) |
| Roles and privileges, row-level security for tenants, auditing, backups | [security-rls.md](references/security-rls.md) |

Vector search with `pgvector` for retrieval-augmented generation is covered by `llm-integration-typescript`; the indexing rules here still apply.

## Review checklist

Report each as pass or fail with `file:line` or the query that proves it.

- [ ] New columns are `NOT NULL` unless absence has a meaning; defaults are explicit
- [ ] Every foreign key column has an index; every new filter or sort on a large table has a matching index
- [ ] Money is not `float`/`real`/`double precision`; timestamps are `timestamptz`
- [ ] Migration is safe against the currently deployed code (no rename/drop of in-use columns or tables)
- [ ] Migration sets `lock_timeout`; indexes on existing tables built `CONCURRENTLY`
- [ ] Large backfills are batched outside the schema migration
- [ ] No raw SQL built with string interpolation of input
- [ ] List queries capped; deep `OFFSET` replaced by keyset pagination on large tables
- [ ] Read-modify-write paths lock, update atomically, or check a version
- [ ] Pool size × instances fits `max_connections`
- [ ] Application role is not superuser, not table owner, no `BYPASSRLS`

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| `ALTER TABLE … RENAME COLUMN` in the same release as the code change | Add new column, dual-write, backfill, switch reads, drop old later |
| `CREATE INDEX` on a busy table inside a transactional migration | `CREATE INDEX CONCURRENTLY` in a non-transactional migration |
| `ADD COLUMN … NOT NULL` with a backfill in one statement on a large table | Add nullable or with a constant default, backfill in batches, then enforce |
| `SELECT *` + `OFFSET 100000` | Selected columns + keyset pagination |
| `SELECT count(*)` on every list request | `hasMore` from fetching `limit + 1`, or an estimate |
| Status as free `text` with no check | `CHECK (status IN (…))` or a lookup table |
| `timestamp without time zone` storing UTC "by convention" | `timestamptz` |
| Pool of 50 per pod × 20 pods against `max_connections = 100` | Size pools from the connection budget, or put a pooler in front |
| Application connects as `postgres` | Dedicated least-privilege role |
