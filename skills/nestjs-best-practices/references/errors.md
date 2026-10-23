# Errors

Load when adding error handling, writing the global exception filter, or reviewing how failures reach clients.

## Principle

Lower layers say **what** went wrong in domain terms; exactly one place decides **how** that looks on the wire. A service that throws `NotFoundException` has decided an HTTP status; the same service called from a queue consumer or a CLI now speaks HTTP for no reason.

If the project already throws Nest's built-in exceptions from services consistently, do not rewrite them all; apply this pattern to new code and flag the mix once.

## Domain error hierarchy

A small set in `common/errors/`, extended only when a caller needs to branch on a new case:

| Class | Meaning | Maps to |
|---|---|---|
| `DomainError` (abstract base) | Carries `code` (stable machine string) and safe `message` | — |
| `ValidationError` | Input passes shape checks but breaks a business rule | 422 (or 400 — pick one project-wide) |
| `NotFoundError` | Resource absent or not visible to this caller | 404 |
| `ConflictError` | Duplicate, version mismatch, invalid state transition | 409 |
| `ForbiddenError` | Authenticated but not allowed | 403 |
| `UnauthorizedError` | Missing or invalid credentials | 401 |
| anything else | Programmer error or infrastructure failure | 500, generic message |

Rules:

- Set `this.name` and keep `code` stable — clients switch on it; the message may change.
- Wrap infrastructure errors with `cause` (`new ConflictError('...', { cause: err })`) when translating, e.g. a unique-constraint violation becomes `ConflictError` **in the repository**, because only the repository knows the ORM's error codes.
- Never put secrets, SQL, file paths or stack traces in `message`.

## Global filter

One `@Catch()` filter registered as `APP_FILTER`:

1. If the exception is a `DomainError` → status from the table above, body `{ error: { code, message, details? } }`.
2. If it is an `HttpException` (thrown by Nest itself: `ValidationPipe`, guards, `ParseUUIDPipe`, unknown route) → keep its status, normalise the body into the same envelope; for validation, turn the message array into `details: [{ field, message }]`.
3. Anything else → 500, `code: "internal_error"`, generic message; log the full error with stack.
4. Always include the request id (from a header or generated in middleware) in the log entry and in the body or a response header.

Log **once, here**. Services do not log-and-rethrow; that doubles every entry.

The envelope and status mapping should match the API contract; when the `api-design` skill is installed, its envelope wins over the one above.

## Controllers

- No `try/catch` in controllers whose only job is to convert an error into a response — that is the filter's job.
- A `try/catch` in a service is legitimate when it **does** something: compensates, retries a transient failure, translates to a domain error, or adds context and rethrows.
- Never an empty `catch`, never `catch (e) { return null }` that turns a database outage into "not found".

## Async and process-level

- Every promise is awaited or explicitly handled; enable `@typescript-eslint/no-floating-promises` if ESLint is present.
- Fire-and-forget work (sending an email after the response) goes to a queue or an event handler that catches and logs its own errors.
- `app.enableShutdownHooks()` in `main.ts`; process-level `unhandledRejection` should log and exit, not continue on corrupted state.

## Non-HTTP contexts

Microservice (`@MessagePattern`) and WebSocket handlers need their own filter (`RpcException` / `WsException` mapping); the HTTP filter does not run there. Same domain errors, different mapping.

## Checks

- Search services and repositories for `HttpException`, `NotFoundException`, `BadRequestException`, `HttpStatus` — each hit is a layer leak (or the project's deliberate convention).
- Search for `catch (` followed by a body with no `throw`, no return of an error value, and no compensating action.
- Search for `console.error` / `logger.error` immediately followed by `throw` in the same catch — double logging.
- Trigger a 500 in a test and assert the body contains no stack, SQL or internal message.
