# Testing

Load when writing or reviewing tests. Use the project's runner (Vitest, Jest, or `node:test`); with none, ask before adding one — `node:test` needs no install.

## Layer by layer

| Layer | Test | Real | Faked |
|---|---|---|---|
| Service | Unit | Service | Repositories and other services, injected through the constructor |
| Repository | Integration | Repository + the production database engine (container or disposable schema) | Nothing |
| Controller + error handler | HTTP | `buildApp(fakeDeps)` driven by `supertest`, Fastify `inject`, or Hono `app.request` | Services, or services with in-memory repositories |
| Whole system | A few end-to-end smoke tests | Everything | Third-party services |

Constructor injection is what makes this cheap: a service test is `new OrderService(new InMemoryOrderRepository())`, no module mocking.

## Service tests

- Prefer an in-memory repository implementing the interface over per-test mocks; it is reused across tests and catches misuse a mock would accept.
- Assert outcomes: returned value, thrown error class and `code`, resulting repository state. Assert calls only when the call is the behaviour (an event published, an email requested).
- One test per business rule branch and boundary value.
- Inject time and randomness (a `clock` and `idGenerator` dependency) where outcomes depend on them, rather than mocking globals.

## Repository tests

- Same engine as production; SQLite does not stand in for Postgres.
- Run migrations in setup; isolate tests by transaction rollback or truncation.
- Cover filters, ordering, pagination edges, owner scoping and driver-error translation (`ConflictError` on duplicates).

## HTTP tests

- Build the app through the same `buildApp` used in production, so middleware, validation and the error handler are the real ones.
- Per endpoint: success status and body, invalid input → 400/422 with field details, unauthenticated → 401, another user's resource → 404/403, and one forced 500 asserting no stack or internals in the body.
- Do not bind a port when the framework can inject requests (`fastify.inject`, `app.request`); `supertest` accepts the app object directly.

## Module mocking

`vi.mock`/`jest.mock` of internal modules is a sign the code imports singletons instead of receiving dependencies. Acceptable for third-party modules at the edge; for internal code, refactor to injection when touching it.

## Hygiene

- No real network; block it in the test setup if the runner allows.
- Fake timers instead of sleeps.
- Test data factories with overridable defaults.
- A bug fix ships with the test that failed before the fix.
- Tests run in parallel safely: unique ids, no shared mutable module state.
