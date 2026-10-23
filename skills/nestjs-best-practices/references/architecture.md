# Architecture: modules, layers, DI

Load when creating a module, moving code between layers, untangling a dependency cycle, or choosing a provider scope.

## Module boundaries

- One module per feature (bounded context): `OrdersModule`, `UsersModule`, `BillingModule`. Name by business capability, not by technical type (`ServicesModule`, `HelpersModule` are smells).
- A module `exports` only the service other modules may call. Repositories, mappers and internal helpers stay private.
- A module imports the modules whose exported services it uses — never their providers directly.
- `@Global()` is for true infrastructure only (config, database connection, logger). A global feature module hides its dependents.
- Infrastructure modules that need configuration expose `forRoot`/`forRootAsync` (or `ConfigurableModuleBuilder`); feature modules do not.

## Layer rules, stated as checks

| Check | Fails when |
|---|---|
| Controller → Service only | A controller constructor injects a repository, ORM client, `DataSource`, `PrismaService` |
| Service holds the rules | A business condition (status transitions, ownership, limits) appears in a controller, guard or repository |
| Repository holds the queries | A service builds a query, calls `.createQueryBuilder`, `prisma.x.findMany`, `db.select` |
| Models are plain | An entity imports a service or performs I/O |
| Domain errors are transport-agnostic | A service or repository throws `HttpException` or sets a status code (see [errors.md](errors.md)) |

A service may call another service of the same module and exported services of imported modules. Two services that need each other mean a responsibility is in the wrong place.

## Repository contract as an abstract class

TypeScript interfaces vanish at runtime, so Nest cannot inject by interface. Use an abstract class: it is the type, the contract and the token at once.

- Declare the methods the service needs, named by intent (`findActiveByCustomer`, not `query`).
- Return models (or `null` for absence), never ORM result wrappers or query builders.
- Accept plain inputs (`NewOrder`, filters object), never a request DTO — DTOs belong to the HTTP edge. The service maps DTO → domain input.
- Bind in the module: `{ provide: OrdersRepository, useClass: PrismaOrdersRepository }`. Tests bind a fake with `useValue`.

When the project already uses `Symbol`/string tokens with `@Inject()`, keep that style; do not mix both in one codebase.

## Model vs DTO vs response

- **Entity / model** — the domain or persistence shape. Owned by the repository layer; may carry ORM decorators if the ORM requires it (TypeORM, MikroORM).
- **Request DTO** — what a client may send. `class-validator` decorators live here and nowhere else.
- **Response DTO** — what a client may see. Built by an explicit mapping (`static from(entity)`) or a serializer; lists fields deliberately.
- Domain input types (`NewOrder`) — plain TS types the service passes to the repository.

Small CRUD features may let the service accept the request DTO directly; do not introduce a separate input type until the shapes diverge.

## Breaking dependency cycles

`forwardRef()` makes the cycle work at runtime and keeps the design wrong. In order of preference:

1. **Move the shared logic down** into a third module both import (often the cycle is two services sharing one calculation).
2. **Invert with an event**: module A emits `order.paid`, module B listens. Use `@nestjs/event-emitter` if installed, otherwise a small in-process publisher service. Events suit side effects (emails, audit, cache busting), not reads that need a return value.
3. **Pass data in** instead of looking it up: the caller already has the value the callee would fetch.

File-level cycles (barrel `index.ts` re-exporting a module that imports the barrel) cause `undefined` providers at boot. Import from the concrete file inside a feature.

## Provider scopes

| Scope | Use for | Cost |
|---|---|---|
| `DEFAULT` (singleton) | Services, repositories, stateless helpers — almost everything | None |
| `REQUEST` | Rare: per-request state that cannot be passed as an argument | New instance of the provider **and every provider that depends on it** per request |
| `TRANSIENT` | A stateful helper each consumer needs its own copy of | Instance per injection |

For per-request context (current user, tenant, correlation id) prefer passing it as an argument from the controller, or AsyncLocalStorage (`nestjs-cls` if installed). Both keep the whole graph singleton.

## Custom providers

- `useClass` — swap implementations (repository per ORM, fake in tests).
- `useValue` — constants, fakes.
- `useFactory` + `inject` — needs config or async setup (a client built from `ConfigService`).
- `useExisting` — alias one token to another.

Async factories run at boot; a failing factory must fail the boot, not log and continue.

## Cross-cutting placement

| Concern | Mechanism | Registered |
|---|---|---|
| Authentication, authorization | Guard | Globally via `APP_GUARD`, opt-out with a `@Public()` metadata decorator |
| Input transformation/validation | Pipe | Global `ValidationPipe`; param pipes (`ParseUUIDPipe`) per route |
| Logging, timing, response mapping, caching | Interceptor | `APP_INTERCEPTOR` or per controller |
| Error → HTTP mapping | Exception filter | `APP_FILTER` (DI-aware, unlike `useGlobalFilters`) |
| Raw request concerns before routing (body size, request id) | Middleware | `configure(consumer)` in `AppModule` |

Prefer `APP_*` providers over `app.useGlobal*()` in `main.ts`: they get dependency injection and are picked up by e2e tests that build `AppModule`.
