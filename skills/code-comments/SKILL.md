---
name: code-comments
description: "Writes and reviews code comments and TSDoc/JSDoc in TypeScript and JavaScript: when a comment earns its place, why over what, doc blocks on exported functions and classes, @throws/@deprecated, TODO hygiene, stale or noise comments. Not HTTP API docs. Use when adding or cleaning up comments."
license: MIT
metadata:
  tags: ["comments", "tsdoc", "jsdoc", "typescript", "documentation"]
---

# Code Comments

A comment is for what the code cannot say itself: why it is this way, what it promises callers, and what would go wrong if it were changed. Everything else is noise that costs a reader time and goes stale.

## Cost rules

- **Match the file's existing comment density and style.** A sparsely commented codebase does not get a doc block on every function because one task touched it.
- **Comment only code the task touches**, unless the user asked for an audit or a documentation pass.
- **Fewer, truer comments beat more comments.** Deleting a wrong comment is a bigger improvement than adding a right one.
- Open [tsdoc.md](references/tsdoc.md) only when writing doc blocks (`/** … */`) for public APIs or reviewing tag usage.

## When a comment earns its place

Write one when the code cannot express it:

| Earns a comment | Example of the shape |
|---|---|
| **Why** a non-obvious choice was made | "Sorted before dedupe because the upstream feed is unordered and the first occurrence wins." |
| A constraint from outside the code | "The provider rejects batches over 100 items." |
| A workaround, with how to know when to remove it | "Works around a driver bug that drops the timezone; remove once the driver is upgraded past the fixed version." |
| A trap for the next editor | "Order matters: the guard must run before the cache lookup or anonymous users read cached private data." |
| The contract of a public function | What it returns on absence, what it throws, side effects, units |
| A non-obvious algorithm or regex | One line naming what it matches or computes, plus an example input |
| A deliberate empty `catch` or ignored result | Why ignoring it is safe |

Do not write one when:

- It restates the code (`// increment counter`, `// get user by id` above `getUserById`).
- A better name would say it. Rename the variable or extract a well-named function instead.
- It narrates history (`// changed by …`, `// added for ticket …`, `// old version below`). That belongs in version control.
- It is commented-out code. Delete it; git keeps it.
- It duplicates the type (`@param id string the id`) or a schema description that already documents the field.
- It describes what the next line obviously does, step by step, as a substitute for clear code.

## Writing rules

- Say **why** or **what is promised**, not **what the line does**.
- One idea per comment, in plain present-tense sentences. No jokes, no blame, no "obviously".
- Put the comment immediately above the code it explains; trailing end-of-line comments only for short notes on a single value (units, a magic number's source).
- Name units and formats: milliseconds or seconds, cents or decimal, UTC or local.
- Reference stable things: an issue id, a spec section, an RFC number. Never a person's name or a chat thread.
- Use the language the codebase's comments are already written in.
- When code changes, update or delete the comments it invalidates **in the same change**. A stale comment is worse than none.

## By layer (Model-Controller-Service-Repository)

| Layer | Comment |
|---|---|
| Model / DTO | Field meaning, units and constraints that types and validators do not show. If an OpenAPI description decorator already documents the field, do not repeat it in TSDoc. |
| Controller | Usually nothing: route decorators and OpenAPI metadata are the documentation. Comment only a non-obvious status choice or a deliberate deviation from the API conventions. |
| Service | A doc block on each public method that holds a business rule: what it guarantees, which domain errors it throws and when, side effects (events, emails), transaction expectations. |
| Repository | Semantics the signature hides: returns `null` vs throws on absence, ordering, locking, whether it must run inside a transaction. |
| Config, guards, filters, middleware | Why the order or setting is what it is; these are the places later edits break silently. |

## TODO, FIXME and markers

- `TODO` and `FIXME` carry an issue reference or a concrete condition (`TODO(#123): …`, `TODO: remove after the v1 endpoint is retired`). A bare `TODO: fix this` is a finding.
- No new `TODO` for work the current task should do; do the work, or tell the user it is out of scope.
- Lint suppressions (`eslint-disable-next-line`, `@ts-expect-error`) carry a reason on the same line.

## Reviewing comments

Report each finding with `file:line`, sorted by harm:

1. **Wrong**: the comment contradicts the code (a stale promise, wrong units, a removed parameter still described). Fix or delete it.
2. **Missing where it matters**: a public service method that throws domain errors without saying so, a workaround with no explanation, an ignored error with no reason.
3. **Noise**: restating code, commented-out blocks, history notes, bare TODOs. Delete.

Do not rewrite comments that are correct and merely phrased differently from how you would write them.

## Other languages

The same rules apply outside TypeScript; only the doc syntax changes: Python docstrings (PEP 257), Javadoc/KDoc, GoDoc (a sentence starting with the identifier's name), Rust `///` doc comments, C# XML doc comments. Follow each ecosystem's doc tool conventions.

## Checklist

- [ ] No comment restates the code or narrates history
- [ ] No commented-out code
- [ ] Every non-obvious choice, workaround and trap has a why-comment
- [ ] Public service and repository methods document absence, errors and side effects
- [ ] Every TODO/FIXME has an issue or a condition; every suppression has a reason
- [ ] Comments touched by the change still match the code
