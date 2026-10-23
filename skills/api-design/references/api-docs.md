# API documentation (OpenAPI)

Load when writing, generating, reviewing or fixing the documentation of an HTTP API.

The OpenAPI 3.x document is the contract: the artifact reviewers diff, clients generate code from, and tests check the implementation against. Prose guides sit on top of it; they never replace it.

## Spec-first or code-first

Follow what the project does. When it does neither yet:

| | Spec-first (write the YAML, implement to it) | Code-first (generate from routes and schemas) |
|---|---|---|
| Fits | Public or partner APIs, several client teams, contract agreed before code | Internal APIs, one team owns client and server |
| Strength | Contract reviewed before any code exists | Cannot drift from the code's types |
| Weakness | Drifts unless tests check the implementation against it | Docs only as good as the annotations; easy to omit error responses |

Either way, the document is committed or generated in CI so a pull request shows the contract change.

## Generating from code, per framework

Use what is installed; ask before adding any of these.

| Framework | Source of the document |
|---|---|
| NestJS | `@nestjs/swagger` with the CLI plugin in `nest-cli.json`, so DTO types become schemas without an `@ApiProperty()` on every field |
| Fastify | `@fastify/swagger` reads the JSON schemas already on each route; no second source of truth |
| Hono | `@hono/zod-openapi` routes declare request and response Zod schemas once |
| Express | No built-in source: a hand-written spec file validated in tests, or the project's existing Zod-to-OpenAPI generator |

Request and response schemas come from the same definitions that validate at runtime. A schema written twice, once for validation and once for docs, will disagree.

## What every operation documents

- `operationId`: unique, stable, camelCase verb + noun (`listOrders`, `cancelOrder`). Generated clients use it as the method name, so renaming it breaks clients.
- `summary` (one line) and, when behaviour is not obvious, a `description`: side effects, preconditions, async behaviour.
- `tags`: one per resource, so the docs group by resource.
- Parameters: type, format, constraints (`minimum`, `maximum`, `maxLength`, `enum`), default, and whether required.
- Request body schema, with `required` listed and unknown properties disallowed when the server rejects them.
- **Every response it can return**: the success code with its schema, and each error status (400/422, 401, 403, 404, 409, 429, 500 as applicable) referencing the shared error schema. A doc that lists only 200 hides most of the contract.
- Security requirement, or an explicit empty one for public routes.
- Pagination parameters and the page metadata schema on list operations.

## Components and reuse

- Shared schemas under `components/schemas`: the error envelope, page metadata, each resource. Reference them with `$ref`; never inline copies.
- Shared parameters (`limit`, `cursor`, `Idempotency-Key`) and responses (`NotFound`, `ValidationFailed`) under `components`.
- `securitySchemes` defined once (bearer JWT, API key) and applied globally, with per-operation overrides only for exceptions.
- Request and response variants of a resource are separate schemas (`OrderCreate`, `Order`) when they differ. Read-only server fields are marked `readOnly` or absent from the input schema.

## Descriptions and examples

- Field descriptions state meaning, units and format that the type cannot show: `amount in minor units (cents)`, `ISO-8601 UTC timestamp`, `opaque cursor from page.nextCursor`.
- Do not restate the name: "The order id" on `orderId` adds nothing.
- Give one example per operation request and response, and one per distinct error, using invented placeholder data. Never real customer data, tokens or internal hostnames.
- Mark deprecated operations and fields `deprecated: true`, say in the description what replaces them, and give the removal date.

## Keeping docs true

- A test validates real responses against the document (a response-schema validator in the HTTP test suite, or a contract-testing tool the project already uses). Docs no test checks will drift.
- CI compares the document with the base branch and flags breaking changes (see [evolution.md](evolution.md)). Suggest this if it is missing; do not add tooling unasked.
- The served docs UI (Swagger UI, Redoc, Scalar) is behind auth or disabled in production unless the API is public by design.
- `info.version` follows the API's release, not the package version of the server.

## Review checklist

- [ ] Every operation has a unique `operationId`, a summary and a tag
- [ ] Every operation lists its error responses with the shared error schema
- [ ] Constraints in the document match runtime validation (spot-check three fields)
- [ ] No inline duplicate of a schema that exists in `components`
- [ ] Examples are invented placeholders; no secrets or real data
- [ ] A test or CI step fails when the implementation and the document disagree
