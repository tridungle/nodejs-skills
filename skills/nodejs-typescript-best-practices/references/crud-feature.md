# New CRUD feature, end to end

Load when asked to add a resource (create, read, list, update, delete) to a Node.js service built on Express, Fastify, Hono or similar. Work through the steps in order; each ends with what must be true before moving on. Skip a step only when the user scoped it out, and say so in the summary.

The process around these steps (sizing, clarifying questions, plan, tests first, self-review, hand-off) is the `feature-workflow` skill when installed; this file is the build list it uses.

Before step 1, read one existing feature in the project and copy its conventions (folder layout, naming, framework, validator, ORM, error classes, test runner, module system). The project's way wins over this list wherever they differ.

## 1. Agree the contract

List the endpoints, request and response fields, status codes and error cases, following the project's existing API conventions (or the `api-design` skill when installed). Ask about anything that changes the data model: ownership, uniqueness, soft vs hard delete, which fields are editable.

**Done when** each endpoint has a method, path, success status, error statuses and the fields it accepts and returns.

## 2. Model, schemas and migration

Domain type, request schemas (create, update, list query, params) with the types inferred from them, and a response mapping function. If the schema changes, a migration through the project's tool, with indexes on filter, sort and owner columns. See [validation-config.md](validation-config.md).

**Done when** the migration applies cleanly, input schemas reject unknown keys and bound every string and array, and no server-owned field appears in an input schema.

## 3. Repository

An interface with intent-named methods and one implementation (the only file importing the ORM or driver), plus an in-memory implementation for tests if the project uses them. Lists are paginated with a capped limit; owner/tenant is a parameter of every user-scoped query; driver errors such as unique violations become domain errors. See [architecture.md](architecture.md).

**Done when** the service can be constructed with either implementation.

## 4. Service

Business rules: ownership checks, state transitions, side effects. Constructor-injected repository; throws domain errors from the shared error module, never touches `req`/`res` or status codes; owns transactions for multi-write operations. See [errors-async.md](errors-async.md).

**Done when** every rule from step 1 lives here and the service file imports nothing from the HTTP framework.

## 5. Controller and routes

One handler per endpoint: parse input with the schemas, take the user from the auth middleware's context, call one service method, map with the response function, set the status (201 + `Location` on create, 204 on delete). Errors propagate to the central error handler; on Express 4, make sure async errors reach it.

**Done when** no handler contains business conditions or database calls.

## 6. Wiring

Construct the repository and service in the composition root and pass them to the route factory or controller; register the routes in `buildApp`. No module-level singletons imported by the service.

**Done when** the app starts and the new routes respond.

## 7. Tests

- Service unit tests with the in-memory repository: happy path and every rejection branch.
- Repository integration test against the real database engine: pagination edges, owner scoping, unique-violation translation.
- HTTP tests through `buildApp`: each endpoint's success, invalid input, unauthenticated, another user's resource, not found.

See [testing.md](testing.md).

**Done when** the new tests pass and the existing suite still passes.

## 8. Docs and comments

OpenAPI entries for the new endpoints, including error responses, if the project maintains a spec. Doc comments on public service methods that throw domain errors or have side effects, matching the project's comment density.

**Done when** the spec (if any) lists every new endpoint with its errors.

## 9. Verify and report

Run the project's lint, type-check (`tsc --noEmit` or the project script) and test commands. Report: files added and changed, endpoints with their statuses, decisions made on the user's behalf (and any step skipped), and the exact commands run with their results.
