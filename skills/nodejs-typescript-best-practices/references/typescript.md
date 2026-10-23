# TypeScript configuration and type patterns

Load when creating or tightening `tsconfig.json`, choosing a module system, or reviewing type safety.

## Compiler options for a backend service

| Option | Value | Why |
|---|---|---|
| `strict` | `true` | Non-negotiable baseline |
| `noUncheckedIndexedAccess` | `true` | `arr[i]` and `record[key]` become `T \| undefined`; catches the most common runtime crash |
| `exactOptionalPropertyTypes` | `true` for new projects | Distinguishes "absent" from "set to undefined" — useful for PATCH semantics; noisy to retrofit |
| `noImplicitOverride`, `noFallthroughCasesInSwitch` | `true` | Cheap safety |
| `module` / `moduleResolution` | `NodeNext` / `NodeNext` | Matches how Node actually resolves; use `Bundler` only if a bundler builds the output |
| `target` | Matches the Node version in `engines` (ES2022+ for Node 18+) | Avoids down-levelling native async/classes |
| `verbatimModuleSyntax` | `true` | Forces `import type`, keeps ESM/CJS output predictable |
| `isolatedModules` | `true` | Required by esbuild/SWC/`tsx`-style single-file transpilers |
| `skipLibCheck` | `true` | Faster builds; type errors in dependencies are not yours to fix |
| `sourceMap` | `true` | Readable stack traces in production (`node --enable-source-maps`) |

Tightening an existing project: enable one flag, fix the errors in the files the task touches, and report the rest as a count — do not rewrite the codebase unasked.

## Module system

- New services: ESM (`"type": "module"`) with `NodeNext`; relative imports carry the `.js` extension.
- Existing CommonJS projects stay CommonJS unless the user asks to migrate — the move touches every import and some dependencies.
- Running TS directly in development: whatever the project uses (`tsx`, `ts-node`, Node's built-in type stripping on current versions). Production runs compiled JS or a type-stripping-safe build; type-check separately with `tsc --noEmit` in CI.

## Type patterns that prevent bugs

- **Infer types from schemas** (`z.infer<typeof Schema>`): one source of truth for the runtime check and the static type.
- **`unknown` at boundaries**: `JSON.parse`, `catch (e)`, third-party responses, queue payloads are `unknown` until a schema or guard narrows them.
- **Discriminated unions** for states: `{ status: 'paid'; paidAt: Date } | { status: 'pending' }` makes impossible combinations uncompilable; switch with an exhaustive `never` check.
- **Branded ids** (`type OrderId = string & { readonly __brand: 'OrderId' }`) where mixing two id kinds is a real risk; not by default.
- **`readonly`** on injected dependencies and on model properties the code must not mutate.
- **`satisfies`** to check a literal against a type without widening it (config maps, route tables).
- **Explicit return types** on exported service and repository methods — they are the contract, and they keep inference from leaking ORM types upward.
- **`as` is a claim, not a check**: allowed after a runtime check that TS cannot follow, never instead of one.

## What to avoid

| Avoid | Instead |
|---|---|
| `any` | `unknown` + narrowing; generics |
| `enum` (runtime object, odd semantics) | String literal unions or `as const` objects — unless the project uses enums consistently |
| `namespace` | ES modules |
| Non-null `!` on data from outside | Check and throw a domain error |
| `@ts-ignore` | `@ts-expect-error` with a one-line reason, or fix the type |
| Barrel `index.ts` everywhere | Direct imports; barrels slow tooling and create cycles |

## Linting

If ESLint with `typescript-eslint` is present, the type-aware rules worth enabling are `no-floating-promises`, `no-misused-promises`, `await-thenable`, `no-unsafe-*`, `switch-exhaustiveness-check`. Do not add ESLint or Biome to a project that has neither without asking.
