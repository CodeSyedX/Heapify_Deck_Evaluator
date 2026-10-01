# 4. psycopg 3 as the database driver

Status: accepted · 2026-10-01

## Decision
SQLAlchemy async over psycopg 3, not asyncpg. Procrastinate requires psycopg 3, so one driver serves both, and psycopg behaves correctly under PgBouncer transaction pooling without workarounds.

## Consequences
Slightly lower raw throughput than asyncpg, which is irrelevant next to model call latency.
