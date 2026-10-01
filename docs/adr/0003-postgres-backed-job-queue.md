# 3. Postgres-backed job queue (Procrastinate)

Status: accepted · 2026-10-01

## Context
The pipeline is multi-step, retryable and must not lose or duplicate work. Enqueuing to a separate broker after a database commit creates a dual-write problem.

## Decision
Procrastinate, which stores jobs in PostgreSQL. A step commits its output and enqueues the next step in one transaction. Run state lives in domain tables; the queue only delivers. Per-tenant concurrency is handled by an admission dispatcher, not by the queue.

## Alternatives
Celery (synchronous worker model), arq (maintenance-only), Dramatiq (LGPL), Temporal (a multi-service cluster to operate).

## Consequences
No broker to run or back up. Throughput is bounded by Postgres, which is far above this workload. The queue is behind a `JobQueue` port, so a move to Temporal would change one adapter.
