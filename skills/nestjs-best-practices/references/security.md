# Security

Load when adding authentication or authorization, exposing a new endpoint, or reviewing a module for security. Packages named here apply only when installed or approved by the user.

## Authentication

- A global guard (`APP_GUARD`) authenticates every route; public routes opt out with a `@Public()` metadata decorator read via `Reflector`. Deny by default, allow by exception.
- JWT: verify signature **and** `exp`, `iss`, `aud`; pin the algorithm list; access tokens short-lived (minutes), refresh tokens rotated and revocable. Secrets or keys come from config, at least 256 bits for HMAC.
- Put the authenticated principal on the request in the guard and read it with a `@CurrentUser()` param decorator. Services receive the user as an argument; they never read the request.
- Passwords: `argon2` or `bcrypt` (cost ≥ 12), whichever the project has. Never a fast hash.

## Authorization

- Role checks: a `RolesGuard` reading `@Roles(...)` metadata — coarse gate only.
- **Ownership checks belong in the service**, because only the service loads the resource: "order belongs to this customer or the caller is support". A guard cannot see the row.
- Return 404 rather than 403 for resources the caller must not know exist.
- Every query for user-owned data filters by owner/tenant in the repository method signature (`findByIdForOwner(id, ownerId)`), so forgetting the filter is a compile error, not a data leak.

## Input

- Global `ValidationPipe` with `whitelist` + `forbidNonWhitelisted` stops mass assignment (`role`, `isAdmin` in a body). See [validation-dtos.md](validation-dtos.md).
- Bound body size (`app.useBodyParser('json', { limit: '100kb' })` or the platform equivalent), string lengths and array sizes.
- Raw SQL only with parameters; never interpolate input into a query, a sort column or a table name — allow-list those.
- File uploads: limit size and count in the interceptor options, check type by content not extension, store outside the web root with generated names.

## Output

- Response DTOs list fields explicitly; no entity serialization (password hashes, tokens, internal flags).
- The exception filter returns generic 500 bodies; stacks and driver messages go to logs only. See [errors.md](errors.md).

## Transport and headers

- `helmet` (Express) or `@fastify/helmet` for security headers when installed.
- CORS: an explicit origin allow-list from config; never `origin: true` with `credentials: true`.
- Behind a proxy, set `trust proxy` correctly so client IPs used for rate limits and logs are real.

## Rate limiting

- `@nestjs/throttler` as a global guard when installed; tighter limits on login, password reset, OTP and other enumeration-prone routes (`@Throttle()` per route).
- Multiple replicas need a shared store (Redis) or limits are per instance.
- Return 429 with `Retry-After`.

## Secrets and config

- Validated config at boot; the app refuses to start with a missing or malformed secret.
- No secrets in source, in committed `.env` files, in logs or in error bodies. Commit an `.env.example` with placeholder values only.
- Redact `authorization`, `cookie`, `password`, `token` fields in the request logger.

## Checks

- List routes that have neither a global guard path nor `@Public()` — each needs a decision.
- Search service methods that load a resource by id without an owner or tenant argument.
- Search for `$queryRawUnsafe`, `query(` with template literals, `.raw(` with interpolation.
- Search CORS config for `origin: '*'` or `origin: true`.
