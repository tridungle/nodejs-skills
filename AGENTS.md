# AGENTS.md

Rules for this repository, on top of whatever global guidance an agent already loads.

## What this repository is

Agent skills for TypeScript backends: NestJS and Node.js services built on the Model-Controller-Service-Repository layering, plus the topics around them: API contracts, databases (PostgreSQL, MongoDB, vector stores), LLM integration, MCP servers, code comments and the feature delivery workflow. Every skill teaches rules an agent applies to someone else's project, so each one adapts to that project's stack instead of imposing ours.

A skill here earns its place by being specific to this stack and these layers. A general-purpose workflow that already exists elsewhere is installed, not rebuilt, unless we need rules of our own in it.

## Every skill keeps the run cheap

Each installed description loads into every session, each `SKILL.md` loads on activation, and each `references/` file loads only when a task reaches it. Write for that:

- **Description**: at most 300 characters. What the skill covers, then `Use when …`, then the boundary with the nearest sibling where one is close ("not for …", "… belong to `other-skill`").
- **`SKILL.md`**: the map. At most 500 lines and 5,000 words; in practice under about 150 lines. Detail goes to `references/`.
- **Each reference**: one topic, at most 200 lines, linked from `SKILL.md` with the task that needs it, so a run opens one file, not all of them.
- **About ten skills at most.** Past that, descriptions compete for the same requests. A new topic becomes a reference in an existing skill unless requests for it would not trigger that skill.

Every `SKILL.md` opens with **cost rules** that bind the agent using it: follow the project's existing libraries and conventions first; add no dependency, extension or infrastructure without asking; read only the reference the task needs; make the smallest change the request needs; no speculative abstraction.

## Shape of a skill

```text
skills/<name>/
  SKILL.md          # frontmatter: name (= folder), description, license, metadata.tags
  references/*.md   # optional, one topic each
  evals/eval_queries.json   # trigger set (see below)
  evals/evals.json          # optional output cases
```

`SKILL.md` sections, in this order where they apply: purpose in one or two sentences; cost rules; where the topic sits in the four layers (a table); numbered non-negotiables; a "pick the reference for the task" table; a review checklist whose items are reported as pass or fail with `file:line` evidence; an anti-pattern table with the fix beside each.

Skills refer to each other **by name in backticks** (`api-design`), with "when installed", because any skill may be installed alone. Never link into another skill's `references/`.

## Examples are abstract, never real

A skill teaches a rule; it never carries a sample of anyone's actual work. Every example in `SKILL.md`, `references/` and the eval sets is a shape or an invented placeholder: invented product names, paths, tickets and data.

Never a real post, account, customer record, person's text, captured run, or anything copied from published writing, including the sources a skill was researched from: those are read for topics, never quoted. Two reasons, each sufficient: such material is private or someone else's, and a sentence printed in a skill comes back verbatim in the next run's output.

## Text only: a skill instructs, it never ships code

A skill folder holds the files shown above and nothing else: no scripts, templates, fixtures, binaries, or files meant to be executed or copied into the user's project.

An agent reading a skill knows its own platform, shell, runtimes and the user's repository; a file written here months ago knows none of that. So a skill states what to check, what counts as a pass, the thresholds and the evidence to report, and the agent writes whatever it needs or checks by reading.

The line is what a code block is for. Code that **is the subject being taught** stays: what a repository contract looks like, a migration statement, a configuration entry, a one-line command against a standard tool. A **routine the reader is meant to run** against their project is written as instructions instead, however short.

A check that cannot be written as an instruction with a stated threshold and stated evidence is not ready to be in a skill.

## Facts that go stale

- Version-dependent behaviour names the version it needs ("PostgreSQL 12+", "Express 5").
- Model ids, prices and SDK method names are never fixed in a skill; it tells the agent to read the installed version or the provider's current documentation.
- Before stating a library or database behaviour you are unsure of, check it; correct it in the same change if it was wrong.

## Evals measure a description

Reading proves a rule; only measurement shows whether a description fires on the requests it should and stays quiet on the rest.

- **A trigger set is written for every skill**, in `evals/eval_queries.json`: around twenty invented queries, half should-trigger and half near-miss negatives, meaning requests that belong to a sibling one boundary away, named in `belongs_to`. Each query is labelled `train` or `validation` once and never reshuffled. Add a near-miss whenever a description gains a new boundary.
- **Running a set is optional and costs money**, one agent session per query per run. Never start a run without the repository owner's explicit go-ahead in the current conversation, and never wire it into CI.
- **A claim about triggering is a number or it is nothing**: trigger rate over at least three runs per query, with model, effort level and date beside it. Until a set has run, say it is unrun; "triggers reliably" with no run behind it is not allowed.
- **Fix the category, not the keyword.** A missed query marks a gap in what the description covers; pasting its words in buys that query only. Choose an iteration by its validation pass rate.
- **No runner and no run output are committed.** The loop is written for the run and thrown away; transcripts and results stay in the agent's scratch folder.

## Checks and commits

`python3 scripts/lint.py` must pass before every commit. It checks frontmatter and the description length, the folder shape, size budgets, that every reference is linked and every link resolves, that sibling skills named in backticks exist, that single-language skills map their examples to other stacks, and the shape of every eval set (including `checks` regexes against their `pass` and `fail` lists). It reads what git tracks, so stage new files before running it.

When adding a skill: write the folder, run lint, add a row to the README table, cross-link the siblings it borders, and check the descriptions side by side for new overlaps.

One logical change per commit. The message states what changed and, for description changes, that triggering is unmeasured unless a run was made.

## Distribution is the git repository

There is no plugin or extension manifest. Users clone the repository and copy or symlink skill folders into their agent's skills directory, as the README describes; a symlinked install updates with `git pull`. The folder name is therefore the public interface: renaming or removing a skill folder breaks every install that points at it, and a commit that does so says so in its message.
