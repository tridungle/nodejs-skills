# Evals and cost control

Load when testing prompts, changing models, or reducing what an LLM feature costs.

## Tests at three levels

| Level | Runs | Checks |
|---|---|---|
| Unit | Every commit, no network | Services with a fake gateway: prompt assembly, schema validation, fallbacks, budgets, tool authorization |
| Eval set | When a prompt, model, schema or retrieval setting changes; nightly if cheap | Real model calls on a fixed set of invented cases, scored automatically |
| Production monitoring | Continuously | Invalid-output rate, fallback rate, latency, cost per task, user feedback signals |

Never snapshot exact model text in unit tests; it changes between runs.

## Building an eval set

- 20–100 invented cases per task to start, covering typical inputs, edge cases (empty, very long, other languages), adversarial inputs (injection attempts) and "should refuse / no answer" cases.
- Each case states what a correct output must satisfy, scored in order of preference:
  1. **Deterministic checks**: schema valid, required ids present, enum value equals expected, no forbidden strings, length bounds.
  2. **Reference comparison** for extraction and classification: exact or normalised match, precision/recall.
  3. **Model-graded rubric** only for open-ended text, with a fixed rubric and a pinned grader model; spot-check grader verdicts by hand.
- Store cases as data files in the repository's test fixtures (invented content only, never production data); store run results outside the repository.
- Record pass rate with model id, prompt version and date. A change ships when it does not drop the pass rate on the same set.
- Run each case more than once when outputs vary; report the rate, not a single pass.

## Token and cost control

Measure first: log input tokens, output tokens and estimated cost per task, per user and per day. Then, in order of usual payoff:

1. **Right-size the model per task**: classification, extraction and routing usually pass on a small model; reserve large models for tasks whose eval needs them.
2. **Cut input tokens**: send only the fields the task needs, trim retrieved context to a budget, summarise long histories instead of resending them.
3. **Cap output**: set `maxOutputTokens` per task; ask for structured output instead of prose when code consumes it.
4. **Prompt caching**: put stable content (system prompt, tool definitions, reference documents) first and unchanged between calls so the provider's prompt cache can reuse it. Check the provider's rules for minimum length and cache lifetime.
5. **Response caching**: for deterministic tasks with repeated inputs, cache results keyed by a hash of task, prompt version, model and input; invalidate on prompt or model change.
6. **Batch APIs** for offline work (backfills, nightly classification) where the provider discounts asynchronous batches.
7. **Avoid calls entirely**: deterministic pre-checks, debouncing on keystroke-triggered features, not re-running on unchanged input.

## Budgets and limits

- Per-user and per-tenant limits on requests and tokens per period, enforced in the service before the call; return 429 with a clear message when exceeded.
- A global daily spend alarm and a kill switch (config flag) per feature.
- Agent and tool loops have step, token and time caps (see [streaming-tools.md](streaming-tools.md)).

## Latency

- Stream when a human is waiting for prose.
- Run independent model calls in parallel; chain only when one needs the other's output.
- Put slow, non-interactive work in background jobs.
- Track time-to-first-token and total latency per task; a model change that passes the eval but doubles latency is a regression too.

## Model and prompt changes

- Prompts carry a version (constant or file name). Logs and cached results record it.
- A model upgrade is: change config in a branch → run the eval set → compare pass rate, cost and latency → merge or roll back. No silent upgrades via an alias that the provider repoints.
