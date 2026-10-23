# Validation and configuration

Load when validating request input, external data or environment variables.

## Where validation happens

Every place data crosses into the process is a boundary: HTTP body, query, params and headers; environment variables; queue and webhook payloads; responses from third-party APIs; files read from disk. Each gets a schema check before the data reaches a service.

Use the project's validator. When it has none, ask before adding one; Zod is the common choice, Valibot is smaller, TypeBox pairs with Fastify's JSON-schema validation, and Fastify's built-in schema validation needs no extra package at all.

## Request validation rules

- One schema per operation (`CreateOrderBody`, `ListOrdersQuery`, `OrderParams`), next to the model; the TypeScript type is inferred from it.
- **Strip or reject unknown keys** (`.strict()` to reject, the default strips in Zod; `additionalProperties: false` in JSON schema). Never pass a raw body into a database write.
- Bound everything: string `max`, array `max`, number `min`/`max`. Set a body size limit on the framework.
- Query and path params are strings: coerce explicitly (`z.coerce.number().int().min(1).max(100)`), and parse booleans from `'true'`/`'false'` explicitly — `Boolean('false')` is `true`.
- Defaults (page size, sort) live in the schema so the service never handles `undefined`.
- Server-owned fields (`id`, `ownerId`, `role`, timestamps) are not in input schemas; the owner comes from the authenticated principal.
- Sort and filter fields are enums, not free strings, before they reach a query.
- Validation failures become one error type that the error handler turns into 400/422 with field-level `details` (`path` → `field`).

Validation of shape lives at the edge; validation of business rules ("cannot cancel a shipped order") lives in the service and throws a domain error.

## External data

Responses from other services are untrusted: parse them with a schema too (often `.passthrough()` or a partial schema covering only the fields used), so a changed upstream field fails loudly at the boundary instead of as `undefined` three layers later.

## Configuration

- One `config.ts` reads `process.env` once, validates with a schema, and exports a typed, frozen object. Nothing else reads `process.env`.
- Validation runs at import/boot time: a missing or malformed variable stops the process with a message naming the variable (never its value).
- Coerce types in the schema (`PORT` → number, `FEATURE_X` → boolean with explicit parsing); give defaults only for values that are safe to default (port, log level), never for secrets or database URLs.
- `.env` loading for local development: Node's `--env-file` flag (current versions) or the project's existing `dotenv`; never commit `.env`, commit `.env.example` with placeholders.
- Secrets never appear in logs, error messages or responses; redact by key name in the logger.
- Behaviour that differs by environment is a config value (`config.emailEnabled`), not `if (process.env.NODE_ENV === 'production')` inside services.

## Checks

- Search for `req.body`, `req.query`, `c.req.json()`, `request.body` reaching a service without passing through a schema parse.
- Search for `as` casts on request data.
- Search for `process.env` outside the config module.
- Start the app with a required variable unset; it must refuse to boot.
