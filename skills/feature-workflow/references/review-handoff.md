# Self-review and hand-off

Load before declaring a feature done, or when asked for a pull request description.

## Self-review checklist

Read the full diff once, top to bottom, as a reviewer. Each finding is fixed or listed in the hand-off.

**Scope**
- [ ] Every change traces to an acceptance criterion or a stated assumption
- [ ] No unrelated refactors, renames, formatting churn or dependency changes
- [ ] No debug output, commented-out code, stray files or temporary flags left behind

**Layers**
- [ ] Controllers parse, call one service method and map; no business rules or queries
- [ ] Services hold the rules and throw domain errors; no HTTP or ORM imports
- [ ] Only repository implementations touch the ORM or SQL

**Security**
- [ ] Every new endpoint is authenticated, or explicitly public
- [ ] Ownership/tenant checks on every resource access
- [ ] Input validated and bounded; no server-owned fields accepted from clients
- [ ] Responses mapped; no internal fields, secrets or stack traces exposed

**Data**
- [ ] Migration safe against the running code; indexes for new filters and joins
- [ ] List queries bounded; no N+1
- [ ] Read-modify-write paths protected against concurrent changes

**Errors and operations**
- [ ] Failure paths return the project's error shape with correct statuses
- [ ] New outbound calls have timeouts; retries only where safe
- [ ] New configuration validated at startup and documented in the example env file

**Tests and docs**
- [ ] Each acceptance criterion has a test; each test was seen failing first
- [ ] Docs updated where the project keeps them (OpenAPI, comments on public methods, changelog)

## Hand-off summary

Short, in this order:

1. **What and why**: one paragraph, then the acceptance criteria each marked done, with the test that proves it.
2. **Verification**: the exact commands run (lint, type-check, tests, build, migration, manual check) and their results. Anything not run, with the reason.
3. **Risks and deploy notes**: migration order, required configuration, feature flags, backfills to run, rollback steps.
4. **Assumptions and open questions**: what the user should confirm.
5. **Follow-ups**: things noticed but kept out of scope.

No claim without evidence: "tests pass" names the command; "works" names what was exercised.

## Pull request description

Only when asked. Same content, reordered for a reviewer:

- **Title**: imperative, specific, under about 70 characters, matching the project's convention (ticket prefix, conventional-commit type) if it has one.
- **Summary**: what changes for users or callers, and why.
- **Changes**: grouped by layer or slice, not a file list.
- **How to test**: steps a reviewer can follow, with an invented example request.
- **Risks / deploy notes**: migrations, configuration, flags, rollback.
- **Out of scope / follow-ups**.

Link the ticket by its id. Leave out anything a reviewer can read faster in the diff.

## Commit messages

Only when asked to commit. Follow the project's convention (read recent history). Otherwise: an imperative subject line under about 70 characters, a blank line, then a body explaining why, wrapped at about 72 characters. One logical change per commit; slices make natural commit boundaries.
