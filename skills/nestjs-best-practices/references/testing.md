# Testing

Load when writing or reviewing tests for a NestJS feature. Use the project's runner (Jest is Nest's default; Vitest with SWC is common) and its existing file naming.

## What to test at which layer

| Layer | Test type | Real | Faked |
|---|---|---|---|
| Service | Unit | The service | Its repositories and other injected services |
| Repository | Integration | Repository + real database (container or test schema) | Nothing below it |
| Controller | Usually covered by e2e; unit-test only when it has mapping logic worth isolating | Controller | Service |
| Whole route | E2E | `AppModule` (or the feature module + infrastructure) over HTTP with `supertest` | External services (payments, email) |

Most behaviour lives in services, so most tests are service unit tests. They need no database and run in milliseconds.

## Service unit tests

- Build with `Test.createTestingModule({ providers: [OrdersService, { provide: OrdersRepository, useValue: fakeRepo }] }).compile()`, or simply `new OrdersService(fakeRepo)` — constructor injection makes the container optional for unit tests.
- A fake repository is a small in-memory object implementing the abstract class; prefer it over a mock with dozens of `mockResolvedValue` lines when several tests share setup.
- Assert outcomes (returned value, thrown domain error class and `code`, what was persisted), not which internal methods were called — unless the call is the behaviour (an event was emitted, an email requested).
- Cover each business rule: the happy path, each rejection branch, and boundary values.

## Repository integration tests

- Run against the same database engine as production (Testcontainers, or a disposable schema), not SQLite standing in for Postgres.
- Apply migrations, not `synchronize`, so the test also proves the migrations.
- Isolate tests by truncating tables or wrapping each test in a rolled-back transaction.
- Test what the ORM can get wrong: filters, ordering, pagination edges, unique-constraint translation to `ConflictError`, owner scoping.

## E2E tests

- Build the app from `AppModule` with `Test.createTestingModule({ imports: [AppModule] })`, override external providers with `.overrideProvider(X).useValue(fake)`, then `createNestApplication()` and `init()`.
- Apply the same global setup as `main.ts` (pipes, filters, prefix, versioning) — put it in one shared `configureApp(app)` function used by both, or the e2e suite tests a different app.
- Assert status code **and** body shape for: success, validation failure (400/422 with field details), unauthenticated (401), forbidden/not-found for another user's resource, and one 500 path proving no internals leak.
- Close the app in `afterAll` so handles do not leak between files.

## Guards, pipes, filters, interceptors

Unit-test them directly with a hand-built `ExecutionContext`/`ArgumentsHost` stub when they contain logic (role matching, error mapping). The e2e suite covers their wiring.

## Hygiene

- No real network calls; no shared mutable state between tests; no `sleep` — use fake timers.
- Factories for test data with overridable defaults, not copied object literals.
- A bug fix lands with the test that failed before it.
- Coverage is a floor to spot untested files, not a target; a branch in a service with no test is a finding regardless of the percentage.
