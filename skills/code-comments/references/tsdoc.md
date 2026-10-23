# TSDoc / JSDoc doc blocks

Load when writing `/** … */` doc blocks for exported functions, classes and types, or reviewing how they use tags.

Use TSDoc syntax in TypeScript and JSDoc in plain JavaScript (where JSDoc types also feed the type checker). Follow whichever the project already uses; when it uses neither, TSDoc is the default for TypeScript.

## Where a doc block belongs

- Exported functions, classes, methods and types that other modules call: the public surface of a module, a service's public methods, repository contracts, shared utilities, library entry points.
- Not on private helpers whose name and signature say everything, not on controller handlers already described by OpenAPI metadata, not on test functions.
- Editors show the first sentence on hover, so it carries the main point.

## Structure

1. **Summary**: one sentence, present tense, starting with a verb ("Cancels an order and releases its reserved stock."). It says what the function does for the caller, not how.
2. **Remarks** (optional): the why, constraints, performance notes, ordering or concurrency guarantees.
3. **Tags**, in this order: `@param`, `@returns`, `@throws`, `@example`, `@deprecated`, `@see`.

## Tags

| Tag | Write | Skip |
|---|---|---|
| `@param name - …` | Meaning, units, accepted range, what `undefined` means | Repeating the type or the name |
| `@returns` | What comes back on success **and on absence** (`null`, empty array), and ordering | "Returns the result" |
| `@throws {@link NotFoundError}` | Each domain error a caller should handle, and when | Generic programmer errors (`TypeError`) |
| `@example` | One short, invented usage when the call shape is not obvious | Examples that only repeat the signature |
| `@deprecated` | What to use instead and when it will be removed | A bare `@deprecated` with no replacement |
| `@see` / `{@link X}` | The related function or type, or a stable spec/RFC reference | Links to chats or personal documents |
| `@remarks` | Why, constraints, side effects (events emitted, emails sent, cache invalidated) | Implementation narration |
| `@internal` | Exported for tests or sibling modules but not public API, when the build strips it | — |

TypeScript already carries the types. JSDoc type annotations (`{string}`) belong only in plain JavaScript files.

## Per layer

- **Service method**: summary of the business outcome; `@throws` for each domain error by class; `@remarks` for side effects and whether it opens its own transaction.
- **Repository contract method**: what "not found" returns, sort order of lists, whether it locks, whether it must run inside a caller's transaction.
- **DTO / model field**: a one-line doc comment only for meaning, units or format not obvious from the name, validators and API descriptions.
- **Config field**: unit, default and effect of each setting; this is often the only documentation operators read.
- **Exported utility**: summary, edge cases (empty input, negative numbers, time zones), one `@example`.

## Deprecation

- `@deprecated Use {@link newName} instead. Removed in <next major version>.` Editors then strike through call sites.
- Keep behaviour unchanged while deprecated; the removal is a separate, announced change.

## Review checks

- A `@param` for a parameter that no longer exists, or a missing `@param` for a new one: the doc is stale.
- `@throws` lists an error the function no longer throws, or a thrown domain error is missing from it.
- A summary that describes the implementation ("loops over…") instead of the outcome.
- Types repeated in TSDoc in a `.ts` file.
- Examples containing real data, tokens or internal hostnames: replace with invented placeholders.
- If the project generates docs (TypeDoc, API Extractor), run it; unresolved `{@link}` targets and warnings are findings.
