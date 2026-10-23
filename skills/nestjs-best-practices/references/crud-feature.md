# New CRUD feature, end to end

Load when asked to add a resource (create, read, list, update, delete) to a NestJS app. Work through the steps in order; each ends with what must be true before moving on. Skip a step only when the user scoped it out, and say so in the summary.

The process around these steps (sizing, clarifying questions, plan, tests first, self-review, hand-off) is the `feature-workflow` skill when installed; this file is the build list it uses.

Before step 1, read one existing feature module in the project and copy its conventions (folder layout, naming, ORM, validator, error style, test runner). The project's way wins over this list wherever they differ.

## 1. Agree the contract

List the endpoints, request and response fields, status codes and error cases, following the project's existing API conventions (or the `api-design` skill when installed). Ask about anything that changes the data model: ownership, uniqueness, soft vs hard delete, which fields are editable.

**Done when** each endpoint has a method, path, success status, error statuses and the fields it accepts and returns.

## 2. Model and migration

Entity/model and, if the schema changes, a migration through the project's tool. Index every column used to filter, sort or look up by owner. Add unique constraints the rules require.

**Done when** the migration applies and rolls back cleanly on a local database, and the model has no HTTP or validation decorators beyond what the ORM requires.

## 3. Repository

Abstract class with intent-named methods (`findById`, `findPageForOwner`, `create`, `update`, `delete`), and one implementation using the ORM. Lists are paginated with a capped limit; owner/tenant is a parameter of every user-scoped query; driver errors such as unique violations become domain errors. See [data-access.md](data-access.md).

**Done when** only the implementation imports the ORM, and the integration test (step 7) can target it.

## 4. Service

Business rules: ownership checks, allowed state transitions, uniqueness beyond the database, side effects (events, cache invalidation). Throws domain errors (`NotFoundError`, `ConflictError`, `ForbiddenError`), never `HttpException`. Multi-write operations own their transaction. See [errors.md](errors.md).

**Done when** every rule from step 1 lives here, and the service imports neither the ORM nor anything from `@nestjs/common` except `Injectable`.

## 5. DTOs

`CreateXDto`, `UpdateXDto` (via `PartialType`), `ListXQueryDto` (limit, cursor or page, allow-listed sort and filters), `XResponseDto` with an explicit mapping from the model. No server-owned fields in input DTOs. See [validation-dtos.md](validation-dtos.md).

**Done when** every input property has a validator and bounds, and the response DTO lists exactly the fields agreed in step 1.

## 6. Controller and module

One method per endpoint: guards, param pipes, a single service call, mapping to the response DTO, correct status (`@HttpCode(204)` on delete, 201 on create). The current user comes from a param decorator, not the body. Register controller, service and repository binding in the feature module; export only the service if another module needs it; import the module in its parent.

**Done when** no controller method contains a condition on business state, and the app boots.

## 7. Tests

- Service unit tests with a fake repository: happy path and every rejection branch.
- Repository integration test against the real database engine: pagination edges, owner scoping, unique-violation translation.
- E2E: each endpoint's success, validation failure, unauthenticated, another user's resource, not found.

See [testing.md](testing.md).

**Done when** the new tests pass and the existing suite still passes.

## 8. Docs and comments

OpenAPI metadata for the new endpoints, including error responses, if the project generates docs. Doc comments on public service methods that throw domain errors or have side effects, matching the project's comment density.

**Done when** the generated docs show every endpoint with its error responses.

## 9. Verify and report

Run the project's lint, type-check and test commands. Report: files added and changed, endpoints with their statuses, decisions made on the user's behalf (and any step skipped), and the exact commands run with their results.
