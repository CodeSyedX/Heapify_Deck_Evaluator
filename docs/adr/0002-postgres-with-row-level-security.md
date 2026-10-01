# 2. PostgreSQL as the system of record, with row-level security for tenancy

Status: accepted · 2026-10-01

## Context
The original design used Firestore. The commercial product needs relational data (organisations, events, ledger), vector search and strong tenant isolation. Personal workspaces make every user a tenant, so tenant count is large.

## Decision
PostgreSQL 18 with pgvector is the only database. Tenancy is a shared schema with `tenant_id` on every tenant-owned table and a forced RLS policy keyed on a transaction-local setting. The runtime role cannot bypass RLS.

## Alternatives
Schema per tenant: stronger isolation by construction, but migrations and connection pooling do not survive thousands of tenants. Firestore: no joins, no transactions across the ledger, provider lock-in.

## Consequences
Isolation is enforced in the database as well as in code. A wrong policy leaks data, so a meta-test checks every tenant table and integration tests run as the runtime role. A customer that requires physical isolation gets a dedicated deployment.
