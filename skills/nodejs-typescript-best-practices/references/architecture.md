# Architecture: layers, wiring, persistence

Load when adding a feature, moving code between layers, wiring dependencies, or implementing a repository or transaction.

## Layer contracts

- **Model** — plain types and schemas. A request schema (`CreateOrderInput`), a domain type (`Order`), a response shape (`OrderResponse`). No classes required; use classes only if the project does.
- **Controller** — the only code that sees the framework. Steps, always in this order: parse/validate input → call one service method → map result to response → set status. Errors are thrown, not formatted.
- **Service** — plain TypeScript. Takes typed inputs (never `req`), returns models, throws domain errors. Holds every business rule: state transitions, ownership checks, limits, calculations.
- **Repository** — an interface the service depends on, plus one implementation per storage. Methods named by intent (`findOpenByCustomer`), returning models or `null`.

Cross-feature calls go service → service, through what the other feature exports. Two services needing each other means a responsibility is misplaced: extract it or emit an event.

## Composition root

- `server.ts` (or `main.ts`) creates infrastructure (config, logger, db pool), constructs repositories, then services, then the app, then listens.
- `app.ts` exports `buildApp(deps)` returning the framework app without listening — tests call it with fakes.
- Wiring is explicit `new` calls in dependency order. When it grows past a screen, split by feature (`wireOrders(deps)`), not into a container.
- Use a DI container (`tsyringe`, `awilix`, `inversify`) only if the project already has one.

## Controllers per framework

| Framework | Controller form | Error routing |
|---|---|---|
| Express 4 | `(req, res, next)` handler or a class method bound to a router | Async errors must reach `next(err)`: wrap handlers or use the `express-async-errors` patch if already present |
| Express 5 | Same | Rejected promises go to the error middleware natively |
| Fastify | Route handler; prefer JSON schema or a type provider (`@fastify/type-provider-*`) for validation | `setErrorHandler` |
| Hono | `(c) => …` with a validator middleware | `app.onError` |
| Koa | Middleware | Top-level `try/catch` middleware |

A controller may be a class (`new OrderController(orderService)` with methods registered on a router) or a function factory `orderRoutes(orderService)`. Pick the one the codebase uses.

## Repository implementation

| Storage | Implementation notes |
|---|---|
| Prisma | Inject the `PrismaClient`; translate `P2002` → `ConflictError`, `P2025` → `null` |
| Drizzle / Kysely | Inject the db instance; keep table definitions next to the repository |
| TypeORM / MikroORM | Inject `DataSource` / `EntityManager`; the ORM's repository stays private |
| `pg` / `mysql2` raw | Parameterised queries only (`$1`, `?`); map rows to models in one function |
| Mongoose / MongoDB driver | `.lean()` or projection; map `_id` → `id` |

Only repository implementations import the ORM or driver. An in-memory implementation of the interface is the default test double.

## Transactions

- The service owns the boundary (it knows the business operation); repositories accept an optional transaction handle (`tx`) on write methods, or a unit-of-work object exposes repositories bound to one transaction.
- A small `runInTransaction(fn)` function wrapping the ORM's API keeps the ORM out of the service.
- AsyncLocalStorage-based transaction context is acceptable when the project already uses it; do not introduce it for one call site.
- No network calls, emails or queue publishes inside a transaction. Publish after commit, or write to an outbox table when delivery must be guaranteed.

## Query rules

The `database-best-practices` skill (when installed) covers query plans, index choice, zero-downtime migrations, locking and pool sizing in depth for PostgreSQL, MongoDB and vector stores.

- Every list query has a limit with a hard maximum; cursor pagination for large or growing tables.
- No queries in loops (N+1); fetch by id list or join.
- Filter and sort columns are allow-listed, then indexed.
- Migrations are committed files run by the migration tool, never schema sync in shared environments.

## Feature folders vs layer folders

Group by feature (`modules/orders/*`) rather than by layer (`controllers/`, `services/`, `repositories/`). A change to one feature then touches one folder, and deleting a feature is deleting a directory. Keep a layer-grouped project as it is unless the user asks to restructure.
