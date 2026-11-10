# Node Backend Agent Skills

Agent skills for NestJS and Node.js + TypeScript backends built on the Model-Controller-Service-Repository layering, plus REST API contracts and their OpenAPI docs, TypeScript MCP servers, LLM integration, databases (PostgreSQL, MongoDB, vector stores), a feature delivery workflow, and code comments. Each skill is a plain `SKILL.md` folder under the open Agent Skills format: it follows the project's existing stack, adds no dependencies, and loads its detail files only when a task needs them.

| Skill | Use it for |
|---|---|
| [nestjs-best-practices](skills/nestjs-best-practices/SKILL.md) | Writing, refactoring or reviewing NestJS code: modules, DI, DTO validation, exception filters, guards, repositories, transactions, tests |
| [nodejs-typescript-best-practices](skills/nodejs-typescript-best-practices/SKILL.md) | Node.js + TypeScript without NestJS (Express, Fastify, Hono, plain `http`): layering, strict tsconfig, validation, errors, config, shutdown, tests |
| [api-design](skills/api-design/SKILL.md) | The HTTP contract and its OpenAPI docs: URLs, methods, status codes, error envelope, pagination, versioning, idempotency, rate limits |
| [mcp-server-typescript](skills/mcp-server-typescript/SKILL.md) | Building or reviewing MCP servers in TypeScript: tools, resources, schemas, errors, transports, auth, tests |
| [llm-integration-typescript](skills/llm-integration-typescript/SKILL.md) | Adding LLM features to a Node/NestJS backend: provider gateway, prompts as code, structured output, streaming, tool calling, RAG, cost budgets, evals |
| [database-best-practices](skills/database-best-practices/SKILL.md) | The database itself, on PostgreSQL, MongoDB/Mongoose or a vector store: schema and document design, integrity, indexes, safe migrations, query tuning, concurrency, connection pools, access control |
| [feature-workflow](skills/feature-workflow/SKILL.md) | Delivering a ticket or user story end to end: sizing, design-changing questions only, plan by layer, tests first, build inside-out, verify, self-review, hand-off |
| [code-comments](skills/code-comments/SKILL.md) | Writing, reviewing or cleaning up comments and TSDoc/JSDoc: why over what, doc blocks on public APIs, TODO hygiene |

## Install

Clone once:

```sh
git clone <repo-url> ~/src/node-backend-skills
```

**Claude Code, for every project** — link each skill into your personal skills folder:

```sh
mkdir -p ~/.claude/skills
ln -s ~/src/node-backend-skills/skills/* ~/.claude/skills/
```

**Claude Code, for one project only** — run inside that project:

```sh
mkdir -p .claude/skills
cp -R ~/src/node-backend-skills/skills/nestjs-best-practices .claude/skills/
```

Copy only the skills the project needs; every installed skill adds its description to each session. Commit `.claude/skills/` so the whole team gets them.

**Other agents** that read the Agent Skills format: point them at, or copy, the same `skills/<name>/` folders into their skills directory.

## Update

Symlinked installs: `git -C ~/src/node-backend-skills pull`. Copied installs: pull, then copy the folders again.

## Contributing

Rules for skill content, evals and size budgets are in [AGENTS.md](AGENTS.md). Run `python3 scripts/lint.py` before committing; it must pass.
