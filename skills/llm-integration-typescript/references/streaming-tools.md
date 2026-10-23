# Streaming, cancellation and tool calling

Load when streaming model output to clients, wiring cancellation, or letting a model call functions (tool use, agents).

## Streaming to the client

- Server-Sent Events (`text/event-stream`) is the default for one-way token streams; WebSockets only when the client also sends messages mid-stream.
- The **controller** owns the stream: it sets headers, writes events and ends the response. The **service** exposes an async iterable (or an observable in Nest) of typed events; the **gateway** adapts the provider's stream into those events.
- Event types are part of the API contract: e.g. `delta` (text chunk), `tool` (status of a tool step), `usage`, `done`, `error`. Document them like any response schema.
- Errors after the stream has started cannot change the HTTP status (it is already 200): send an `error` event with the standard error `code` and close. Clients must handle it.
- Send a heartbeat comment every 15–30 seconds on long streams so proxies do not close idle connections; disable proxy buffering for the route.
- Framework notes: Nest `@Sse()` returns an `Observable<MessageEvent>`; Express and Fastify write to the raw response with flushing; Hono has a `streamSSE` helper. Use whatever the project already uses.

## Cancellation

- Create an `AbortController` per request; abort it when the client disconnects (`req.on('close')` or the framework's equivalent) and pass its signal to the gateway, which passes it to the SDK. A disconnected client must stop token spend.
- Combine with a deadline: `AbortSignal.any([clientSignal, AbortSignal.timeout(ms)])` on runtimes that support it.
- Record partial usage on abort; the tokens were still billed.

## Persisting streamed results

- Accumulate the full text (and usage) server-side while streaming; persist once at `done`, not per chunk.
- If the result must survive a client disconnect (a generated report), run it as a background job and stream progress from the job, not from the HTTP request.

## Tool / function calling

The model proposes a call; **your code decides whether to run it**.

- **Allow-list**: register only the tools this feature needs. Each tool has a name, a description written for the model, and a Zod schema for arguments.
- **Validate** arguments with the schema before execution; on failure, return the validation error to the model as the tool result rather than throwing.
- **Authorize** every execution in the service with the end user's identity and permissions, exactly as an HTTP request would be. The model never acts with a service account's privileges on behalf of a user.
- **Side effects need confirmation**: tools that send, pay, delete or publish either require an explicit user confirmation step or are not exposed to the model at all.
- **Tool results are untrusted text** when they contain external content (web pages, emails, tickets): they are data for the model, and a tool result must not be able to add tools, change permissions or alter the system prompt.
- Tools call services, not repositories or the database directly, so business rules apply.

## Agent loops

- Hard limits per run: maximum steps (e.g. 5–10), maximum total tokens, wall-clock deadline. On hitting one, stop and return what was done with a clear status.
- Detect loops: the same tool with the same arguments twice in a row ends the run.
- Log each step (tool name, argument summary, duration, outcome) with the run id for debugging; redact arguments that carry user data.
- Prefer a fixed workflow (step 1 → step 2 → step 3 with a model call inside each) over an open agent loop when the steps are known; it is cheaper, faster and testable.

## Testing

- Fake gateway that replays scripted events (text chunks, tool-call proposals, errors) to test the service's streaming and tool loop without a provider.
- Test that a client disconnect aborts the gateway call.
- Test that a tool call with invalid arguments, an unauthorized target, or a forbidden tool name is refused.
- Test the iteration cap by scripting a model that never stops calling tools.
