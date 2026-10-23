---
name: nestjs-best-practices
description: "NestJS + TypeScript on Model-Controller-Service-Repository layers: modules, DI, DTO validation, exception filters, guards, repositories, transactions, tests. Use when writing, refactoring or reviewing NestJS code. Node services without Nest belong to nodejs-typescript-best-practices."
license: MIT
metadata:
  tags: ["nestjs", "typescript", "nodejs", "architecture", "backend"]
---

# NestJS Best Practices (Model-Controller-Service-Repository)

Write NestJS code that any reviewer can place in one layer at a glance, that adds nothing the project does not already depend on, and that a test can exercise without a database.

## Cost rules — read first

These keep a run cheap and the diff small. They override any habit of "completing" a codebase.

- **Read only what the task needs.** Open the one reference below that matches the task; do not load all of them.
- **Match the project before the guide.** If the repo already has an ORM, validator, error shape, logger or test runner, use it. This skill states the target shape, not a library choice.
- **Add no dependency without asking.** A rule below that names a package (`@nestjs/throttler`, `nestjs-cls`, `helmet`) applies only when it is installed or the user agrees to add it.
- **Touch the smallest set of files.** Generate a feature's files only when asked to create the feature; never scaffold modules, barrels, base classes or "utils" nobody requested.
- **No speculative abstraction.** One implementation does not need a generic base repository, a factory or a strategy. Add the second layer of indirection when the second case exists.

## The four layers

| Layer | File | Owns | Never does |
|---|---|---|---|
| Model | `models/*.entity.ts`, `dto/*.dto.ts` | Domain/persistence shape; request and response DTOs with validation decorators | Business rules, I/O |
| Controller | `*.controller.ts` | Route, guards, pipes, mapping request DTO → service call → response DTO, status code | Business logic, repository or ORM access, `try/catch` for mapping errors |
| Service | `*.service.ts` | Business rules, orchestration, transaction boundary, throwing domain errors | `req`/`res`, HTTP status codes, ORM query builders |
| Repository | `*.repository.ts` | All data access for one aggregate; returns models; hides the ORM | Business decisions, calling services, HTTP concerns |

Dependency direction is one way: **Controller → Service → Repository → database**. Never skip a layer (controller → repository), never reverse it (repository → service), and never reach into another module's repository — call that module's exported service.

Feature layout (one folder per bounded feature):

```text
src/
  modules/orders/
    orders.module.ts
    orders.controller.ts
    orders.service.ts
    orders.repository.ts          # abstract class = DI token + contract
    prisma-orders.repository.ts   # implementation (only file that imports the ORM)
    models/order.entity.ts
    dto/create-order.dto.ts  dto/update-order.dto.ts  dto/order-response.dto.ts  dto/list-orders.query.ts
    orders.service.spec.ts
  common/   errors/  filters/  guards/  interceptors/  pipes/
  config/
  main.ts  app.module.ts
```

If the project already uses a different but consistent layout, keep it and map the four layers onto it.

## Shape of each layer

The repository contract is an abstract class so it doubles as the injection token — no `Symbol`, no `@Inject()`:

```ts
// orders.repository.ts
export abstract class OrdersRepository {
  abstract findById(id: string): Promise<Order | null>;
  abstract create(data: NewOrder): Promise<Order>;
}

// orders.module.ts
@Module({
  controllers: [OrdersController],
  providers: [OrdersService, { provide: OrdersRepository, useClass: PrismaOrdersRepository }],
  exports: [OrdersService],
})
export class OrdersModule {}

// orders.service.ts
@Injectable()
export class OrdersService {
  constructor(private readonly orders: OrdersRepository) {}

  async getById(id: string): Promise<Order> {
    const order = await this.orders.findById(id);
    if (!order) throw new NotFoundError('Order', id); // domain error, not HttpException
    return order;
  }
}

// orders.controller.ts
@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Get(':id')
  async get(@Param('id', ParseUUIDPipe) id: string): Promise<OrderResponseDto> {
    return OrderResponseDto.from(await this.ordersService.getById(id));
  }
}
```

A controller method is a few lines: call one service method, map the result. If it grows a branch on business state, that branch belongs in the service.

