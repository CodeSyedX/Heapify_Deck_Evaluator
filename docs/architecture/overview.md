# Architecture overview

Status: accepted · 2026-10-01. Decisions are recorded individually in [docs/adr](../adr). Research behind them is in [docs/research](../research).

## System

```
Browser ──► web (Next.js) ──► api (FastAPI) ──► PostgreSQL + pgvector   system of record, job queue
   │             │                 │       ├──► S3-compatible storage   decks, slide images, exports
   │             └ sign-in (IdP)   │       └──► Valkey                  rate limits, progress hints
   └── direct upload to storage ───┘
                                worker (Procrastinate) ──► LLM providers, embedding model, ClamAV
```

- **web** renders the UI and hosts sign-in. It contains no business logic and calls the API through a generated client.
- **api** and **worker** are two thin entry points over one Python package, `deck_core`. The API handles requests; the worker runs the evaluation pipeline.
- **PostgreSQL** holds all state, including the job queue. Losing Valkey loses no work.

Everything runs locally under Docker Compose and uses only open protocols (Postgres, S3, OIDC, OTLP), so the deployment target is the team's choice.

## Code organisation

A modular monolith: bounded contexts first, layers inside each.

```
packages/py/core/src/deck_core/
  shared_kernel/     ids, errors, clock, pagination
  platform/          db and unit of work, jobs, storage, llm, embeddings, audit, observability, settings
  identity/          users, external identities, principals
  tenancy/           tenants, memberships, roles and permissions
  events/            competitions, rubrics and rubric versions
  submissions/       submissions, uploads
  evaluation/        deck parsing, integrity checks, scoring, pipeline runs, results, overrides
  originality/       embeddings and within-event similarity
  billing/           plans, credit ledger, reservations
```

Each context has:

| Layer | Contains | May import |
|---|---|---|
| `domain/` | Entities, value objects, domain services, repository protocols | `shared_kernel` only |
| `application/` | Use cases, permission checks, ports for external services | `domain`, `shared_kernel`, `platform` ports, other contexts' `public.py` |
| `infrastructure/` | SQLAlchemy tables, repository implementations, adapters | everything above |
| `interfaces/http`, `interfaces/jobs` | Routers and schemas, job handlers | `application` |
| `public.py` | The only module another context may import | — |

`import-linter` enforces these rules in CI. Simple contexts keep the layers thin; the full pattern earns its place in `evaluation` and `billing`.

## Multi-tenancy

A tenant is a workspace: an organisation or a user's personal workspace. Every tenant-owned table carries `tenant_id` and has a forced row-level security policy keyed on a transaction-local setting. The unit of work is the only place that opens a transaction, and it will not open one without a tenant context. The runtime database role cannot bypass RLS. Repositories also filter on `tenant_id` explicitly; RLS is the backstop.

A separate privileged role exists for named cross-tenant jobs (retention, reconciliation) and is not reachable from request handlers.

## Authentication and authorisation

Authentication is delegated to an OIDC identity provider; the API verifies bearer tokens against the issuer's JWKS and maps `(issuer, subject)` to a local user. The default provider is Better Auth, hosted in the web app. Tenancy, roles, permissions and API keys belong to the backend.

Roles are named bundles of permissions defined in code: `owner`, `admin`, `judge`, `member`. Each use case declares the permission it needs. A request for another tenant's resource returns 404.

## Evaluation pipeline

Detailed in [evaluation-pipeline.md](evaluation-pipeline.md). In short: an upload creates an evaluation run; the worker executes one job per step, and each step commits its output, its progress event and the next step's job in a single transaction. Run state lives in domain tables, not in the queue. Every step is safe to run twice.

```
queued → scanning → parsing → structure_check → integrity_check → scoring → similarity → reporting → succeeded
                                                              terminals: failed, quarantined, cancelled
```

## Credits

One credit is one deck evaluated against one rubric. Credits are reserved when a run is created, captured when it succeeds and released when it fails. The ledger is append-only with unique idempotency keys; a balance row is updated under lock in the same transaction. Payment providers are a later adapter and are never the source of truth for entitlements.

## Cross-cutting

| Concern | Approach |
|---|---|
| Errors | Typed domain errors mapped to RFC 9457 problem responses in one place |
| Idempotency | `Idempotency-Key` on cost-incurring requests; unique run key; step primary key; content-addressed LLM call cache |
| Audit | Append-only `audit_log`, written by use cases in the same transaction as the change |
| Logging | structlog JSON with request, tenant and run ids bound; no deck content or personal data in logs |
| Tracing | OpenTelemetry, propagated from API into jobs |
| LLM accounting | Every model call recorded in `llm_calls` with tokens and computed cost |
| Configuration | Typed settings from environment variables; no secrets in the repository |

## What is deliberately not built yet

Payment provider integration, SSO, API keys, judge Q&A, calibration against human gold sets, and a hardened parsing sandbox (gVisor or nsjail). Each has a port or a documented seam; none needs a redesign to add.
