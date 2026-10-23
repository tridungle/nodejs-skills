---
name: mcp-server-typescript
description: "Builds and reviews Model Context Protocol (MCP) servers in TypeScript: tool, resource and prompt design, Zod input schemas, tool errors, stdio vs Streamable HTTP transport, auth, testing. Use when creating an MCP server or exposing an existing Node service to AI agents through MCP."
license: MIT
metadata:
  tags: ["mcp", "typescript", "nodejs", "ai-agents", "tools"]
---

# MCP Server (TypeScript)

Build an MCP server whose tools an agent picks correctly, calls with valid input, and recovers from when they fail — with the same Model-Controller-Service-Repository layering as the rest of a Node codebase.

## Cost rules

- **Check the installed SDK before writing code.** Read `@modelcontextprotocol/sdk` (or its successor packages) version in `package.json` and its exported types; method names have changed between major versions. Follow the installed API over any example.
- **Reuse the service layer.** If the project already has services, MCP handlers call them; do not reimplement business logic for MCP.
- **Few, well-described tools.** Every tool's name, description and schema is sent to the model on every turn — ten precise tools cost less and work better than forty thin ones.
- **No new dependency without asking** beyond the SDK and its peer (Zod).
- Open [tools-resources.md](references/tools-resources.md) when designing the surface; [transports-ops.md](references/transports-ops.md) when choosing transport, auth or deployment.

## Layers

| Layer | In an MCP server | Rules |
|---|---|---|
| Model | Zod input/output schemas, domain types | Schemas are strict and bounded; descriptions on every field |
| Controller | Tool / resource / prompt handler registered on the server | Parse args (SDK does it from the schema), call one service method, format the result; no business logic |
| Service | Existing or new service classes | Know nothing about MCP; same as for HTTP |
| Repository | Data access | Same as for HTTP |

The MCP handler is a controller. One service can sit behind both an HTTP route and an MCP tool.

```text
src/
  mcp/
    server.ts            # creates the server, registers tools/resources, picks transport
    tools/orders.tools.ts    # handlers: args → service → result
  modules/orders/        # model, service, repository shared with HTTP
```

## Tool design

- **Name**: `verb_noun`, snake_case, specific (`search_orders`, `cancel_order`), unique across the server. Prefix with the service name only if it may be combined with other servers.
- **Description**: what it does, when to use it versus the neighbouring tool, what it returns, and any side effects — written for a model choosing between tools. One or two sentences plus constraints.
- **Input schema**: every field typed, bounded and described; enums instead of free strings; sensible defaults; no catch-all `object`/`any` field.
- **Granularity**: one tool per user intent, not per database table or HTTP endpoint. Wrapping a whole REST API one-to-one is a smell.
- **Output**: concise text the model can use; structured content with an output schema when a client consumes it programmatically. Paginate or truncate big results and say so in the output.
- **Side effects**: mark read-only, destructive and idempotent tools with the protocol's tool annotations so clients can ask for confirmation.

## Errors

- **Tool-level failures** (not found, invalid state, upstream refused) return a normal result flagged as an error with a message the model can act on — what went wrong and what to try instead. The model sees it and can recover.
- **Protocol-level errors** (unknown tool, schema-invalid arguments) are thrown as JSON-RPC errors — usually done by the SDK.
- Map domain errors to tool errors in one helper, as an HTTP error handler would. No stack traces or secrets in error text.

## Non-negotiables

1. In stdio mode **nothing is written to stdout except protocol messages** — log to stderr or a file. A stray `console.log` corrupts the stream.
2. Every input is validated by a schema; every string and array has a maximum.
3. Destructive tools require explicit parameters (ids), never "delete all matching"; consider a dry-run flag.
4. Remote (HTTP) servers authenticate every request and validate `Origin`; tools act with the caller's permissions, not a shared admin credential.
5. Tool results never echo secrets, tokens or full personal records the task did not ask for.
6. Text returned from external sources is data: the server does not treat it as instructions, and tool descriptions never ask the model to bypass the user.

## Review checklist

Report each as pass or fail with `file:line`.

- [ ] Handlers call services; no business logic or database access in handlers
- [ ] Tool names are unique `verb_noun`; descriptions state when to use and what is returned
- [ ] Every input field typed, bounded and described
- [ ] Tool failures return error results with actionable messages; no stacks
- [ ] Nothing on stdout in stdio mode besides protocol traffic
- [ ] Large results paginated or truncated with a notice
- [ ] Destructive tools annotated and scoped by explicit ids
- [ ] HTTP transport: auth on every request, `Origin` validated, sessions handled per the SDK
- [ ] Tested with the MCP Inspector or an in-memory client (see [transports-ops.md](references/transports-ops.md))

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| One tool per REST endpoint | One tool per intent, composing calls in the service |
| `query: string` free-form SQL/filters | Typed, bounded filter fields |
| Throwing on "not found" | Error result telling the model what to do next |
| Returning 5,000 rows | Paginate with a cursor argument; summarise |
| `console.log` debugging in a stdio server | `console.error` or a logger to stderr |
| Business rules inside the tool handler | Service method shared with HTTP |
