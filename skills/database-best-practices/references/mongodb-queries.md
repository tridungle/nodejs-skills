# MongoDB: indexes and query performance

Load when a MongoDB query or aggregation is slow, when choosing an index, or when reviewing list and search queries.

## Find the slow queries first

- The database profiler or slow-query log (managed services expose a query profiler and index suggestions): sort by total time and by frequency.
- Driver or Mongoose debug logging in a test to count queries per request; `populate` hides extra queries the same way an ORM hides N+1.
- Fix the top few; a query that runs once a day rarely matters.

## Read the plan

Run `explain("executionStats")` on the exact query with realistic data.

| In the output | Usually means |
|---|---|
| `COLLSCAN` stage on a large collection | No usable index |
| `totalDocsExamined` far above `nReturned` | Index does not cover the filter well: wrong field order, or a field missing from it |
| `totalKeysExamined` far above `nReturned` | Range field placed before equality or sort fields in the index |
| A blocking `SORT` stage | No index provides the sort order; large sorts hit the in-memory limit and fail or spill to disk |
| `FETCH` after `IXSCAN` on a hot read | Could be a covered query with a projection limited to indexed fields |

## Choosing an index

- **Compound index order follows ESR**: Equality fields first, then Sort fields, then Range fields. `{ tenantId: 1, status: 1, createdAt: -1 }` serves "this tenant, this status, newest first, created after X".
- One compound index often serves several queries through its prefixes; check before adding another.
- **Partial indexes** for queries that always include a condition (`{ deletedAt: null }`, `{ status: "pending" }`); **unique** and **partial unique** indexes for business uniqueness.
- **TTL indexes** for data that should expire (sessions, tokens, temporary records).
- **Multikey indexes** index each array element; a compound index can contain at most one array field.
- Text search: a text index for simple keyword search; the managed search service when ranking, typo tolerance or facets are needed.
- Every index costs RAM and slows writes: remove indexes with no usage in the index statistics, and indexes that are a prefix of another.

## Creating indexes safely

- Mongoose's `autoIndex` builds indexes on application start; turn it off in production and create indexes through a migration or deployment script, so a large build does not start unannounced on every deploy.
- Index builds on large collections still consume heavy resources; run them at low traffic and watch replication lag.

## Query rules

- **Project only the fields needed**; with Mongoose use `select()` and `lean()` for reads.
- **No N+1**: fetch related documents with one `$in` query on the ids, or a single `$lookup` with an index on the foreign field; limit `populate` to what the response uses.
- **Range pagination**: filter on the sort key plus `_id` as tie-breaker (`{ createdAt: { $lt: lastCreatedAt } }` or `{ _id: { $lt: lastId } }`) with a matching index; `skip()` reads and discards every skipped document.
- **Counts**: `countDocuments` with a filter scans the matches; use `hasMore` from fetching `limit + 1`, and `estimatedDocumentCount` only for whole-collection approximations.
- **Atomic updates instead of read-modify-write**: `$inc`, `$set`, `$push` with `$slice`, `$addToSet`, and filters that encode the precondition (see [mongodb-operations.md](mongodb-operations.md)).
- **Bulk writes**: `bulkWrite` / `insertMany` with `ordered: false` for independent documents, in batches of a few hundred to a few thousand.
- **Time limits**: `maxTimeMS` on queries that could run long, so a bad query fails instead of piling up.
- **Large result sets**: stream with a cursor instead of loading arrays into memory.

## Aggregation pipelines

- `$match` (and `$project` / `$unset` of unused fields) as early as possible so indexes apply and less data flows through.
- `$sort` + `$limit` adjacent so the server keeps only the top results.
- `$lookup` on an indexed foreign field, after filtering; avoid `$lookup` inside a per-document loop.
- `$group` on huge inputs may exceed the stage memory limit; filter first, or allow disk use deliberately for batch jobs, not request paths.
- Heavy reporting pipelines run against a secondary or an analytics node, not the primary that serves user requests, when the deployment offers one.

## Checks

- Every hot query's plan uses `IXSCAN` with `totalDocsExamined` close to `nReturned`.
- No new filter or sort field on a large collection without a matching compound index in ESR order.
- Query count per request does not grow with the number of items returned.
