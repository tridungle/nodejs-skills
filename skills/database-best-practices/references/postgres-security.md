# PostgreSQL: Roles, row-level security and data protection

Load when setting up database access for an application, isolating tenants, or reviewing database security and backups.

## Roles and privileges

- **Separate roles**: an owner/migration role that owns the schema and runs DDL, and an application role with only `SELECT`, `INSERT`, `UPDATE`, `DELETE` (and `USAGE` on sequences) on the tables it needs. Read-only consumers (reporting, analytics) get their own read-only role.
- The application role is never a superuser, never the table owner, and has no `CREATEROLE`, `CREATEDB` or `BYPASSRLS`.
- `REVOKE CREATE ON SCHEMA public FROM PUBLIC` on versions before 15 (15 and later do this by default); grant per schema explicitly.
- Set `ALTER DEFAULT PRIVILEGES` for the owner role so tables created by future migrations are granted to the application role automatically.
- Connection strings and passwords come from the secret store; TLS (`sslmode=verify-full` where the provider supports it) for connections leaving a private network.

## Row-level security for tenant isolation

RLS is a backstop under the repository's tenant filter: if a query forgets `WHERE tenant_id = …`, the database still returns nothing from other tenants.

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;  -- applies to the table owner too
CREATE POLICY tenant_isolation ON orders
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

- Set the tenant **per transaction**: `SELECT set_config('app.tenant_id', $1, true)` (the `true` makes it transaction-local, like `SET LOCAL`). Session-level settings leak between requests through a connection pool.
- The repository or a transaction helper sets it at the start of every transaction from the authenticated principal, never from request input.
- `current_setting('app.tenant_id', true)` returns `NULL` when unset; with the policy above, unset means no rows, which is the safe failure.
- Policies must cover `INSERT` and `UPDATE` with `WITH CHECK`, or rows can be written into another tenant.
- Index `tenant_id` (leading column) on every RLS table; the policy adds that predicate to every query.
- Test: with tenant A set, selecting, updating and inserting tenant B's rows all fail or return nothing; with no tenant set, nothing is returned.
- Migrations and admin jobs that legitimately cross tenants run as a role with `BYPASSRLS` (or the owner without `FORCE`), never the application role.

## Sensitive data

- Store only what is needed; separate highly sensitive columns (government ids, health data) into their own table with tighter grants.
- Passwords are hashed in the application (argon2/bcrypt), never stored reversibly; never use `pgcrypto` hashing with a fast algorithm for passwords.
- Field-level encryption in the application for data that must stay unreadable to database operators; keys live outside the database.
- Logs: `log_statement = 'all'` writes parameters, including personal data, into server logs. Prefer `pg_stat_statements` and slow-query logging with parameter logging reviewed.
- Test and development databases use invented or properly anonymised data, never a raw production copy.

## Auditing

- Application-level audit table (who, what, when, before/after summary) written by the service in the same transaction as the change, when the business needs an audit trail.
- Trigger-based or extension-based (`pgaudit`) auditing when compliance requires database-level evidence; ask before enabling.

## Backups and recovery

- Point-in-time recovery (base backups + WAL archiving, or the managed service's PITR) with a retention period that matches the business requirement.
- A backup is proven only by a restore: schedule periodic restore tests into a scratch instance and check row counts and application smoke tests.
- `pg_dump` is for logical exports and migrations between versions, not the primary backup of a large, busy database.
- Know the recovery time and data-loss window you can actually achieve, and write them down.

## Checks

- Application role: `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = '<app role>'` returns false for both.
- No table owned by the application role.
- RLS tables have both `relrowsecurity` and `relforcerowsecurity` set when owner access must be restricted.
- Tenant context is set with transaction scope, not session scope.
- The last restore test date is known.
