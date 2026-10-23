---
name: api-design
description: "Designs and reviews HTTP/REST API contracts and their OpenAPI documentation: resource URLs, methods, status codes, one error envelope, pagination, filtering, versioning, idempotency, rate limits. Use when shaping, documenting or reviewing endpoints as a contract, apart from the framework code."
license: MIT
metadata:
  tags: ["api", "rest", "http", "openapi", "contract"]
---

# API Design

Decide the contract a client sees — URLs, methods, status codes, bodies, errors, paging, versions — so it is consistent across every endpoint and can evolve without breaking callers. Implementation in a framework belongs to `nestjs-best-practices` or `nodejs-typescript-best-practices`.

## Cost rules

- **Follow the existing API first.** If the service already has a convention (snake_case vs camelCase, envelope shape, 400 vs 422), new endpoints match it; list deviations instead of rewriting them.
- **Answer the question asked.** A single-endpoint question gets a decision and its reason, not a full style guide.
- **Open a reference only when the task reaches it**: [pagination-filtering.md](references/pagination-filtering.md) for list endpoints, [evolution.md](references/evolution.md) for versioning, idempotency and rate limits, [api-docs.md](references/api-docs.md) for writing or generating OpenAPI documentation.

## Resources and URLs

- Nouns, plural, lowercase, kebab-case: `/orders`, `/team-members`, `/orders/{orderId}`.
- Nest at most one level to express ownership: `/customers/{id}/orders`. Deeper paths become top-level resources with a filter: `/order-items?orderId=…`.
- No verbs for CRUD. A state change that is not CRUD is a sub-resource action: `POST /orders/{id}/cancel`.
- Identifiers are opaque strings (UUID/ULID) — never expose sequential database ids for user-owned data.
- One field-naming case across the whole API (camelCase for JS clients is common; follow what exists).
- Prefix with a version only if the API is versioned in the path (`/v1/…`); see [evolution.md](references/evolution.md).

## Methods

| Method | Use | Safe | Idempotent | Typical success |
|---|---|---|---|---|
| GET | Read | yes | yes | 200 |
| POST | Create, or run an action | no | no (make it so with `Idempotency-Key`) | 201 + `Location`, or 200/202 for actions |
| PUT | Replace whole resource | no | yes | 200 or 204 |
| PATCH | Partial update | no | no by default | 200 with the updated resource |
| DELETE | Remove | no | yes | 204 (repeat delete: 204 or 404, choose once) |

GET never changes state. No request body on GET or DELETE.

## Status codes

| Code | When |
|---|---|
| 200 | Success with body |
| 201 | Created; include `Location` header and the resource |
| 202 | Accepted for async processing; return a status resource URL |
| 204 | Success without body |
| 400 | Malformed request: unparsable JSON, wrong types, failed schema |
| 401 | No or invalid credentials |
| 403 | Authenticated but not allowed (use 404 when existence itself is secret) |
| 404 | Resource does not exist or is not visible to this caller |
| 409 | Conflict: duplicate, version mismatch, invalid state transition |
| 412 | `If-Match` precondition failed (optimistic concurrency) |
| 415 | Unsupported `Content-Type` |
| 422 | Well-formed but violates a business rule |
| 429 | Rate limited; include `Retry-After` |
| 500 | Unexpected server failure; generic message |
| 502 / 503 / 504 | Upstream failure / temporarily unavailable / upstream timeout |

Pick **one** rule for 400 vs 422 and write it down. A common split: schema failures → 400, business-rule failures → 422. Never 200 with `success: false`.

## Error envelope

One shape for every error from every endpoint:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request validation failed",
    "details": [{ "field": "items[0].quantity", "code": "too_small", "message": "Must be at least 1" }],
    "requestId": "<request id>"
  }
}
```

- `code` is stable snake_case and documented; clients branch on it. `message` is human-readable and may change.
- `details` only for field-level problems; field paths use the same naming as the request body.
- No stack traces, SQL, internal hostnames or exception class names.
- If the project or its consumers use RFC 9457 Problem Details (`application/problem+json`), use that instead — same rules, different field names.

## Bodies

- JSON with `Content-Type: application/json`; reject others with 415.
- Return the resource object directly for single reads; wrap collections: `{ "data": [...], "page": {...} }` so metadata can be added without a breaking change.
- Timestamps ISO-8601 in UTC (`2026-01-31T12:00:00Z`); money as integer minor units plus a currency code, or a decimal string — never a float.
- `null` vs absent: decide once. Common: absent means "not applicable", `null` means "known to be empty".
- Enums are strings, documented, and clients must tolerate new values.
- No server-owned fields accepted in input (`id`, `createdAt`, `ownerId`).

## Security in the contract

- Authenticate with `Authorization: Bearer <token>`; no credentials in query strings (they land in logs).
- Every resource read checks ownership; listing endpoints are scoped to the caller by default.
- Bound everything a client controls: page size, body size, string lengths, array sizes, filter count.

## Review checklist

Report each as pass or fail with the endpoint that proves it.

- [ ] URLs are plural nouns, kebab-case, at most one nesting level, no CRUD verbs
- [ ] Methods match semantics; GET is side-effect free
- [ ] Creation returns 201 with `Location`; deletes return 204
- [ ] One error envelope everywhere; one documented 400 vs 422 rule; no 200-with-error
- [ ] Every list endpoint paginated with a maximum page size
- [ ] Field naming case consistent across all endpoints
- [ ] Retryable `POST`s accept `Idempotency-Key`
- [ ] Breaking changes identified and versioned (see [evolution.md](references/evolution.md))
- [ ] Contract documented in OpenAPI (or the project's equivalent) and matches the implementation (see [api-docs.md](references/api-docs.md))

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| `POST /getOrders`, `GET /deleteOrder?id=` | `GET /orders`, `DELETE /orders/{id}` |
| `200 { "success": false }` | Correct 4xx/5xx with the error envelope |
| Bare array response for a list | `{ "data": [...], "page": {...} }` |
| Different error shapes per endpoint | One envelope, one set of codes |
| Exposing auto-increment ids | Opaque ids |
| Renaming a field in place | Add the new field, deprecate the old, remove in the next version |
