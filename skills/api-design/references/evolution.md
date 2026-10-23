# Versioning, idempotency, concurrency, rate limits, documentation

Load when changing a published contract, making writes safe to retry, or documenting the API.

## Breaking vs non-breaking

| Non-breaking (ship in place) | Breaking (needs a new version or a migration window) |
|---|---|
| Adding an endpoint | Removing or renaming an endpoint or field |
| Adding an optional request field | Making an optional field required; adding a required field |
| Adding a response field | Changing a field's type, format or meaning |
| Adding an enum value **if clients were told to tolerate unknown values** | Removing an enum value; adding one clients cannot handle |
| Relaxing validation | Tightening validation |
| New optional query parameter | Changing defaults (sort order, page size), status codes or the error `code` for a case |
| | Changing authentication or required scopes |

## Versioning

- Path versioning (`/v1/…`) is the most visible and cache-friendly; header or media-type versioning is acceptable when the project already uses it. One scheme per API.
- Bump the major version only for breaking changes; the version is not a release number.
- Keep at most two major versions live. Announce deprecation with the `Deprecation` and `Sunset` headers plus documentation, and give consumers a fixed window (commonly six months for public APIs; internal APIs follow their consumers' release cycle).
- Prefer evolving in place: add the new field, deprecate the old one, remove it in the next major version.
- Internal APIs with a single known consumer may skip versioning if both deploy together — state that assumption.

## Idempotency

- PUT and DELETE are idempotent by definition; make sure the implementation is.
- POSTs that create or charge accept an `Idempotency-Key` header (client-generated UUID). The server stores key + request fingerprint + response for a retention window (e.g. 24h):
  - same key, same request → replay the stored response;
  - same key, different request → 422 (or 409);
  - same key while the first is still running → 409.
- Webhook and message consumers dedupe by event id for the same reason.

## Concurrency

- Return an `ETag` (or a `version` field) on resources that are edited concurrently.
- Updates send `If-Match`; a stale value gets 412. Without this, two editors silently overwrite each other.
- Conditional GET (`If-None-Match` → 304) for large, frequently polled resources.

## Long-running operations

Return 202 with `Location: /operations/{id}`; the operation resource reports `status` (`pending`, `running`, `succeeded`, `failed`) and, when done, the result or a link to it. Clients poll with backoff or receive a webhook.

## Rate limiting

- Limit per credential (API key, user), with a looser per-IP limit for anonymous traffic and tighter limits on authentication, password reset and other enumeration-prone routes.
- Communicate limits: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (or the `X-RateLimit-*` forms if already used); 429 with `Retry-After` when exceeded.
- Pick numbers from measured capacity and per-tier agreements, not from a template, and document them.

## Webhooks (if the API emits them)

- Sign every payload (HMAC over the raw body with a per-subscriber secret, timestamp included to block replays).
- Retry with exponential backoff; include a unique event id so receivers can dedupe.
- Payload carries the event type, id, timestamp and either the resource or a link to fetch it.

## Documentation

The OpenAPI document is how a contract change becomes reviewable. Writing it, generating it per framework, and keeping it in step with the code are covered in [api-docs.md](api-docs.md).
