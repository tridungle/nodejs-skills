# Production readiness

Load when preparing a service to run in production, adding logging or health checks, or diagnosing performance. Packages named here apply only when installed or approved.

## Graceful shutdown

On `SIGTERM` and `SIGINT`, in the composition root:

1. Mark readiness unhealthy so the load balancer stops sending traffic.
2. `server.close()` — stop accepting connections; let in-flight requests finish (`server.closeIdleConnections()` on current Node for keep-alive sockets).
3. Stop consumers and schedulers; wait for running jobs up to a deadline.
4. Close database pools, cache and queue clients.
5. Exit 0. A hard timer (shorter than the orchestrator's kill timeout, e.g. 10–25s) forces exit 1 if the steps hang.

Register the handlers once; a second signal during shutdown forces exit.

## Health endpoints

- **Liveness** (`/healthz`): the process answers. Checks nothing external — otherwise a database blip restarts every instance.
- **Readiness** (`/readyz`): dependencies reachable (database ping, required caches). Fails during startup and shutdown.
- Neither requires authentication; neither returns internal details.

## Logging

- A structured JSON logger (the project's: `pino`, `winston`, …). `pino` is the fast default if the user approves adding one; never `console.log` in application code.
- Each request gets an id (from an incoming header such as `x-request-id` or generated), carried through async calls with `AsyncLocalStorage` and attached to every log line and to error responses.
- Levels: `error` needs action, `warn` handled degradation, `info` lifecycle and business events, `debug` off in production.
- Redact by key: `authorization`, `cookie`, `password`, `token`, `secret`, personal data fields.
- Log errors once, at the error handler, with stack.

## Security baseline

- Security headers (`helmet` / `@fastify/helmet` / Hono `secureHeaders`), CORS with an explicit origin allow-list.
- Body size limits; timeouts on the server (`requestTimeout`, `headersTimeout`) and on every outbound call.
- Rate limits on authentication and other enumeration-prone routes; a shared store when running more than one instance.
- Parameterised queries only; allow-listed sort/filter fields.
- Run as a non-root user; `NODE_ENV=production`; dependencies installed with the lockfile (`npm ci` or the equivalent).
- Ownership checks in services: a query for user-owned data takes the owner id as a parameter.

## Performance

- Measure first: latency percentiles per route, database time per request, event-loop delay (`perf_hooks.monitorEventLoopDelay`).
- Usual causes in order: N+1 queries and missing indexes; sequential `await`s that could be parallel; unpaginated lists and oversized payloads; synchronous CPU work on the main thread (large `JSON.stringify`, crypto hashing, image work, catastrophic regex) — move it to `worker_threads` or a job queue.
- Never use `*Sync` filesystem or crypto APIs in request paths.
- Stream large responses and uploads instead of buffering them; use `stream/promises` `pipeline`.
- Reuse HTTP connections to upstreams (keep-alive is the default for `fetch` in current Node; check custom agents).
- Cache in the service with a TTL and explicit invalidation on writes; a shared cache when there is more than one instance.

## Runtime

- Pin the Node version (`engines`, `.nvmrc` or the container base image) to an active LTS line.
- Run compiled JavaScript or a type-stripping-safe build with `--enable-source-maps`; type-check in CI with `tsc --noEmit`.
- One process per container; scale with replicas rather than the `cluster` module unless the platform lacks orchestration.
