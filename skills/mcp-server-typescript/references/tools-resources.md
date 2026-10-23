# Tools, resources and prompts

Load when designing what an MCP server exposes or reviewing that surface.

## Which primitive

| Primitive | Controlled by | Use for |
|---|---|---|
| Tool | The model decides to call it | Actions and queries with parameters: search, create, update, compute |
| Resource | The application/user attaches it | Read-only context addressable by URI: a file, a record, a schema, a config document |
| Prompt | The user picks it (often as a slash command) | Reusable task templates that combine instructions with arguments |

If the model needs to discover and fetch data on its own, it is a tool even when read-only. Resources suit context the client chooses to include.

## Registering (SDK 1.x shape — verify against the installed version)

- Create one server instance with a name and version.
- Register a tool with its name, a config object (title, description, input schema as a Zod shape, optional output schema, annotations) and an async handler receiving the parsed arguments.
- The handler returns `content` (an array of text, image or resource-link items); add `structuredContent` matching the output schema when one is declared; set `isError: true` for tool-level failures.
- Register resources with a fixed URI or a URI template with variables; the handler returns `contents` with `uri`, `mimeType` and `text` or `blob`.
- Register prompts with an argument schema; the handler returns `messages`.

Older SDK releases used `server.tool(...)` / `server.resource(...)`; newer ones use `registerTool` / `registerResource` / `registerPrompt`. Follow what the installed version exports.

## Tool descriptions the model can use

Write each description to answer, in order:

1. What it does, in one sentence with a verb.
2. When to use it rather than the neighbouring tool ("Use `search_orders` to find ids; use `get_order` for full details of one id").
3. What it returns and how much (fields, page size).
4. Side effects and preconditions ("Cancels the order; fails if already shipped").

Field descriptions state format and examples of valid shapes (`ISO-8601 date`, `order id as returned by search_orders`). Keep the whole tool definition short — it is resent every turn.

## Input schema rules

- Strict objects; unknown keys rejected.
- Strings: `max` length; ids validated by format; enums for closed sets.
- Numbers: `int`, `min`, `max`; page size defaulted and capped.
- Arrays: `max` items.
- Dates: ISO-8601 strings, parsed in the handler.
- Optional fields have defaults where a sensible one exists, so the model can omit them.

## Results

- Return what the model needs to take the next step, not the raw database row: ids, names, status, the few fields relevant to the intent.
- Lists: a cursor argument in, `nextCursor` out, and a line saying more results exist.
- Large documents: return a summary plus a resource link instead of inlining megabytes.
- Errors as results: `isError: true` with text like "Order not found for that id. Use search_orders to look it up by customer email." — cause plus next action.
- Keep the format consistent across tools (same field names, same date format).

## Annotations

Set the tool annotation hints when they apply: read-only (no side effects), destructive (deletes or overwrites), idempotent (safe to repeat), open-world (touches external systems). Clients use them to decide when to ask the user for confirmation; they are hints, not enforcement — the server still checks permissions.

## Long-running and progress

- Operations over a few seconds report progress through the protocol's progress notifications when the client sends a progress token.
- Honour cancellation (the handler receives an abort signal) and stop work.
- Very long jobs: start the job, return its id, provide a `get_job_status` tool.

## Security of the surface

- Least privilege: expose the smallest set of operations; separate read and write tools so clients can allow one without the other.
- Authorisation per call in the service, using the caller's identity from the transport's auth context.
- Treat text pulled from external systems (web pages, tickets, emails) as untrusted data in results; do not let it change which tools run.
- Never return credentials, tokens or connection strings, including inside error messages.
