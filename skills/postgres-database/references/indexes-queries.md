# Indexes and query performance

Load when a query is slow, when choosing an index, or when reviewing list, search and count queries.

## Find the slow queries first

- `pg_stat_statements` (enable it if the user agrees; most managed services ship it): sort by `total_exec_time` for the biggest overall cost, by `mean_exec_time` for the slowest single calls, and look at `calls` for N+1 patterns (one cheap query called thousands of times).
- Application logs with query duration per request, or the ORM's query logging in a test, to count queries per endpoint.
- Fix the top few; tuning a query that runs once a day rarely matters.

## Read the plan

`EXPLAIN (ANALYZE, BUFFERS)` the exact query with realistic parameters on a realistic data volume. `ANALYZE` executes the statement: for `INSERT`/`UPDATE`/`DELETE`, wrap it in `BEGIN; … ROLLBACK;`, and do not run it against production writes.

| In the plan | Usually means |
|---|---|
| `Seq Scan` on a large table with a selective `WHERE` | Missing or unusable index (function on the column, type mismatch, leading column not used) |
| Estimated rows far from actual rows | Stale statistics (`ANALYZE table`), or correlated columns that need extended statistics |
| `Nested Loop` with a large outer side and an inner `Seq Scan` | Missing index on the join column |
| `Sort` with `external merge` / disk | Sorting many rows: add an index matching `ORDER BY`, or reduce rows first |
| `Rows Removed by Filter` large after an `Index Scan` | Index only covers part of the predicate; extend or reorder it |
| High `shared read` vs `shared hit` | Data not in cache: the query reads too much; select fewer rows or columns |

## Choosing an index

- **B-tree** (default) for equality, ranges and sorting. In a composite index: equality columns first, then the range or sort column. `(tenant_id, status, created_at DESC)` serves `WHERE tenant_id = $1 AND status = $2 ORDER BY created_at DESC`.
- **Partial index** when queries always filter on a condition: `WHERE deleted_at IS NULL`, `WHERE status = 'pending'`. Smaller and faster.
- **Covering index** with `INCLUDE (…)` to allow index-only scans for hot read paths.
- **Expression index** when the query applies a function: `lower(email)` needs an index on `lower(email)`.
- **GIN** for `jsonb` containment (`@>`), arrays, and full-text `tsvector`.
- **Trigram (`pg_trgm`) GIN** for `ILIKE '%term%'` and fuzzy search. A plain B-tree cannot serve a leading wildcard.
- **BRIN** for huge append-only tables queried by time range.
- Every index slows writes and uses memory: check `pg_stat_user_indexes.idx_scan` for indexes never used, and indexes that are a prefix of another, before adding more.
- On existing tables, build with `CREATE INDEX CONCURRENTLY` (see [migrations.md](migrations.md)).

## Query rules

- **Select the columns you need.** Wide `text`/`jsonb` columns in `SELECT *` on list endpoints cost I/O and memory.
- **No N+1**: load related rows with a join or one `WHERE id = ANY($1)` query, not one query per row. ORMs: use their include/relation loading deliberately and check the generated SQL.
- **Keyset pagination** on large or growing tables:
  `WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT $3`, backed by an index on `(created_at DESC, id DESC)` (with `tenant_id` first when scoped). Always include a unique tie-breaker.
- **Deep `OFFSET`** reads and discards every skipped row; fine for small admin tables, not for feeds.
- **Counts**: `count(*)` on a large filtered set is a full scan of the matching rows. Return `hasMore` by fetching `limit + 1`; for an approximate total, use the planner estimate (`reltuples` or `EXPLAIN` row estimate) and label it as approximate.
- **`IN` with huge lists**: pass an array parameter with `= ANY($1)`; above a few thousand ids, join against `unnest($1)` or a temporary table.
- **Upserts**: `INSERT … ON CONFLICT (key) DO UPDATE` instead of select-then-insert, which races.
- **Bulk writes**: multi-row `INSERT` or `COPY` instead of one statement per row; batch large `UPDATE`/`DELETE` by primary-key ranges.
- **Avoid functions on indexed columns in `WHERE`** (`date(created_at) = $1`): write a range (`created_at >= $1 AND created_at < $2`) instead.

## Full-text search

For search inside the database: a generated `tsvector` column (`GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED`) with a GIN index, queried with `websearch_to_tsquery`. Choose the text-search configuration matching the content's language. Move to a dedicated search engine only when ranking, typo tolerance or scale demand it.

## Statistics and maintenance

- Autovacuum must keep up: check `pg_stat_user_tables` for `n_dead_tup` growing and `last_autovacuum` stale on hot tables; tune per-table autovacuum settings rather than running manual `VACUUM FULL`, which locks the table.
- After a large backfill or bulk load, run `ANALYZE` on the table so the planner sees the new distribution.
- Long-running transactions block vacuum cleanup across the database; find them in `pg_stat_activity` (`xact_start`).

## Checks

- The plan for each new or changed hot query uses an index scan on realistic data volume.
- No new filter or sort column on a large table without a matching index.
- Query count per request does not grow with the number of items returned.
