# MongoDB: document modelling

Load when designing collections and documents, deciding between embedding and referencing, adding schema validation, or writing Mongoose schemas.

## Model by access pattern

Start from the queries, not the entities: list the reads and writes each screen or endpoint performs, how often, and how much data each touches. A document should hold what is read together; data that is read or updated independently belongs in its own document.

## Embed or reference

| Embed when | Reference when |
|---|---|
| The child is always read with the parent | The child is read or updated on its own |
| The number of children is small and bounded (addresses on a user, lines on an order) | The number grows without limit (comments, events, log entries) |
| The child has no meaning outside the parent | The child is shared by many parents (a product in many orders) |
| Writes to parent and child must be atomic: a single-document write is atomic without a transaction | Duplicating it would mean updating many copies when it changes |

Middle ground: the **extended reference**: store the id plus the few fields always displayed (customer id and name on an order), and accept that those copies are updated (or deliberately left as a historical snapshot).

## Hard limits and anti-patterns

- A document cannot exceed 16 MB, and large documents are slow to read and rewrite long before that. Arrays that can grow without bound are the usual cause: move them to their own collection, or use the **bucket** pattern (one document per parent per time window or per fixed count).
- Avoid very wide documents where most reads need a few fields; split rarely used heavy fields into a separate collection.
- Avoid one collection per tenant or per day; use a field and an index. Many small collections cost memory and file handles.
- Avoid joining with `$lookup` on hot paths as a substitute for modelling; if two collections are always read together, reconsider embedding or an extended reference.

## Useful patterns

- **Computed**: store a precomputed total or counter updated on write when it is read far more often than written.
- **Attribute**: variable sets of attributes as an array of `{ k, v }` with one index, instead of many sparse fields each needing an index.
- **Schema versioning**: a `schemaVersion` field so old and new shapes coexist; code reads both while a backfill or lazy migration upgrades them (see [mongodb-operations.md](mongodb-operations.md)).
- **Time series**: use time-series collections for measurements and events when the server version supports them.

## Types and identifiers

- `_id` as `ObjectId` by default; map it to a string `id` in the repository and never expose `_id` or `__v` to API clients.
- Dates as BSON `Date` (UTC), never strings. Money as `Decimal128` or integer minor units with a currency field, never a floating-point number.
- Tenant- or owner-scoped collections carry `tenantId` / `ownerId` on every document, and it leads the compound indexes used by scoped queries.

## Validation in the database

- Add a `$jsonSchema` validator to each collection for required fields, types and allowed values. Use `validationAction: "error"`; when adding a validator to existing data, start with `validationLevel: "moderate"` (applies to inserts and to documents that already pass) and tighten after a cleanup.
- Uniqueness is a **unique index**, never a "check if exists, then insert" in code; partial unique indexes handle "unique among active records".
- Mongoose validation runs only through Mongoose and can be bypassed by other writers or by update methods without validators enabled; the database validator is the backstop.

## Mongoose schemas

- One schema per collection, in the repository layer; services receive plain domain objects, not Mongoose documents.
- Keep `strict` mode on (the default) so unknown fields are dropped, and turn on `strictQuery` so filters on undeclared fields fail instead of matching everything.
- `timestamps: true` for `createdAt` / `updatedAt`; `required`, `enum`, `min`/`max` and `maxlength` on fields that have those rules.
- Declare indexes on the schema for documentation, but create them through a controlled step in production (see [mongodb-queries.md](mongodb-queries.md)).
- Middleware (`pre`/`post` hooks) only for mechanical concerns (timestamps, normalising case). Business rules, cascading deletes and notifications live in the service where they are visible and tested.
- Virtuals and getters for presentation belong in the response mapping, not the schema.
- For reads, return plain objects (`lean()`), which skips document hydration and is much cheaper.
