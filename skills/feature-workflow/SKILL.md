---
name: feature-workflow
description: "Delivers a feature from ticket, user story or spec to a verified, reviewable change in a TypeScript backend: size the work, ask only design-changing questions, plan by layer, write tests first, build inside-out, verify, self-review, hand off. Use when implementing a ticket or feature end to end."
license: MIT
metadata:
  tags: ["workflow", "planning", "tdd", "feature", "typescript", "backend"]
---

# Feature Workflow

Turn a requirement into a change that does what was asked, nothing more, passes its own tests, and can be reviewed in one sitting. Run this process around the code rules in `nestjs-best-practices` or `nodejs-typescript-best-practices`; for plain CRUD resources, their `crud-feature.md` reference is the step list for the build phase.

## Cost rules

- **Effort matches size.** A one-file change does not get a written plan or a round of questions. Size first (step 1) and skip what the size does not need.
- **One batch of questions, only design-changing ones**, each with a recommended default. Everything else becomes a stated assumption.
- **Read one similar feature, not the whole codebase.** Copy its conventions.
- **No scope creep.** Refactors, renames, dependency upgrades and "while I'm here" fixes the requirement did not ask for go into the follow-up list, not the diff.
- **Stop at the hand-off.** Do not commit, push or open a pull request unless asked.

## 1. Size the work

| Size | Looks like | Process |
|---|---|---|
| Small | One layer or a few files, behaviour fully specified | Understand → test → implement → verify → short summary |
| Medium | Several layers of one feature, a new endpoint, a validation or business rule | Full process; share the plan and continue unless something in it is a real decision |
| Large | Several modules, a schema migration on a large table, a breaking API change, a new external service or dependency | Full process; **wait for plan approval**; split into slices that each ship on their own |

When unsure between two sizes, take the larger one.

## 2. Understand

- Restate the goal in one or two sentences, from the user's point of view.
- Turn the requirement into **acceptance criteria**: short, testable statements of behaviour (given state, when action, then outcome), including at least one failure case per rule.
- Read one existing feature most like this one and the code paths this change touches. Note the conventions to copy.
- List the layers affected: model/migration, repository, service, controller/DTO, docs.

## 3. Clarify

Ask only when the answer changes the design, data model, contract or security. Typical topics: who may perform the action and on whose data; what happens on conflict or duplicate; limits and sizes; whether existing clients must keep working unchanged; synchronous or background processing.

Put all questions in one message, each with a recommended answer, so the user can reply "go with your defaults". Everything not asked becomes an assumption written in the plan.

## 4. Plan

One screen, by layer, with risks and slices. The shape and examples of what belongs in it are in [planning.md](references/planning.md).

- Changes per layer: model and migration, repository methods, service rules, controller and DTOs, tests, docs.
- Contract changes: new or changed endpoints, fields and statuses; anything breaking.
- Risks: migration on a large table, concurrency, performance, security, external dependencies.
- **Vertical slices**: each slice is a thin, working path through all layers (for example create and read first, then list, then update) rather than one layer at a time.
- Out of scope: what was deliberately left for later.

## 5. Test first, per slice

- Write the tests for the slice's acceptance criteria before the implementation: service unit tests for business rules first, then HTTP tests for the endpoint contract.
- Run them and confirm they **fail for the expected reason** (missing method, wrong status), not because of a setup error.
- For a bug or a changed behaviour, the first test reproduces the current wrong behaviour.

## 6. Build inside-out

Model and migration → repository → service → controller and DTOs → wiring. Follow the layer rules of the framework skill; use its `crud-feature.md` for resource endpoints. Make the slice's tests pass, then move to the next slice. Keep each slice's diff reviewable on its own.

## 7. Verify

Run the project's own commands: lint, type-check, unit and integration tests, and the build. Apply the migration to a local database. Start the app and exercise the new endpoint once (success and one failure). Record each command and its result; a step that could not run is reported as not run, with the reason.

## 8. Self-review and hand off

Review the diff as a reviewer would, using the checklist in [review-handoff.md](references/review-handoff.md): scope, layer rules, authorization, validation, errors, queries, migration safety, tests, docs and leftovers. Fix what it finds, then hand off with:

- what changed and why, mapped to the acceptance criteria;
- how it was verified (commands and results);
- risks, deploy and migration notes;
- assumptions made and questions still open;
- the follow-up list (things noticed but out of scope).

If asked for a pull request description, use the same content; the shape is in [review-handoff.md](references/review-handoff.md).

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| Ten clarifying questions before reading the code | Read first; ask only what the code cannot answer, with defaults |
| Building all repositories, then all services, then all controllers | Vertical slices that each work end to end |
| Tests written after the code, shaped to pass | Tests from acceptance criteria first, seen failing |
| "Also cleaned up the module and upgraded the ORM" | Requirement only; extras in the follow-up list |
| "Done" without running anything | Commands run and results reported |
| A plan document for a two-line change | Size first; small work skips the plan |
