# Planning a feature

Load when writing the plan for a medium or large feature, or splitting it into slices.

## Shape of a plan

Kept in the conversation unless the project stores plans in the repository (then follow its location and format). One screen; a plan nobody reads in full is too long.

1. **Goal**: one or two sentences from the user's point of view.
2. **Acceptance criteria**: numbered, testable, including failure cases. Each later test points back to a number.
3. **Assumptions**: what was decided without asking, so the user can correct it cheaply now.
4. **Changes by layer**:
   - Model / migration: tables, columns, indexes, constraints; whether the migration is safe against the running code.
   - Repository: new or changed methods, named by intent.
   - Service: rules, domain errors thrown, side effects (events, emails, cache), transaction boundaries.
   - Controller / DTOs: endpoints with method, path, statuses; request and response fields.
   - Tests: which levels cover which criteria.
   - Docs: OpenAPI, comments, README or changelog if the project keeps one.
5. **Slices**: ordered list; each slice names the criteria it satisfies.
6. **Risks**: each with how it is handled or why it is accepted.
7. **Out of scope**: noticed, deliberately not done.

## Writing acceptance criteria

- One behaviour per criterion, observable from outside the service: a response, a stored state, an emitted event.
- Phrase as given / when / then, in domain words rather than code words.
- Cover the boundaries: empty, maximum, duplicate, unauthorized, not found, concurrent change.
- A criterion that cannot be tested is a sign of an unclear requirement: turn it into a question.

## Slicing

Good slices are **vertical** (every layer, thin), **ordered by value and risk**, and **independently shippable** (the app works after each one, behind a flag if the feature must not be visible yet).

Typical order for a resource:

1. Create + read one: proves the model, migration, repository, service rules, validation and auth path.
2. List with pagination and filters.
3. Update, including concurrency rules.
4. Delete or archive.
5. Side effects: events, notifications, background jobs.

Put the riskiest unknown (an external API, a data migration, a performance-sensitive query) in the earliest slice that can contain it, so surprises arrive while there is time.

## Sizing signals that raise the process level

- A migration that rewrites or locks a large table.
- A change to an existing public contract (fields, statuses, error codes).
- A new external dependency or service.
- Money, permissions, personal data or deletion.
- More than one team's code touched.

Any one of these makes the work at least medium; two or more make it large.

## Risk list prompts

- Data: migration safety, backfill size, rollback path.
- Concurrency: two requests changing the same record; retries creating duplicates.
- Security: who can call it; whose data it can reach; input limits.
- Performance: new queries on large tables; N+1; unbounded lists.
- Operations: new configuration or secrets; feature flag; monitoring of the new path.
- Compatibility: existing clients, mobile apps that update slowly, other services consuming events.
