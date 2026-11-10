# MongoDB: concurrency, schema evolution, connections and security

Load when concurrent writes can conflict, when using transactions, when changing the shape of stored documents, when sizing connections, or when reviewing MongoDB security.

## Concurrency without transactions first

A write to a single document is atomic. Prefer designs where one business operation changes one document:

| Situation | Tool |
|---|---|
| Counter, stock, balance | `$inc` with a guard in the filter: `updateOne({ _id, stock: { $gte: qty } }, { $inc: { stock: -qty } })`; zero `modifiedCount` → domain error |
| State transition | Filter on the expected current state: `{ _id, status: "pending" }` → `$set` new status; zero matches → `ConflictError` |
| Concurrent edits of a whole document | Optimistic concurrency: a version field in the filter and `$inc` on it (Mongoose: `optimisticConcurrency: true` on the schema) |
| Insert if absent | Unique index + upsert, handling the duplicate-key error (`11000`) as a conflict |
| Claiming work items | `findOneAndUpdate` that sets an owner and status in one step |

## Multi-document transactions

- Require a replica set or sharded cluster, including in local development and tests (a single-node replica set works).
- Use them when one operation must change several documents atomically; keep them short (few documents, no external calls), because long transactions hold resources and are aborted after the server's time limit.
- Use the driver's callback-style transaction helper (or Mongoose's equivalent), which retries on transient errors and unknown commit results; pass the session to **every** operation inside, or that operation runs outside the transaction.
- Use majority write concern for writes that must survive a primary failover.

## Read consistency

- Reads from secondaries can be stale; read your own writes from the primary.
- Pick read and write concerns per use case (important writes: majority; analytics reads: secondary preferred) and document the choice.

## Changing document shape

There is no schema migration step built into MongoDB; old and new shapes coexist unless you change them.

- Follow expand → migrate → contract: write code that reads both shapes and writes the new one, backfill old documents, then remove support for the old shape.
- Mark shapes with a `schemaVersion` field when more than one change is in flight.
- Backfills: a migration script in the project's tool (or a versioned script folder), processing documents in batches with `bulkWrite`, idempotent (filter on the old shape), resumable, and throttled to watch replication lag.
- Renaming a field is a shape change: add the new field, dual-write, backfill, switch reads, then `$unset` the old field later.
- Update the collection's `$jsonSchema` validator in step with the code: loosen it before writing the new shape, tighten it after the backfill.

## Connections

- One `MongoClient` (or one Mongoose connection) per process, created at startup and reused; never one per request. Serverless functions reuse a client across invocations.
- The driver pools connections per client; size `maxPoolSize` from the budget: pool size × processes × replicas must fit the server's connection limit for the cluster tier.
- Set `serverSelectionTimeoutMS` (fail fast when the cluster is unreachable) and per-operation time limits; close the client on shutdown.
- Mongoose buffers commands while disconnected by default; disable buffering in services that should fail fast instead of queueing requests.

## Security

- A dedicated database user per application with only the roles it needs (read-write on its own database), never a cluster admin or root user; a separate user for migrations and backfills.
- TLS on, network access restricted to known sources (private networking or an IP allow-list), credentials from the secret store.
- **Operator injection**: a request body like `{ "email": { "$ne": null } }` turns an equality check into "match anything". Validate that query inputs are scalars of the expected type at the boundary, reject keys starting with `$` or containing `.`, and enable Mongoose's `sanitizeFilter` (or the equivalent) as a second layer.
- Never pass user input into `$where`, `$function` or `$accumulator`, which execute JavaScript on the server.
- Encrypt highly sensitive fields at the application level or with the database's field-level encryption when offered.

## Backups

- Use point-in-time backups from the hosting platform, or scheduled dumps plus oplog-based recovery when self-managed.
- Prove backups with periodic restores into a scratch cluster, and write down the achievable recovery time and data-loss window.
