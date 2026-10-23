# Schema design

Load when creating tables, choosing column types and keys, or adding constraints.

## Keys

- **Primary key on every table.** Two good defaults; follow the project:
  - `bigint GENERATED ALWAYS AS IDENTITY`: small, fast, ordered. Do not expose it in public URLs for user-owned data (it reveals volume and invites enumeration); add a separate public id if needed.
  - `uuid`: safe to expose, generated anywhere. Prefer time-ordered UUIDv7 (native `uuidv7()` from PostgreSQL 18, or generated in the application on older versions) over random v4, which scatters inserts across the index.
- Avoid `serial` in new schemas; identity columns are the standard replacement.
- Natural keys (email, SKU) get a `UNIQUE` constraint, not the primary key; they change.
- Join tables use a composite primary key of the two foreign keys, plus an index on the second column alone if queried from that side.

## Column types

| Data | Type | Avoid |
|---|---|---|
| Point in time | `timestamptz` (stored as UTC, converted on output) | `timestamp` without time zone |
| Calendar date | `date` | A timestamp at midnight |
| Money | `numeric(p, s)` or `bigint` minor units + currency code column | `float`, `real`, `double precision`, `money` |
| Text | `text`, with `CHECK (char_length(x) <= n)` when a limit is a business rule | `varchar(n)` as a habit, `char(n)` |
| Flags | `boolean NOT NULL DEFAULT false` | Nullable booleans (three states nobody planned) |
| Closed set of values | `text` + `CHECK (x IN (…))`, or a lookup table with a foreign key | Postgres `ENUM` types when values may ever be removed or reordered: adding is easy, removing is not |
| Semi-structured documents | `jsonb` | `json` (no indexing, keeps duplicates); also `jsonb` for data you filter on constantly: make those real columns |
| IP addresses, ranges | `inet`, `tstzrange`, `int4range` | Two text or integer columns |

## Constraints

- `NOT NULL` unless absence has a defined meaning; document that meaning in a column comment.
- Foreign keys on every reference, with an explicit `ON DELETE` (`RESTRICT` by default; `CASCADE` only for true ownership, such as order lines belonging to an order).
- **Index every foreign key column**: Postgres does not do it automatically, and without the index, deletes on the parent and joins from it scan the child table.
- `CHECK` constraints for invariants within a row: `quantity > 0`, `ends_at > starts_at`, allowed status values.
- `UNIQUE` for business uniqueness, including partial uniqueness: `UNIQUE (email) WHERE deleted_at IS NULL` as a partial unique index.
- Exclusion constraints (`EXCLUDE USING gist`) for "no overlapping bookings" rules.
- Name constraints explicitly (`orders_customer_id_fkey`, `orders_quantity_positive`) so error messages and migrations are readable, and the repository can map a specific constraint to a specific domain error.

## Common columns

- `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()`. Maintain `updated_at` in one place: an ORM hook or a trigger, not both.
- Optimistic locking: `version integer NOT NULL DEFAULT 0`, incremented on every update (see [concurrency-connections.md](concurrency-connections.md)).

## Soft delete

- Only when there is a requirement (undo, audit, legal hold). It costs a filter on every query and complicates uniqueness.
- If used: `deleted_at timestamptz NULL`, partial indexes and partial unique constraints `WHERE deleted_at IS NULL`, and the repository applies the filter so services cannot forget it.
- For audit history, an append-only history table is often better than soft delete.

## Multi-tenancy

- **Shared tables with a `tenant_id` column** is the usual default: `tenant_id` is `NOT NULL`, leads every composite index used by tenant-scoped queries, and appears in foreign keys between tenant-owned tables where practical so rows cannot point across tenants.
- Enforce isolation in two places: the repository always filters by tenant, and optionally row-level security as the backstop (see [security-rls.md](security-rls.md)).
- Schema-per-tenant or database-per-tenant only for strong isolation requirements; they multiply migrations and connections.

## Naming

`snake_case`, plural table names or singular: follow the existing schema. Columns that reference another table are `<table_singular>_id`. Booleans read as predicates (`is_active`, `has_paid`). ORMs that expect camelCase map names in the model layer rather than quoting identifiers in the database.

## Large tables

- Time-series or append-only data: a BRIN index on the timestamp column is tiny and effective.
- Partitioning (by time range or by tenant) helps when old data must be dropped cheaply or tables reach hundreds of millions of rows; it adds planning and migration complexity, so it is a measured decision, not a default.