## Non-negotiables

1. **Global validation** — one `ValidationPipe` with `whitelist`, `forbidNonWhitelisted` and `transform`; every DTO property decorated. Details: [validation-dtos.md](references/validation-dtos.md).
2. **Never return an entity** from a controller. Map to a response DTO so internal fields (password hashes, soft-delete flags, foreign keys) cannot leak.
3. **Services throw transport-agnostic domain errors**; exactly one global exception filter maps them to HTTP. Details: [errors.md](references/errors.md).
4. **Only repository implementations import the ORM.** A service that imports `PrismaClient`, `Repository<T>` or a Drizzle table has skipped a layer.
5. **Constructor injection, `private readonly`**, default (singleton) scope. `REQUEST` scope propagates up every injector and costs an instance per request — use it only with a measured reason.
6. **Config is validated at boot** and injected via `ConfigService`; no `process.env` outside the config module.
7. **No `forwardRef`** to paper over a cycle. Extract the shared piece or emit an event. Details: [architecture.md](references/architecture.md).
8. **Strict TypeScript**: `strict: true`, no `any` (use `unknown` and narrow), explicit return types on public service and repository methods.

## Request lifecycle

Middleware → guards → interceptors (before) → pipes → handler → interceptors (after) → exception filters (on any throw). Put each concern at the earliest stage that has the information it needs: authentication in a guard, input shape in a pipe, response shaping or timing in an interceptor, error mapping in a filter. Never inside the handler.

## Pick the reference for the task

| Task | Read |
|---|---|
| New module, layer boundaries, cycles, DI scopes, cross-module calls, events | [architecture.md](references/architecture.md) |
| DTOs, `ValidationPipe`, query params, response serialization, OpenAPI decorators | [validation-dtos.md](references/validation-dtos.md) |
| Domain errors, exception filter, error envelope, logging failures | [errors.md](references/errors.md) |
| Repository implementations per ORM, transactions, N+1, pagination, migrations | [data-access.md](references/data-access.md) |
| Auth guards, roles, rate limiting, CORS, headers, secrets | [security.md](references/security.md) |
| Unit, integration and e2e tests | [testing.md](references/testing.md) |
| Caching, health checks, shutdown, logging, queues, performance | [operations.md](references/operations.md) |

The HTTP contract itself — URL naming, status codes, pagination format, versioning — is decided by the `api-design` skill when it is installed; this skill implements whatever contract it settles.

## Other frameworks

The same four layers apply outside Nest: Express, Fastify or Hono route handlers are the controller, plain classes wired in a composition root replace the DI container. Use `nodejs-typescript-best-practices` for that code.

## Review checklist

Report each item as pass or fail with the `file:line` that proves it.

- [ ] Every controller method calls a service and contains no business branching, ORM or repository use
- [ ] No service imports an ORM client, `Request`/`Response`, or `HttpException` subclasses (unless the project has deliberately chosen Nest exceptions in services — then flag it once, not per file)
- [ ] Every request DTO property has a validation decorator; global pipe has `whitelist` + `forbidNonWhitelisted` + `transform`
- [ ] No controller returns an entity or ORM object
- [ ] One global exception filter; no per-handler `try/catch` that only re-maps errors
- [ ] No `process.env` outside config; config validated at startup
- [ ] No `forwardRef`, no cross-module repository injection
- [ ] No new dependency added without the user's agreement
- [ ] Services are unit-tested with a fake repository; the test does not start a database

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| Fat controller with validation `if`s and queries | DTO + pipe for shape, service for rules, repository for queries |
| `throw new NotFoundException()` deep in a repository | Repository returns `null`; service decides whether absence is an error |
| One `SharedModule` exporting everything | Each feature module exports only the service others need |
| Generic `BaseRepository<T>` before a second entity needs it | Concrete repository; extract when duplication is real |
| `@Injectable({ scope: Scope.REQUEST })` to read the current user | Pass the user from the controller (`@CurrentUser()` decorator) or use AsyncLocalStorage |
| Entity class decorated for both ORM and `class-validator` and returned to clients | Separate entity, request DTO and response DTO |
