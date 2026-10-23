# Data access: repositories, transactions, queries

Load when implementing a repository, adding a transaction, fixing slow queries, or writing a migration.

Use the ORM the project already has. The repository layer exists so the rest of the code does not care which one that is.

## Repository implementation per ORM

| ORM | Inject into the repository | Notes |
|---|---|---|
| Prisma | A `PrismaService` (extends `PrismaClient`, connects in `onModuleInit`) | Map Prisma's generated types to the model if they differ; translate `P2002` → `ConflictError`, `P2025` → return `null` |
| TypeORM | `@InjectRepository(OrderEntity) Repository<OrderEntity>` or `DataSource` | Keep the TypeORM `Repository<T>` private inside your repository; services never see it |
| Drizzle | The database instance via a custom token (`useFactory` building it from config) | Table definitions live with the repository; return inferred select types or mapped models |
| Mongoose | `@InjectModel(Order.name) Model<OrderDocument>` | Call `.lean()` for reads that return plain objects; map `_id` → `id` |
| MikroORM | `EntityManager` / `EntityRepository` | Flush in the service's unit of work, not inside every repository method |

The implementation is the only file importing the ORM. Name it by ORM (`PrismaOrdersRepository`) when the abstract class is the token, so swapping or faking stays obvious.

## Transactions

The **service** owns the transaction boundary because it knows which writes form one business operation. The repository must not start one on its own when called as part of a larger operation.

Pick one mechanism project-wide:

1. **Transaction-aware repositories** (no extra dependency): repository methods accept an optional transaction handle; the service opens the transaction via a small `TransactionRunner` provider (wraps `prisma.$transaction`, `dataSource.transaction`, `db.transaction`) and passes the handle down.
2. **AsyncLocalStorage**: `@nestjs-cls/transactional` (only if installed) puts the transaction in context; repositories read it implicitly and services use `@Transactional()`.

Rules either way:

- Keep transactions short: no HTTP calls, no email, no queue publishing inside one. Publish after commit (or use an outbox table if delivery must be guaranteed).
- Read-modify-write on contested rows needs a row lock or an optimistic version column; a transaction alone does not stop a lost update under the default isolation level.
- Tests for multi-write operations assert the rollback: force the second write to fail and check the first is gone.

## Query performance

- **N+1**: a loop calling the repository per item. Replace with one `findManyByIds(ids)` or an ORM include/join. Check by enabling query logging in a test and counting statements for a list of N items.
- **Select what is used**: list endpoints select the columns the response DTO needs, not `SELECT *` with large text/JSON columns.
- **Every list is paginated** with a hard maximum page size (e.g. 100). Prefer cursor (keyset) pagination for large or append-heavy tables; offset is fine below roughly ten thousand rows.
- **Index what you filter and sort by**, matching column order to the query. A new filter param without an index is a review finding.
- Counting totals on large tables is expensive; return `hasNext` instead of `total` unless the client needs it.

## Migrations

- Schema changes go through the ORM's migration tool and are committed; never `synchronize: true` (TypeORM) or `db push` (Prisma) outside local development.
- Migrations are forward-only in shared environments; a fix is a new migration.
- Destructive changes ship in two deployments: stop using the column, then drop it.
- Large backfills run in batches outside the migration that changes the schema.

## Connection handling

- One client/pool per process, created in a provider, closed in `onModuleDestroy` / `beforeApplicationShutdown`.
- Pool size from config; total across replicas must stay below the database's connection limit.
- Database URL and credentials come from `ConfigService`, never hard-coded, never logged.

## Checks

- Search services for ORM imports (`@prisma/client`, `typeorm`, `drizzle-orm`, `mongoose`) — each is a layer leak (types-only imports of generated models may be accepted if the project chose that).
- Search for `await` inside `for`/`map` over repository calls — candidate N+1.
- Search list repository methods for missing `take`/`limit`.
