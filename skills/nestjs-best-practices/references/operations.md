# Operations and performance

Load when adding caching, health checks, logging, background jobs, or diagnosing a slow or unstable service. Packages named here apply only when installed or approved.

## Bootstrap (`main.ts`)

- Keep it short: create the app, call one shared `configureApp(app)` (global prefix, versioning, pipes, CORS, body limits), `enableShutdownHooks()`, `listen` on the port from config.
- Fastify adapter is faster than Express for high-throughput JSON APIs; switching is a decision for the user, not a drive-by change — middleware and some packages differ.

## Graceful shutdown

- `app.enableShutdownHooks()`; close pools, consumers and clients in `onModuleDestroy` / `beforeApplicationShutdown`.
- On SIGTERM: stop accepting connections, let in-flight requests finish within a deadline shorter than the orchestrator's kill timeout, then exit.
- Readiness turns unhealthy at shutdown start so the load balancer drains traffic first.

## Health checks

- `@nestjs/terminus` when installed: liveness (process is up, no dependencies checked) and readiness (database, cache, required downstreams) as separate endpoints.
- Liveness must not check the database, or a database blip restarts every pod at once.

## Logging

- One structured logger (the project's: `nestjs-pino`, `winston`, or Nest's `Logger` with a JSON format). JSON in production, readable in development.
- Each line carries a request/correlation id (middleware sets it, AsyncLocalStorage carries it).
- Levels: `error` needs action, `warn` degraded but handled, `info` lifecycle and business events, `debug` off in production.
- Never log secrets, tokens, full bodies or personal data; redact by field name in the logger config.
- Replace `console.log` with the logger in application code.

## Caching

- Cache in the **service** (it knows what is safe to cache and when it changes) or via `CacheInterceptor` for whole GET responses that are identical for every caller.
- Every cache entry has a TTL; every write path that changes the data invalidates or updates the key.
- Per-user data never goes in a response cache keyed only by URL.
- Multiple replicas need a shared store (Redis); an in-memory cache per pod is a correctness risk for anything invalidated on write.

## Background work

- Anything slow or retryable (emails, webhooks, report generation, image processing) leaves the request path: a queue (`@nestjs/bullmq` if installed) with a processor class that calls a service.
- Processors are thin controllers: parse the job, call the service, let failures throw so the queue retries with backoff. Jobs are idempotent because they will run twice.
- Scheduled tasks (`@nestjs/schedule`) on multiple replicas run on every replica unless guarded by a lock or moved to a single worker.

## Performance

- Measure before changing: response time percentiles per route, query count and duration per request, event-loop lag.
- Usual causes in order: N+1 queries and missing indexes ([data-access.md](data-access.md)), serial `await`s that could be `Promise.all`, large payloads without pagination, synchronous CPU work (hashing, JSON of huge objects, regex on large input) blocking the event loop — move CPU-heavy work to a worker thread or a job.
- `REQUEST`-scoped providers multiply instantiation per request; check scopes before micro-optimising.
- Enable compression at the proxy rather than in the app where possible.

## Configuration

- `@nestjs/config` with `isGlobal: true` and a `validate` function (Zod, Joi or `class-validator`, whichever the project uses); typed access through a config namespace or a typed wrapper, not stringly `get('DB_URL')` scattered around.
- Different behaviour per environment comes from config values, never from `if (NODE_ENV === 'production')` inside services.
