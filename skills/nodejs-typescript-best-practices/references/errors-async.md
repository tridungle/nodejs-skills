# Errors and async

Load when adding error handling, writing the error middleware, or chasing lost errors, hangs and unhandled rejections.

## Operational vs programmer errors

- **Operational** — expected failures: invalid input, missing record, conflict, timeout from a dependency. Model them as domain errors, handle, return a clean response.
- **Programmer** — bugs: `undefined` access, broken invariant. Let them reach the top-level handler, log with stack, return a generic 500. At process level, exit and let the supervisor restart rather than run on corrupted state.

## Domain error classes

One small file (`shared/errors.ts`):

- `AppError extends Error` with a stable `code` string, safe `message`, optional `details`, and `cause` passthrough (`super(message, { cause })`).
- Subclasses only for cases a caller branches on: `ValidationError`, `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`.
- Set `this.name = new.target.name` so logs show the subclass.
- Services and repositories throw these. They never know status codes.
- Repositories translate driver errors (unique violation → `ConflictError`) because only they know driver codes.

A `Result<T, E>` return type is a valid alternative for expected failures in a codebase that already uses it; do not mix both styles in one feature, and do not add a Result library unasked.

## The single error handler

At the edge (Express error middleware with four parameters, Fastify `setErrorHandler`, Hono `onError`):

1. `AppError` → status from its class (400/422 validation, 401, 403, 404, 409), body `{ error: { code, message, details? } }`.
2. Schema-validation failure from the boundary → 400 or 422 (one choice project-wide) with field-level `details`.
3. Anything else → 500, `code: "internal_error"`, generic message.
4. Log once here, with request id, route, error name and stack. Response bodies never carry stacks, SQL or paths.

If the `api-design` skill defines the envelope, use that envelope.

## Async rules

- Every promise is `await`ed, returned, or given a `.catch` that handles it. `void promise` only with a comment saying where its errors go.
- Express 4 does not route rejected promises to error middleware: wrap handlers in a small `asyncHandler` or keep the project's existing solution. Express 5, Fastify, Hono and Koa do.
- Independent awaits run in parallel with `Promise.all`; use `Promise.allSettled` when partial failure is acceptable and each result is inspected.
- `array.forEach(async …)` never waits — use `for…of` with `await` (sequential) or `Promise.all(array.map(…))` (parallel, bounded if the array is large).
- Every outbound call has a timeout (`AbortSignal.timeout(ms)` with `fetch`, the client's own option otherwise). A missing timeout turns a slow dependency into exhausted sockets.
- Retries only for idempotent or idempotency-keyed operations, with capped exponential backoff and jitter, honouring `Retry-After`.
- Event emitters and streams: attach `'error'` listeners; use `stream/promises` `pipeline` so errors and cleanup propagate.

## Process-level handlers

In the composition root only:

- `process.on('unhandledRejection', …)` and `process.on('uncaughtException', …)`: log fatal with the error, start graceful shutdown, exit non-zero. Never swallow and continue.
- `SIGTERM`/`SIGINT`: graceful shutdown (see [production.md](production.md)).

## Checks

- Search for `catch` blocks with no rethrow, no returned error value and no compensating action.
- Search services for `res.`, `status(`, `reply.code(` — layer leaks.
- Search for `.forEach(async` and un-awaited calls to async functions (type-aware lint does this best).
- Search outbound `fetch`/HTTP client calls for a timeout.
- Force a 500 in a test; assert the body has no stack and the log has one.
