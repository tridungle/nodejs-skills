---
name: llm-integration-typescript
description: "Integrates LLM APIs into Node.js/NestJS TypeScript backends: provider gateway behind services, prompts as code, structured output, streaming, timeouts and retries, token and cost budgets, RAG, prompt-injection defence, eval tests. Use when adding or reviewing LLM-powered backend features."
license: MIT
metadata:
  tags: ["llm", "ai", "typescript", "nodejs", "nestjs", "rag"]
---

# LLM Integration (TypeScript backends)

Add LLM-powered features to a Node.js or NestJS backend so that the model is one replaceable dependency, every call has a budget and a timeout, its output is validated before anything trusts it, and a prompt change is tested like a code change.

This skill is for a backend **calling** a model. Exposing your backend **to** agents as tools is `mcp-server-typescript`.

## Cost rules

Two costs matter here: the agent's tokens while writing the code, and the model tokens the feature spends in production.

- **Use the SDK the project already has** (a provider SDK or a multi-provider one such as the Vercel AI SDK or LangChain). Do not add or switch SDKs without asking.
- **Read only the reference the task needs**: [streaming-tools.md](references/streaming-tools.md), [rag.md](references/rag.md), [evals-cost.md](references/evals-cost.md).
- **Model ids and prices change between releases**: never hard-code them in services. They live in config, and are checked against the provider's current documentation, not memory.
- **Smallest model that passes the eval** for each task; a larger model is a measured decision, not a default.
- **No LLM where a deterministic rule works.** Parsing a date, matching an enum or validating an email is code, not a prompt.

## Layers (Model-Controller-Service-Repository)

| Layer | Owns | Never does |
|---|---|---|
| Model | Prompt templates, input variables, output schemas (Zod), domain types | Call the provider |
| Controller | HTTP or SSE endpoint, auth, request validation, streaming the response to the client | Build prompts, call the SDK |
| Service | Decides when to call the model, assembles context, validates and post-processes output, falls back on failure, enforces per-user budgets | Import the provider SDK |
| Gateway (repository layer) | The only code that imports the provider SDK: one `LlmGateway` port plus an implementation per provider; timeouts, retries, usage reporting | Business decisions, prompt wording |

The model is an external dependency like a database: services depend on a port, tests use a fake, swapping provider touches one file.

```ts
// llm.gateway.ts: port the services depend on (abstract class doubles as a Nest DI token)
export abstract class LlmGateway {
  abstract complete<T>(req: {
    task: string;                 // stable name for logging, budgets and config lookup
    system: string;
    messages: ChatMessage[];
    schema?: ZodType<T>;          // when set, output is parsed and validated
    maxOutputTokens: number;
    signal?: AbortSignal;
  }): Promise<{ output: T; usage: TokenUsage; model: string }>;
}
```

Model choice per `task` comes from config, so a model upgrade is a config change plus an eval run.

## Non-negotiables

1. **Prompts are code**: stored in files or constants next to the feature, reviewed in pull requests, versioned. Never assembled by concatenating raw user input into instructions.
2. **System and user content stay separate.** User-supplied and retrieved text goes in delimited user content, never into the system prompt.
3. **Model output is untrusted input.** Validate it with a schema before use; escape it before rendering as HTML; never execute it, never pass it to SQL, a shell or `eval`.
4. **Every call has a timeout, a max output token limit and an abort signal** tied to the client's request.
5. **Retries only on retryable failures** (429, 5xx, overloaded, network), with capped exponential backoff, jitter and the provider's `retry-after`. Never retry a 400.
6. **Per-user or per-tenant budgets and rate limits** on endpoints that trigger model calls; a single client must not be able to spend the month's budget.
7. **Log usage, not content**: task, model, input and output tokens, latency, cost estimate, request id. Full prompts and outputs only behind an explicit debug setting with redaction, because they carry user data.
8. **No secrets or unnecessary personal data in prompts.** Redact before sending; check the provider's data-retention terms match the data you send.
9. **Tool or function calling acts with the user's permissions**: every tool the model can call is allow-listed, its arguments validated, and authorization checked in the service as for an HTTP request. See [streaming-tools.md](references/streaming-tools.md).
10. **A prompt or model change runs the eval set** before merge. See [evals-cost.md](references/evals-cost.md).

## Structured output

- Use the provider's structured-output or tool-schema feature when available, **and** validate with the Zod schema anyway; providers differ in how strictly they enforce it.
- On a validation failure: one repair attempt that includes the validation error, then a typed domain error (`LlmOutputInvalidError`), never a half-parsed object.
- Keep output schemas small and flat; every optional field is one more way to be wrong.
- Ask for enums and ids from a supplied list rather than free text whenever the result drives code.

## Failure and fallback

Decide per feature, in the service, what the user sees when the model is slow, down, over budget or returns invalid output: a cached answer, a smaller model, a non-AI fallback, or a clear error. "Spinner forever" is not an option. Long tasks run as background jobs with a status endpoint rather than holding an HTTP request open.

## Pick the reference for the task

| Task | Read |
|---|---|
| Streaming to clients (SSE), cancellation, tool/function-calling loops, agents | [streaming-tools.md](references/streaming-tools.md) |
| Retrieval-augmented generation: chunking, embeddings, vector search, citations, tenancy | [rag.md](references/rag.md) |
| Eval sets, prompt regression tests, token and cost control, caching, batching, model choice | [evals-cost.md](references/evals-cost.md) |

Framework wiring (modules, DI, config, error filter) follows `nestjs-best-practices` or `nodejs-typescript-best-practices`; the SSE or JSON contract follows `api-design`.

## Review checklist

Report each as pass or fail with `file:line`.

- [ ] Only gateway files import the provider SDK; services depend on the port
- [ ] Model ids come from config, per task
- [ ] Every call sets a timeout, max output tokens and an abort signal
- [ ] Retries limited to retryable errors with backoff
- [ ] Structured output validated with a schema; invalid output becomes a typed error
- [ ] User and retrieved text never enter the system prompt or instructions unmarked
- [ ] Model output escaped or validated before rendering, storing or acting on it
- [ ] Tool calls allow-listed, argument-validated and authorized as the user
- [ ] Per-user/tenant budget or rate limit on model-triggering endpoints
- [ ] Usage logged per call; content not logged by default
- [ ] An eval set exists and runs when prompts or models change
- [ ] A fallback is defined for timeout, outage and invalid output

## Anti-patterns

| Anti-pattern | Instead |
|---|---|
| `openai.chat.completions.create` (or any SDK call) inside a controller or service | Call through the `LlmGateway` port |
| Prompt built with template strings mixing instructions and user input | Fixed instructions; user content in its own delimited message |
| `JSON.parse(output)` and trust | Structured output + schema validation + typed error |
| Hard-coded model name in ten files | Per-task model in config |
| Unbounded `max_tokens`, no timeout | Explicit limits on every call |
| Logging full prompts and completions in production | Log usage metadata; content only when debugging, redacted |
| "It looked right in the playground" | An eval set that runs in CI |
| An agent loop with no iteration cap | Max steps, max tokens and a wall-clock deadline per run |
