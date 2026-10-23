# Concurrency, transactions and connections

Load when two requests can change the same data, when deadlocks or lock waits appear, when using Postgres as a job queue, or when sizing connection pools.

## Isolation levels

- Default is `READ COMMITTED`: each statement sees data committed before it started. It does **not** prevent lost updates in read-modify-write code.
- `REPEATABLE READ`: one snapshot for the whole transaction; concurrent updates to the same row fail with a serialization error (`40001`) instead of silently overwriting.
- `SERIALIZABLE`: behaves as if transactions ran one at a time; any transaction may fail with `40001`.
- Raising the level means **the service must retry** the whole transaction on `40001` (and on deadlock `40P01`), with a small capped backoff. Without retry code, a higher level just turns races into errors.

## Preventing lost updates

Pick the lightest tool that fits:

| Situation | Tool |
|---|---|
| Counter or balance change | Atomic update: `UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1`; check affected rows |
| Edit form where users may overwrite each other | Optimistic: `UPDATE … SET …, version = version + 1 WHERE id = $1 AND version = $2`; zero rows → `ConflictError` (HTTP 409/412) |
| Multi-step decision on one row inside a transaction | Pessimistic: `SELECT … FOR UPDATE` then update in the same transaction |
| Insert-if-absent | `INSERT … ON CONFLICT DO NOTHING / DO UPDATE` with a unique constraint |
| Only one worker may run a task | Advisory lock: `pg_try_advisory_xact_lock(key)` in a transaction |

## Deadlocks

- Two transactions locking the same rows in opposite order. Lock rows in a consistent order (e.g. sort ids before `FOR UPDATE`), keep transactions short, and retry on `40P01`.
- Foreign keys take share locks on parent rows; heavy concurrent inserts referencing one parent row can contend.

## Postgres as a job queue

Fine for moderate volumes when the project has no queue system:

- Claim: `SELECT … FROM jobs WHERE status = 'pending' AND run_at <= now() ORDER BY run_at LIMIT 10 FOR UPDATE SKIP LOCKED`, then mark them running in the same transaction.
- Partial index on `(run_at) WHERE status = 'pending'`.
- Record attempts and the last error; move to `failed` after a maximum number of attempts; make job handlers idempotent.
- Delete or archive finished jobs so the table stays small.
- `LISTEN/NOTIFY` can wake workers, but needs a dedicated session connection (not through a transaction-mode pooler) and is a hint, not delivery: workers still poll.

## Transactions in practice

- Keep them short: no HTTP calls, no waiting for users, no large loops inside. Long transactions hold locks and block vacuum.
- Set `idle_in_transaction_session_timeout` (e.g. 30–60s) on the application role so a crashed request cannot hold locks forever.
- Set a `statement_timeout` for the application role (e.g. a few seconds for an API) and raise it only for specific long operations.
- Reading your own write: replicas lag; read from the primary right after writing, or the user sees stale data.

## Connection pools

- Each Postgres connection is a backend process with real memory; hundreds of mostly idle connections hurt performance.
- **Budget**: `pool size per instance × instances (+ workers, cron, migrations, admin)` < `max_connections`, with a margin. Recompute when autoscaling limits change.
- Pool sizes are usually small: start near (CPU cores of the database × 2) **in total across all clients**, not per instance, then measure. Queries waiting for a pool connection is a cheaper failure than the database thrashing.
- Set pool timeouts: wait-for-connection timeout, idle timeout, and close the pool on shutdown.
- Prisma: `connection_limit` in the URL; `pg`: `max` on the `Pool`; TypeORM/Drizzle/Knex: their pool options. Each process has its own pool: count processes, not services.

## PgBouncer and other poolers

- Needed when instance counts are high or serverless functions open connections per invocation.
- **Transaction pooling** gives the biggest saving but breaks session state: session-level `SET`, session advisory locks, `LISTEN`, temporary tables across transactions, and (on older PgBouncer versions) named prepared statements. Use `SET LOCAL` inside transactions, transaction-scoped advisory locks, and check the pooler's prepared-statement support against the ORM's settings.
- Migrations and `LISTEN` connect directly to Postgres, not through a transaction pooler.

## Checks

- Every read-modify-write path names its protection (atomic update, version check, row lock or unique constraint).
- Code running at `REPEATABLE READ` or `SERIALIZABLE` retries on `40001`.
- No transaction spans an external call.
- The connection budget is written down and fits `max_connections`.
