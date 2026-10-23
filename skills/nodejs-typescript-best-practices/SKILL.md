---
name: nodejs-typescript-best-practices
description: "Node.js + TypeScript backends without NestJS (Express, Fastify, Hono, plain http): Model-Controller-Service-Repository layers, strict tsconfig, boundary validation, typed errors, config, graceful shutdown, tests. Use when writing, refactoring or reviewing such code."
license: MIT
metadata:
  tags: ["nodejs", "typescript", "express", "fastify", "architecture", "backend"]
---

# Node.js + TypeScript Best Practices (Model-Controller-Service-Repository)

Structure a Node.js service so each file sits in one layer, the domain code does not know which HTTP framework or ORM is underneath, and the project gains no dependency it did not ask for. For NestJS projects use `nestjs-best-practices` instead.

## Cost rules — read first

- **Read only the reference the task needs**; do not preload all of them.
- **Match the project first.** Its framework, validator (Zod, Valibot, TypeBox, Joi), ORM, logger, test runner and module system win over any preference here.
- **Add no dependency without asking.** No DI container, no "Result" library, no framework swap. Node's standard library (`node:test`, `AsyncLocalStorage`, `fetch`, `AbortSignal.timeout`, `util.parseArgs`) covers more than it used to — prefer it when the project has nothing.
- **Smallest diff that satisfies the request.** No scaffolding, base classes, barrels or helpers that the current task does not use.

## The four layers

| Layer | File | Owns | Never does |
|---|---|---|---|
| Model | `*.model.ts`, `*.schema.ts` | Domain types; request/response schemas and the types inferred from them | I/O, framework imports |
| Controller | `*.controller.ts` (or `*.routes.ts`) | Parse and validate input, call one service method, map result to response, set status | Business rules, database access |
| Service | `*.service.ts` | Business rules, orchestration, transaction boundary, throwing domain errors | Touching `req`/`res`, status codes, SQL/ORM calls |
| Repository | `*.repository.ts` | All persistence for one aggregate; returns models; translates driver errors | Business decisions, calling services |

Direction is one way: **Controller → Service → Repository → database**. No skipping, no reversing, no reaching into another feature's repository.

```text
src/
  modules/orders/
    order.model.ts          # types + schemas (Zod etc.)
    order.controller.ts     # framework-specific edge
    order.service.ts        # pure TS, no framework import
    order.repository.ts     # interface + implementation (only ORM importer)
    order.service.test.ts
  shared/  errors.ts  http/error-handler.ts  logger.ts
  config.ts                 # validated env, exported typed object
  app.ts                    # builds the app from dependencies (testable)
  server.ts                 # composition root: wires deps, listens, handles signals
```

## Dependency injection without a container

Constructor injection plus one composition root. Classes receive their collaborators; only `server.ts` (and tests) call `new`.

```ts
// order.service.ts
export class OrderService {
  constructor(private readonly orders: OrderRepository) {}

  async getById(id: string): Promise<Order> {
    const order = await this.orders.findById(id);
    if (!order) throw new NotFoundError('Order', id);
    return order;
  }
}

// server.ts — the only place that knows concrete implementations
const db = createDb(config.databaseUrl);
const orderService = new OrderService(new SqlOrderRepository(db));
const app = buildApp({ orderService });
```

Factory functions returning objects (`createOrderService(deps)`) are equally fine; follow what the codebase does. Module-level singletons imported directly (`import { db } from './db'`) inside services make them untestable without module mocking — replace them when touching that code.

## Non-negotiables

1. **Strict TypeScript**: `strict`, `noUncheckedIndexedAccess`, no `any` — `unknown` at boundaries then narrow. Details: [typescript.md](references/typescript.md).
2. **Validate at every boundary** (HTTP input, env, queue messages, third-party responses) with a schema; derive the type from the schema. Details: [validation-config.md](references/validation-config.md).
3. **Domain errors in services, one error handler at the edge** mapping them to HTTP. Details: [errors-async.md](references/errors-async.md).
4. **Every promise is awaited or handled**; async route errors reach the error handler (Express 4 needs this wired; Express 5, Fastify and Hono do it natively).
5. **Config validated at startup**, read from one module; no `process.env` elsewhere.
6. **Graceful shutdown** on SIGTERM/SIGINT; close the server, then pools. Details: [production.md](references/production.md).
7. **Responses are mapped**, never the raw database row.

## Pick the reference for the task

| Task | Read |
|---|---|
| Layer boundaries, composition root, framework mapping, repositories, transactions | [architecture.md](references/architecture.md) |
| `tsconfig`, ESM vs CommonJS, type patterns, linting | [typescript.md](references/typescript.md) |
| Error classes, error middleware, async pitfalls, process handlers | [errors-async.md](references/errors-async.md) |
| Request validation, env config, external data | [validation-config.md](references/validation-config.md) |
| Unit, integration and HTTP tests | [testing.md](references/testing.md) |
| Logging, shutdown, health, security headers, performance | [production.md](references/production.md) |

URL design, status codes, the error envelope and pagination format belong to the `api-design` skill when installed. Comments and TSDoc follow the `code-comments` skill when installed.

## Other frameworks

The controller is the only framework-specific layer. Express `(req, res, next)` handlers, Fastify route handlers with a JSON schema or type provider, Hono `c` handlers and Koa middleware all play the same role: parse, call service, map. Moving between them rewrites controllers and the error handler only. For NestJS, use `nestjs-best-practices`.

## Review checklist

Report each item as pass or fail with the `file:line` that proves it.

- [ ] Services and repositories import nothing from the HTTP framework
- [ ] Controllers contain no SQL/ORM calls and no business branching
- [ ] Every input boundary validates with a schema; no `req.body as Foo`
- [ ] One error handler maps domain errors; no per-route catch-and-format blocks
- [ ] No floating promises; async errors reach the handler
- [ ] `process.env` read only in the config module, validated at boot
- [ ] SIGTERM closes the server and pools within a deadline
- [ ] `tsconfig` is strict; no new `any`, no `@ts-ignore` without a reason comment
- [ ] No new dependency added without the user's agreement
- [ ] Services tested with an in-memory repository, no database

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| Route handler with 80 lines of validation, queries and rules | Schema at the edge, rules in a service, queries in a repository |
| `req.body as CreateOrder` | Parse with the schema; use the inferred type |
| `import { db } from '../db'` inside a service | Inject the repository through the constructor |
| `res.status(404)` inside a service | Throw `NotFoundError`; the error handler sets the status |
| `catch (e) { console.log(e) }` | Handle, translate, or rethrow; log once at the edge |
| A hand-rolled DI container or generic repository "for later" | Composition root with `new`; generic code when a second case exists |
