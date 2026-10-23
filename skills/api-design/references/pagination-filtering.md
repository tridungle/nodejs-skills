# Pagination, filtering, sorting

Load when designing or reviewing a list endpoint.

## Every list is paginated

Even a list that is small today: adding pagination later is a breaking change. Default page size around 20, hard maximum around 100; a request above the maximum is clamped or rejected with 400 — choose once.

## Cursor vs offset

| | Cursor (keyset) | Offset |
|---|---|---|
| Request | `?limit=20&cursor=<opaque>` | `?limit=20&offset=40` or `?page=3&pageSize=20` |
| Cost on deep pages | Constant (index seek) | Grows with offset (rows are scanned and skipped) |
| Stable when rows are inserted | Yes | No — items shift, duplicates and gaps appear |
| Jump to page N | No | Yes |
| Total count | Usually omitted | Often expected |
| Use when | Feeds, large or growing tables, infinite scroll, sync | Small bounded sets (under roughly 10k rows), admin tables needing page numbers |

Default to cursor for new public endpoints.

## Cursor rules

- The cursor is opaque to clients: base64url-encode the sort key values of the last item (e.g. `createdAt` + `id`). Clients must not parse it.
- The sort must be total: always append a unique tie-breaker (`id`) to the sort key, or items with equal sort values are skipped or repeated.
- A cursor is bound to its filter and sort; reject a cursor used with different parameters (400) rather than returning wrong pages.
- An index must cover the filter + sort columns in order.

## Response shape

```json
{
  "data": [ { "id": "…" } ],
  "page": { "nextCursor": "<opaque or null>", "hasMore": true, "limit": 20 }
}
```

Offset variant: `"page": { "offset": 40, "limit": 20, "total": 1234 }`. Return `total` only when the client needs it; `COUNT(*)` on large filtered tables is often the slowest part of the request.

A `Link` header (`rel="next"`) may be added for clients that use it; the body remains the source of truth.

## Filtering

- Simple equality as plain params: `?status=active&customerId=…`.
- Ranges with a consistent operator convention, chosen once: suffixes (`createdAfter`, `priceMin`) or brackets (`price[gte]=10`). Suffixes are easier to validate and document.
- Multiple values: repeated params (`?status=active&status=paused`) or comma-separated (`?status=active,paused`) — one convention for the whole API.
- Every filterable field is allow-listed and validated; unknown filter params return 400 rather than being silently ignored (a typo otherwise returns the unfiltered list).
- Full-text search as a separate `q` param with its own limits.

## Sorting

- `?sort=createdAt` ascending, `?sort=-createdAt` descending; multiple keys comma-separated.
- Allow-list sortable fields (they must be indexed); reject others with 400.
- Document the default order; never leave it to the database.

## Sparse fields and expansion

- `?fields=id,name,status` only when payloads are large and clients demonstrably need it.
- `?expand=customer` (embed related resource) with an allow-list and a depth limit of one; each expansion is a query to budget for.
- Neither is needed by default — add when a client asks.

## Checks

- Request the maximum page size + 1 and confirm it is clamped or rejected.
- Insert a row between two cursor page requests and confirm no item repeats or disappears.
- Sort by a non-unique field and page through; every item appears exactly once.
- Pass an unknown filter and an unknown sort field; both must fail with 400.
