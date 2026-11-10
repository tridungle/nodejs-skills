# PostgreSQL: Migrations without downtime

Load when writing or reviewing a migration, planning a backfill, or changing a column that live code uses.

## The rule

During a deploy, old and new application versions run against the same database at the same time, and a failed deploy rolls back the code but not the schema. So every migration must work with **both** the code before it and the code after it.

## Expand → migrate → contract

A breaking change becomes several deploys:

1. **Expand**: add the new column, table or index. Nothing reads it yet. Old code is unaffected.
2. **Dual-write**: deploy code that writes both old and new shapes.
3. **Backfill**: copy existing data into the new shape, in batches.
4. **Switch reads**: deploy code that reads the new shape.
5. **Contract**: stop writing the old shape, then (in a later deploy) drop it.

Renaming a column or table, changing a type, splitting a table and moving data between tables all follow this path. Renames in place break the running version.

## Operation safety table

| Operation | Safe as one step? | Safe approach |
|---|---|---|
| Add a nullable column | Yes | — |
| Add a column with a constant default | Yes (PostgreSQL 11+ stores the default without rewriting) | Volatile defaults such as `random()` still rewrite: add nullable, backfill, then set default |
| Add `NOT NULL` to an existing column | No: scans the whole table under a strong lock | Add `CHECK (col IS NOT NULL) NOT VALID` → `VALIDATE CONSTRAINT` (weaker lock) → `SET NOT NULL` (PostgreSQL 12+ uses the valid check and skips the scan) → drop the check |
| Add a foreign key | No: validates every row under lock | `ADD CONSTRAINT … NOT VALID`, then `VALIDATE CONSTRAINT` in a separate step |
| Add a `CHECK` constraint | No | Same `NOT VALID` → `VALIDATE` pattern |
| Create an index on an existing table | No: blocks writes | `CREATE INDEX CONCURRENTLY`, outside a transaction; on failure drop the leftover `INVALID` index and retry |
| Add a unique constraint | No | `CREATE UNIQUE INDEX CONCURRENTLY`, then `ADD CONSTRAINT … UNIQUE USING INDEX` |
| Change a column type | Usually no: rewrites the table | New column + expand/contract (some widening changes, such as `varchar(n)` to `text`, are metadata-only) |
| Rename a column or table | No: breaks running code | Expand/contract, or a temporary view for tables |
| Drop a column | Only after no deployed code reads or writes it | Remove from code (and from ORM models that select all columns) first, drop in a later release |
| Drop a table | Only after no code references it | Rename-to-deprecated first if unsure, drop later |

## Locks and timeouts

- Even a fast `ALTER TABLE` needs a strong lock, and waiting for it queues every query behind it. Start each migration with `SET lock_timeout = '5s'` (and a `statement_timeout` sized for the step) so it fails fast instead of stalling the application; retry later.
- One risky operation per migration file, so a failure is easy to retry and reason about.
- Run migrations as a separate deploy step before the new code starts, not from every application instance on boot.

## Backfills

- Never in the same transaction as the schema change. Run as a script or job in batches (for example 1,000–10,000 rows by primary-key range), committing per batch, with a pause between batches if replicas lag.
- Idempotent: safe to stop and rerun (`WHERE new_col IS NULL`).
- Run `ANALYZE` on the table afterwards.

## ORM and tool notes

| Tool | Watch for |
|---|---|
| Prisma Migrate | Generated SQL uses plain `CREATE INDEX`, and a renamed field may come out as drop + add, losing data; edit the generated `migration.sql` before applying (`CONCURRENTLY`, expand/contract). Never `prisma db push` outside local development. |
| TypeORM | Never `synchronize: true` beyond local; set `transaction = false` on a migration class that uses `CONCURRENTLY`. |
| Drizzle Kit | Review generated SQL; renames may be detected as drop + add. Use custom SQL migrations for concurrent indexes and `NOT VALID` constraints. |
| Knex / node-pg-migrate | Disable the per-migration transaction for `CONCURRENTLY` (`config.transaction = false` / `pgm.noTransaction()`). |

## Review checklist

- [ ] Works with the currently deployed code (no rename, drop or type change of anything it uses)
- [ ] `lock_timeout` set; one risky operation per file
- [ ] Indexes on existing tables built concurrently, outside a transaction
- [ ] New constraints on existing data added `NOT VALID`, then validated
- [ ] Backfill separate, batched, idempotent
- [ ] Down migration exists if the project uses them, or the migration is documented as forward-only
- [ ] Applied to a copy with realistic data volume when the table is large
