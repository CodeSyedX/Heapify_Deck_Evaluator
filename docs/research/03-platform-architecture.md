# 03 — Platform Architecture and Toolchain Research

- **Date of research:** 2026-10-01
- **Scope:** platform architecture and toolchain for the commercial, multi-tenant, cloud-portable Deck Evaluator.
- **Method:** versions were read from the PyPI / npm registry JSON APIs and official docs on the research date. Regulatory and vendor facts come from the cited pages.
- **Confidence markers:** `[V]` verified against a primary source on the research date; `[S]` taken from secondary sources (blogs, search summaries) and plausible but not checked against the primary text; `[U]` unverified — treat as an assumption to confirm before relying on it.
- **Not legal advice:** section 10 is an engineering reading of the DPDP Act/Rules and GDPR. Have counsel confirm before launch.

---

## Recommended stack

| Component | Choice | Version (2026-10-01) | One-line reason |
|---|---|---|---|
| Language (backend) | Python | **3.14.x** (3.14.8) — not 3.13, not 3.15 | 3.14 is a year old and in bugfix support until 2030; 3.15.0 is due today and too new for wheels |
| Web framework | FastAPI | 0.142.x | De-facto async API framework; native SSE (`fastapi.sse`) since 0.135 |
| Validation / settings | Pydantic v2 + pydantic-settings | 2.13.x | Required by FastAPI; fast, strict mode available |
| ORM | SQLAlchemy async | **2.1.x** (2.1.1) | Current line; needs `sqlalchemy[asyncio]` extra (greenlet no longer default) |
| DB driver | **psycopg 3** (not asyncpg) | 3.3.x | One driver shared with the job queue; friendlier to PgBouncer; asyncpg 0.31 is the alternative |
| Migrations | Alembic | 1.20.x | Standard; async template; CI drift check |
| Database | PostgreSQL + pgvector | PG **18.x** (18.6); pgvector ext 0.8.x; `pgvector` py 0.5.0 | Single system of record; iterative index scans make tenant-filtered ANN usable |
| Tenancy | Shared schema, `tenant_id` + RLS (`FORCE`), `set_config(..., true)` per transaction | — | One schema to migrate; DB-enforced isolation as defence in depth |
| Background jobs | **Procrastinate** (Postgres-based) | 3.10.0 | Transactional enqueue in the same DB, async-native, locks, retries; no broker to run |
| Cache / rate limit / pub-sub | **Valkey** (Redis-compatible) | 9.1.x | BSD-licensed; Redis 8 is AGPL/SSPL/RSAL. Not on the critical path for jobs |
| Object storage | S3 API behind a port; **SeaweedFS or Garage locally (not MinIO)** | — | MinIO community edition was archived in April 2026 |
| Malware scanning | ClamAV `clamd` sidecar, INSTREAM | 1.4 LTS (1.4.6) or 1.5.4 | Only credible open-source option; scan in the pipeline's first step |
| Auth (authn) | **Better Auth** in the web app, issuing JWTs verified by the API via JWKS, behind an `IdentityProvider` port | 1.7.x | Self-hosted, MIT, email + Google now, SSO plugin later; swappable for Keycloak / WorkOS |
| Auth (authz) | Backend-owned orgs, memberships, roles, API keys; permission-based RBAC | — | Tenancy is core domain; never delegate it to the IdP |
| Realtime | **SSE** for progress and chat; no WebSockets | FastAPI native | One-way streams; works through proxies; resumable with `Last-Event-ID` |
| Billing | `BillingProvider` port; **Razorpay** adapter first, Stripe adapter later; internal append-only credit ledger | — | Stripe India is invite-only; UPI/Autopay and INR are table stakes |
| Frontend framework | Next.js App Router + React | Next **16.3.x**, React **19.3** | Current stable; Turbopack default; `proxy.ts` replaces `middleware.ts` |
| Server state | TanStack Query | 5.104 | Standard; generated `queryOptions` |
| UI | shadcn/ui (CLI v4) + Tailwind CSS | Tailwind **4.3** | Owned components; Base UI is now the shadcn default |
| Forms | react-hook-form + zod | RHF 7.89, zod **4.6** | Standard; zod schemas generated from OpenAPI |
| API client | **@hey-api/openapi-ts** (+ TanStack Query and zod plugins) | 0.99.0 (pre-1.0, pin exactly) | SDK + query options + zod from one spec; fallback: openapi-typescript 7.13 + openapi-fetch |
| JS workspace | pnpm workspaces + Turborepo | pnpm 12.8, turbo 2.11 | Standard; remote-cache optional |
| Python workspace | uv workspaces | uv 0.12.x | Single lockfile, fast, Docker-friendly |
| Lint / format | Ruff | 0.16.x | Replaces black/isort/flake8 |
| Type check (Py) | mypy strict (+ pydantic plugin) | 2.3.x | Stable and plugin-aware; pyright 1.1.414 is an equal alternative; `ty` is still beta (0.0.x) |
| Tests (Py) | pytest + pytest-asyncio + testcontainers | 9.1 / 1.4 / 4.15 | Real Postgres in tests is mandatory for RLS |
| Tests (JS) | Vitest + Playwright | 5.0 / 1.63 | Unit + E2E |
| Observability | OpenTelemetry + structlog + Sentry; Langfuse (optional, via OTel) for LLM traces | OTel SDK 1.45, structlog 26.1, sentry-sdk 2.71 | Vendor-neutral; own `llm_calls` table is the source of truth for cost |

### Where this departs from the planned direction

1. **Python 3.14, not 3.13.** 3.13 is fine but already a year behind; 3.14 has full library support. Do not adopt 3.15 yet.
2. **psycopg 3 instead of asyncpg.** The recommended job queue requires psycopg 3, so one driver serves both.
3. **Postgres-based jobs (Procrastinate) rather than a Redis-backed queue.** Redis/Valkey stays, but only for rate limiting, caching and SSE fan-out — losing it must not lose work.
4. **MinIO is no longer a safe default** for local S3. Use SeaweedFS or Garage, and keep the storage port strictly on the S3 API.
5. **Valkey rather than Redis** for licence reasons in a product the customer's team deploys themselves.
6. **Razorpay first.** Stripe cannot be assumed available to an Indian entity.

---

## 1. Backend stack versions and gotchas

| Package | Version | Requires Python | Notes |
|---|---|---|---|
| CPython | 3.14.8 (released 2026-09-30) `[V]` | — | 3.15.0 final is scheduled for 2026-10-01 and was still listed as pre-release when checked `[V]` |
| FastAPI | 0.142.2 `[V]` | >=3.10 | |
| Pydantic | 2.13.5 `[V]` | >=3.9 `[S]` | |
| SQLAlchemy | 2.1.1 `[V]` | >=3.11 | |
| asyncpg | 0.31.0 `[V]` | >=3.9 | |
| psycopg | 3.3.6 `[V]` | >=3.10 | |
| Alembic | 1.20.0 `[V]` | >=3.10 | |
| pgvector (Python) | 0.5.0 `[V]` | >=3.10 | |
| pgvector (extension) | 0.8.6 `[S]` | — | Version from a search summary; 0.8.x line is certain |
| PostgreSQL | 18.6 `[S]` | — | PG 19 is in beta and reportedly delayed `[S]` |
| uv | 0.12.21 `[V]` | — | |
| Ruff | 0.16.9 `[V]` | — | |
| mypy | 2.3.1 `[V]` | — | |
| pyright | 1.1.414 `[V]` | — | |
| ty (Astral) | 0.0.84, classified Beta `[V]` | — | "does not yet have a stable API" |
| pytest | 9.1.1 `[V]` | >=3.10 | |
| pytest-asyncio | 1.4.0 `[V]` | >=3.10 | |
| testcontainers | 4.15.0 `[V]` | >=3.10 | |

### Recommendations and gotchas

**Python.** Pin `requires-python = ">=3.14,<3.15"` and the Docker base to `python:3.14-slim`. Move to 3.15 after its first two patch releases and once every compiled dependency (psycopg binary, pydantic-core, PyMuPDF or whichever parser is chosen, greenlet) ships wheels. The free-threaded build is not needed; the pipeline is I/O-bound and CPU-heavy parsing should run in the worker process pool.

**FastAPI.** Still 0.x — pin a minor range (`>=0.142,<0.143`) and upgrade deliberately. Use `Annotated` dependencies, `lifespan` (not `on_event`), and one `APIRouter` per bounded context. SSE is built in since 0.135 (`fastapi.sse.EventSourceResponse`), with automatic 15-second keep-alive comments and `X-Accel-Buffering: no`; the `sse-starlette` dependency is no longer needed.

**Pydantic v2.** Keep API schemas (Pydantic) separate from domain entities (plain dataclasses / attrs) and ORM models. Use `model_config = ConfigDict(extra="forbid", frozen=True)` on request models. Give every schema a stable name — the OpenAPI component names become TypeScript type names.

**SQLAlchemy 2.1.** Released recently; two things bite:
- greenlet is no longer installed by default. Depend on `sqlalchemy[asyncio]` or the app fails at import. Several projects broke on the day 2.1.0 shipped for this reason.
- Minimum Python is 3.11, and the legacy `async_fallback` mode is removed.

Async rules that do not change: `expire_on_commit=False`; no implicit lazy loads (use `selectinload` / `raiseload("*")` as the default so accidental lazy loads fail loudly); one `AsyncSession` per request or per job, never shared across tasks.

**Driver: psycopg 3 over asyncpg.** asyncpg is somewhat faster on raw throughput, but:
- Procrastinate's async connector is psycopg 3 only; asyncpg is not supported. Using psycopg everywhere means one driver, one pool configuration, one set of type adapters.
- asyncpg prepares and caches every statement by name, which breaks under PgBouncer transaction pooling unless `statement_cache_size=0` and a unique `prepared_statement_name_func` are set. psycopg 3 only prepares after a threshold and can be told not to (`prepare_threshold=None`).
- pgvector registers cleanly with both.

If raw driver speed ever becomes the bottleneck (it will not before the LLM calls do), the repository layer is the only place that knows.

**Alembic.** Use the async `env.py` template. Run migrations as a separate one-shot container/job with the **owner** role, never at app start. Add `alembic check` to CI (fails if models and migrations diverge) and a test that upgrades from empty to head and downgrades one step. RLS policies, roles and grants are not autogenerated — write them as explicit `op.execute` and keep a helper (`enable_tenant_rls("table")`) so every new tenant table gets the same policy.

**pgvector.** Use the `pgvector/pgvector:pg18` image. Decide embedding dimension once (changing it means re-embedding). Use `halfvec` to halve index size if the embedding model is 1024+ dims. Use HNSW with cosine distance. With RLS or any `WHERE tenant_id = …` filter, plain HNSW can return too few rows; set `hnsw.iterative_scan = relaxed_order` (0.8+) for originality queries.

**uv workspaces.** One root `pyproject.toml` with `[tool.uv.workspace] members = ["apps/*", "packages/py/*"]`, one `uv.lock`. In Docker: copy `pyproject.toml` + `uv.lock` first, `uv sync --frozen --no-install-workspace --package <app>`, then copy source and `uv sync --frozen --package <app>` so dependency layers cache. uv is still 0.x; pin the uv version in CI and Dockerfiles.

**Ruff.** Format + lint. Start with `E,F,I,UP,B,SIM,ASYNC,S,PL,RUF,TID` and use `flake8-tidy-imports` banned-API rules (or `import-linter`, see section 12) to enforce layering.

**Type checker.** mypy 2.x in strict mode with `pydantic.mypy` plugin as the CI gate. pyright is equally defensible and is what editors (Pylance) run; choose one as the gate so there is a single source of truth. Do not gate on `ty` yet.

**pytest-asyncio 1.x.** The `event_loop` fixture was removed in 1.0. Set `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "session"` (plus `asyncio_default_test_loop_scope = "session"`) so a session-scoped engine/pool and the tests share one loop; mismatched loop scopes are the main source of "attached to a different loop" errors.

**testcontainers.** Start one Postgres container (the pgvector image) per test session, run Alembic to head, then isolate tests with a transaction-per-test rollback (`join_transaction_mode="create_savepoint"`). The default testcontainers user is a superuser and **bypasses RLS** — tests must connect as the runtime role (section 3).

---

## 2. Background job system

### Comparison

| | Celery 5.6 | Dramatiq 2.2 | arq 0.28 | Taskiq 0.13 | Procrastinate 3.10 | Temporal (SDK 1.34) |
|---|---|---|---|---|---|---|
| Broker | Redis / RabbitMQ | Redis / RabbitMQ | Redis | Redis, NATS, RabbitMQ, others | **PostgreSQL** | Temporal server + its own DB |
| asyncio-native | No (sync workers) | No | Yes | Yes | Yes | Yes |
| Transactional enqueue with domain write | No (needs outbox) | No | No | No | **Yes** (same DB) | No (needs outbox or workflow-first design) |
| Retries / backoff | Yes | Yes | Yes | Yes (middleware) | Yes, custom strategies | Yes, first-class |
| Per-key serialisation | Manual | Manual | Manual | Manual | **Locks and queueing locks** | Workflow ID |
| Multi-step orchestration | Canvas (fragile) | Pipelines | Manual | Pipelines add-on | Manual (state machine) | **Best in class** |
| Ops burden | Medium | Medium | Low | Low | **Lowest** (no new service) | High (multi-service cluster) |
| Status | Mature, heavy | Mature; **LGPL** | **Maintenance-only** | Active, 0.x | Active | Active |

Sources: PyPI metadata for each `[V]`; arq's own description states maintenance-only mode `[V]`; Procrastinate docs `[V]`. Procrastinate 3.10.0 is confirmed as the current version on PyPI and GitHub, but the two sources returned different publication dates, so its release date is `[U]`.

### Recommendation: Procrastinate

Reasons specific to this product:

- **The dual-write problem disappears for jobs.** The job row is inserted in the same Postgres transaction that creates the submission/evaluation run, so "row committed but job never enqueued" and "job runs before row is visible" cannot happen. Procrastinate documents deferring on an externally supplied connection for exactly this `[S]` — confirm the API in a spike in week one.
- **One fewer stateful service.** The founder's team deploys it; Postgres is already the system of record and already backed up.
- **Scale is modest.** Hundreds of submissions per event, each step dominated by seconds-long LLM calls. Postgres `SKIP LOCKED` queues handle thousands of jobs per second; this workload is orders of magnitude below that.
- **Async-native**, so the worker reuses the same application services, repositories and LLM clients as the API.

When to revisit: if the pipeline grows into long-lived, human-in-the-loop, multi-day workflows with signals and versioning, Temporal becomes worth its operational cost. The application layer below is written so that only the `JobQueue` adapter and the step runner change.

Rejected: **arq** (maintenance-only), **Celery** (sync model, heavy, canvas is a poor fit for async code), **Dramatiq** (LGPL and not async-native), **Taskiq** (reasonable second choice if a Redis broker is preferred, but 0.x and needs an outbox), **Temporal** (self-hosting is a multi-service cluster; overkill today).

### Pipeline state-machine pattern

The queue is a delivery mechanism. **The state lives in domain tables**, not in the queue.

```
evaluation_runs(id, tenant_id, submission_id, rubric_version_id, status, current_step,
                attempt, idempotency_key UNIQUE, started_at, finished_at, error_code)
pipeline_steps(run_id, step, status, attempt, input_hash, output_ref, started_at,
               finished_at, error, PRIMARY KEY (run_id, step))
pipeline_events(id BIGSERIAL, tenant_id, run_id, type, payload JSONB, created_at)   -- progress feed
outbox(id, tenant_id, topic, payload JSONB, created_at, published_at)               -- external side effects
```

Run states: `queued → scanning → parsing → structure_check → scoring → embedding → originality → reporting → succeeded`, with `failed`, `cancelled` and `quarantined` (malware) as terminals.

Rules:

1. **One job per step.** Each step job does: load run → check `pipeline_steps` for this step (if `succeeded`, skip) → do work → in one transaction: write output, mark step `succeeded`, append a `pipeline_events` row, advance `current_step`, and defer the next step's job. Because the defer is in the same transaction, the chain cannot break.
2. **Idempotency keys at three levels.**
   - *API*: `Idempotency-Key` header on "start evaluation", stored with a request hash; a repeat returns the original response.
   - *Run*: `idempotency_key = hash(submission_id, file_sha256, rubric_version_id)` with a unique constraint, so a double-click cannot create two runs or charge twice.
   - *Step*: `(run_id, step)` primary key; and for LLM calls, a content-addressed cache key `hash(model, prompt_version, input_hash)` so a retried step reuses the stored response instead of paying again.
3. **At-least-once is assumed.** Every step must be safe to run twice. External effects (charging credits, sending email, calling webhooks) go through the ledger's unique constraint or the outbox, never directly.
4. **Retries with backoff.** Classify errors: *transient* (429, 5xx, timeouts) → exponential backoff with jitter, bounded attempts (e.g. 5), honouring `Retry-After`; *permanent* (corrupt file, validation failure, content-policy refusal) → fail the step immediately with a user-facing error code. Procrastinate supports custom retry strategies via `BaseRetryStrategy.get_retry_decision`.
5. **Dead-letter handling.** There is no separate DLQ service; exhausted jobs end in Procrastinate's `failed` status and the run is marked `failed` with `error_code`. Provide: an admin view of failed runs, a "retry from failed step" action (re-defers that step only), an alert on failure rate, and a reaper periodic task that finds runs stuck in a non-terminal state beyond a timeout (worker crash) and re-defers or fails them.
6. **Credit handling.** Reserve credits when the run is created, capture on success, release on terminal failure (section 7).
7. **Transactional outbox** for everything that is not a Postgres write: organiser webhooks, emails, billing-provider calls, Valkey publishes. A periodic dispatcher reads unpublished rows with `FOR UPDATE SKIP LOCKED`, sends, and marks them published; consumers must dedupe on the outbox id.

### Per-tenant concurrency limits

Procrastinate locks serialise jobs sharing a lock (concurrency of exactly 1 per lock value); they do not natively express "at most N per tenant". Use **admission control** instead of trying to make the queue do it:

- Runs are created in `queued` without a job.
- A dispatcher (periodic task every few seconds, plus a trigger on run completion) admits runs per tenant while `running_count(tenant) < plan.max_concurrency`, ordered by priority then age, using `SKIP LOCKED`. Admission defers the first step.
- This also gives fairness (round-robin across tenants so one 500-deck event cannot starve everyone) and plan-based priority for free.
- Separate **provider-level** rate limiting (tokens/requests per minute per LLM key) lives in a Valkey token bucket shared by all workers.

### Progress reporting

Each step appends to `pipeline_events`. The API serves them over SSE (section 6). Because events are rows with a monotonically increasing id, a reconnecting client resumes with `Last-Event-ID` and misses nothing.

---

## 3. Multi-tenancy in Postgres

### Decision: shared schema, `tenant_id` on every tenant-owned table, RLS enforced

| | Shared schema + RLS | Schema per tenant |
|---|---|---|
| Migrations | One | N (slow, partial-failure states) |
| Thousands of tenants incl. personal workspaces | Fine | Catalog bloat, `search_path` juggling, pool-hostile |
| Cross-tenant analytics / billing | Simple, via a privileged role | Union across schemas |
| Isolation strength | Policy-enforced; a bug in a policy leaks | Stronger by construction |
| Per-tenant backup/restore, residency | Harder | Easier |

Personal workspaces make every individual user a tenant, so tenant count will be large; schema-per-tenant does not survive that. If a large institution later demands physical isolation, deploy a dedicated instance of the same codebase (the cloud-portable design makes that cheap) rather than complicating the shared one.

### How to apply RLS safely with SQLAlchemy async

**Roles**

- `app_owner` — owns tables, runs migrations. Never used at runtime.
- `app_rw` — runtime role for API and worker. `NOBYPASSRLS`, not a table owner, DML grants only.
- `app_admin` — `BYPASSRLS`, used only by named cross-tenant jobs (retention sweeper, billing aggregation, platform admin). Separate engine, separate connection string, every use audited.

**Policy template** (applied by a migration helper to every tenant table):

```sql
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON submissions
  USING      (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
```

`current_setting(..., true)` returns NULL when unset and the comparison then yields no rows — the policy **fails closed**. The `nullif(..., '')` matters: after a transaction-local setting ends, the parameter can read as an empty string on a reused connection, and `''::uuid` would raise instead of returning nothing.

**Setting the tenant** — once, at the start of each transaction:

```python
async with session.begin():
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)}
    )
    ...
```

- `SET LOCAL` cannot take bind parameters; `set_config(name, value, true)` is the parameterised equivalent and is transaction-scoped.
- Transaction-scoped means the value is discarded at COMMIT/ROLLBACK, so it cannot leak to the next user of a pooled connection. This is also the only form that is safe under PgBouncer transaction pooling.
- Implement it in **one place**: a unit-of-work / session factory that takes a `TenantContext` and refuses to open a transaction without one. Hook `after_begin` so a session that commits and begins again re-applies the setting.
- The worker does the same: each job carries `tenant_id` and opens its unit of work with it.

### Pitfalls

1. **Owner and superuser bypass.** Without `FORCE ROW LEVEL SECURITY`, or when connected as the owner/superuser, policies are silently ignored. This is the most common failure, and it hides in tests because test containers default to a superuser.
2. **Session-level `SET`** leaks across pooled connections. Only ever use the transaction-local form.
3. **Autocommit / no transaction.** A statement outside an explicit transaction runs without the setting and returns nothing (correct but confusing). Never use autocommit on the runtime engine.
4. **Views** run with the view owner's rights by default and bypass RLS. Create them `WITH (security_invoker = true)`. Same care for `SECURITY DEFINER` functions.
5. **Foreign keys and unique constraints are not filtered by RLS.** A child row can reference another tenant's parent id, and a unique violation reveals that a value exists elsewhere. Use composite keys: `UNIQUE (tenant_id, id)` on parents, `FOREIGN KEY (tenant_id, parent_id)` on children, and include `tenant_id` in every business unique constraint.
6. **Performance.** Put `tenant_id` first in composite indexes. Wrap the setting lookup so the planner evaluates it once (`(SELECT current_setting(...))` in the policy is a common optimisation) `[S]`. Check plans with `EXPLAIN` as `app_rw`.
7. **pgvector + RLS.** The tenant filter is applied after the ANN scan; enable iterative scans or queries return fewer than `k` rows.
8. **Cross-tenant originality search is a product decision, not a default.** If originality is compared across organisations, the query must run through a narrow `SECURITY DEFINER` function that returns only similarity scores and opaque ids — never another tenant's text. Default to scope = same event, then same tenant.
9. **Tables without `tenant_id`** (users, global plans, the job queue's own tables) are outside RLS. Keep job arguments to ids only — no personal data in job payloads.
10. **Users belong to many tenants.** `users` is global; `memberships(tenant_id, user_id, role)` is tenant-scoped. The active tenant comes from the request (path or header) and is validated against memberships before the context is set.
11. **Application-level filter as well.** Repositories still take `tenant_id` explicitly. RLS is the backstop, not the only line.

### Testing strategy for isolation

- **Run all tests as `app_rw`** against real Postgres (testcontainers), with migrations applied by `app_owner`.
- **Schema meta-test:** query `pg_class` / `pg_policies` and assert every table having a `tenant_id` column has `relrowsecurity` and `relforcerowsecurity` true and a `tenant_isolation` policy. A new table without RLS fails CI.
- **Two-tenant fixture:** seed tenants A and B; for every repository and every list/detail endpoint assert A cannot read, update or delete B's rows (expect 404, not 403, to avoid confirming existence).
- **No-context test:** a session without the setting sees zero rows and cannot insert.
- **Write-check test:** inserting a row with B's `tenant_id` under A's context raises.
- **Pool-leak test:** pool size 1; run a transaction as A, then one with no context; assert zero rows.
- **Worker test:** a job for A cannot load B's submission.
- **Property-style API test:** enumerate all routes from the OpenAPI spec that take an id; call each with a foreign-tenant id.

---

## 4. Authentication and authorisation

### Options

| Option | Portable / self-hostable | Email + Google | Orgs / roles | SAML / OIDC SSO | Notes |
|---|---|---|---|---|---|
| Self-implemented in FastAPI (Authlib, argon2) | Yes | Build | Build | Painful (SAML in Python) | Owning password reset, verification, OAuth, MFA, SAML is a large security surface for a small team |
| **Better Auth** (TS library) | **Yes** — runs in the Next.js app, own tables in Postgres, MIT | Yes | Plugin | SSO plugin (OIDC + SAML 2.0) | Version 1.7.7 `[V]`; Auth.js is now maintained by this team and in security-only mode |
| Auth.js / NextAuth | Yes | Yes | No | No | Maintenance mode; do not start new projects on it |
| Keycloak 26.x | **Yes** — separate JVM service | Yes | Organizations feature (supported since 26.0) | **Strongest** (brokering, SAML, OIDC) | Heavier to run and theme; standards-pure |
| Supabase Auth | Partly (self-host GoTrue) | Yes | No native orgs | SAML on paid/self-host | Pulls the design towards Supabase |
| Clerk | No (SaaS) | Yes | Yes | Yes | Best DX, most lock-in; per-MAU pricing |
| Auth0 | No (SaaS) | Yes | Yes | Yes | Expensive at B2B scale |
| WorkOS (AuthKit) | No (SaaS) | Yes | Yes | **Best enterprise SSO/SCIM** | Free to 1M MAU; about $125 per SSO connection per month `[S]` |

### Recommendation

**Split the problem:**

- **Authentication** (who is this human) is delegated to an identity provider.
- **Tenancy and authorisation** (which orgs, which role, which permissions, API keys) are **owned by the backend** in its own tables. This is core domain, it drives RLS, and it must not move when the IdP changes.

**Port in the backend:**

```python
class IdentityProvider(Protocol):
    async def verify(self, token: str) -> VerifiedIdentity: ...
    # VerifiedIdentity(issuer, subject, email, email_verified, amr, auth_time)
```

The default adapter is a **generic OIDC/JWKS verifier**: validate signature against the issuer's JWKS (cached, with rotation), `iss`, `aud`, `exp`, and pin the algorithm (EdDSA or RS256; reject `none` and HS*). Map `(issuer, subject)` to a local `users` row via `user_identities`. Anything that issues standard JWTs can sit behind this.

**Default IdP: Better Auth inside `apps/web`**, with email + password (verification required), Google, and its JWT/JWKS plugin issuing short-lived (about 15 min) access tokens for the API. The web app holds the session in an HttpOnly, Secure, SameSite=Lax cookie; server components and route handlers attach the bearer token when calling the API. Add the SSO plugin when the first institution asks for SAML/OIDC.

- **Do not use Better Auth's organization plugin.** Two sources of truth for membership is the failure mode to avoid. Its auth tables live in a separate `auth` schema of the same database; the API never reads them.
- **Swap paths, unchanged backend:** Keycloak (self-hosted, if an institution's security review wants a dedicated IdP or the SSO plugin proves immature) or WorkOS (if the team would rather pay per connection than operate SAML).
- **Honest caveat:** this puts security-critical code in the web tier and makes the web app a required component for login. If the team wants the API to be fully standalone, choose Keycloak from the start; the port is the same.
- Better Auth's SSO plugin maturity for Indian university IdPs (often Shibboleth/ADFS, sometimes Google Workspace) is `[U]` — spike it before promising SSO to a customer.

**SSO for institutions (later):** per-tenant `sso_connections(tenant_id, protocol, domain, config)`, verified-domain ownership, home-realm discovery by email domain, just-in-time provisioning into the tenant with a default role, and an "enforce SSO" tenant setting.

**API keys (organiser integrations):** backend-owned.

- Format `dek_live_<prefix>_<secret>`; show once; store `prefix` plus SHA-256 of the secret (high-entropy secrets do not need a slow hash); constant-time compare.
- Key belongs to a tenant, carries scopes (subset of permissions), optional expiry, `last_used_at`, created-by, revocation.
- Separate rate-limit bucket; every use lands in the audit log.
- Resolves to the same `Principal` type as a user session so the authorisation code has one path.

### RBAC model

Permission-based, with roles as named bundles:

```
Principal = User(user_id) | ApiKey(key_id)        + tenant_id + permissions
roles:   owner > admin (organiser) > judge > member (student)
scope:   tenant-level membership role, plus optional event-level assignment
         (event_roles: judge on event X; organiser on event Y)
```

- Permissions are strings such as `event:create`, `rubric:edit`, `submission:read:any`, `submission:read:own`, `evaluation:run`, `billing:manage`, `member:invite`, `export:create`, `apikey:manage`.
- The role → permission map is code (versioned, testable), not database rows, until a customer needs custom roles.
- Enforcement in the **application layer** (each use case declares the permission it needs); FastAPI dependencies only build the `Principal`. Ownership checks ("own submission", "assigned judge") are policy functions next to the use case.
- A personal workspace is a tenant with one `owner` membership — no special cases in authorisation.
- A platform-staff role exists outside tenant roles, uses the `app_admin` path, requires a reason, and is always audited.

---

## 5. File upload architecture

**Flow**

1. `POST /submissions/{id}/uploads` — authenticated; server checks permission, plan quota, declared size (≤ 50 MB) and declared type (pdf / pptx). Creates an `uploads` row (`pending`) and returns a presigned upload target with a short expiry (5–10 min).
2. Browser uploads **directly to object storage**. The API never proxies file bytes.
3. `POST /uploads/{id}/complete` — server `HEAD`s the object, verifies actual size and checksum, marks `uploaded`, and creates the evaluation run. Do not rely on bucket event notifications; they differ per provider.
4. First pipeline step: **scan and sniff**, then promote from quarantine.

**Presigned POST vs PUT.** A presigned POST policy can enforce `content-length-range`, key prefix and content type at the storage layer; a bare presigned PUT pins only bucket, key and expiry `[S]`. But POST-policy support varies across S3-compatible stores (Cloudflare R2 has historically not supported it `[U]`). For portability:

- Make it a capability of the `ObjectStorage` adapter: use POST policy where supported, otherwise presigned PUT with signed `Content-Type` / `Content-Length`.
- **Never trust the upload step alone.** Always verify size on completion, land uploads in a quarantine prefix with a short lifecycle expiry, and delete oversize objects. That makes the design safe on any backend.
- 50 MB does not need multipart; a single request is simpler. Add multipart only if limits rise.

**Validation (in the worker, on the stored bytes)**

- Magic-byte sniffing: `%PDF-` for PDF; PPTX is a ZIP that must contain `[Content_Types].xml` and `ppt/presentation.xml`. The client's `Content-Type` and filename are hints only.
- Zip-bomb guards for PPTX: cap entry count, total uncompressed size and compression ratio before parsing.
- Reject macro-enabled formats (`.pptm`), encrypted files, and PDFs over a page limit.
- Parse in a sandboxed subprocess with CPU, memory and time limits; parsers are the main attack surface.
- Store the SHA-256; it feeds idempotency and duplicate detection.

**Malware scanning.** ClamAV `clamd` as a sidecar container (official `clamav/clamav` image), called over TCP with `INSTREAM`. Set `StreamMaxLength` above the upload limit (default is lower than 50 MB `[S]`), keep `freshclam` updating signatures, give it about 1.5–2 GB RAM `[S]`. On a hit: mark the upload `quarantined`, delete or retain per policy, notify the uploader, audit-log it. Behind a `MalwareScanner` port so a cloud scanning service can replace it. ClamAV 1.4 is the LTS line (1.4.6); 1.5.4 is the latest feature release.

**Keys and tenancy**

```
{env}/tenants/{tenant_id}/submissions/{submission_id}/original/{upload_id}.{ext}
{env}/tenants/{tenant_id}/submissions/{submission_id}/derived/{artifact}       # slide images, extracted text
{env}/tenants/{tenant_id}/exports/{export_id}.zip
{env}/quarantine/{upload_id}
```

- Keys are generated server-side; never include the user's filename (store it in the DB).
- Per-tenant prefixes make deletion, export, and (later) per-tenant encryption keys or bucket policies straightforward.
- Bucket is private; downloads are short-lived presigned GETs issued after an authorisation check, with `Content-Disposition: attachment` and a safe content type. Lock CORS to the app origin.

**Retention and deletion**

- Retention is a **tenant/event policy** in the DB (e.g. "delete originals N days after event close"), executed by a scheduled retention job — not only by bucket lifecycle rules, which are provider-specific and unaware of legal holds.
- Deletion is two-phase: soft-delete (tombstone, hidden immediately) → hard-delete job removes the object, all derived artefacts, embeddings, cached LLM inputs/outputs, and report content, then writes an audit record. Deleting only the original file while embeddings and extracted text remain is not deletion.
- Bucket lifecycle rules are a safety net: expire the quarantine prefix and abort incomplete multipart uploads.
- If bucket versioning is on, hard-delete must remove versions too.

**Local object storage.** MinIO's community edition went into maintenance mode in December 2025 and the repository was archived in April 2026 `[S]`. Use **SeaweedFS** (mature, active) or **Garage** (light, Rust) in Docker Compose. Whichever is chosen, an integration test must exercise presigned PUT/POST, HEAD, range GET and delete against it, because compatibility gaps are where S3 clones differ. RustFS is promising but young.

---

## 6. Realtime progress and streaming

**Decision: SSE for both pipeline progress and chat. No WebSockets.**

| | SSE | WebSockets |
|---|---|---|
| Direction | Server → client (what both features need) | Bidirectional |
| Transport | Plain HTTP; works through proxies, load balancers, HTTP/2 | Upgrade; sticky routing, separate auth handshake |
| Reconnect / resume | Built in (`Last-Event-ID`) | Hand-rolled |
| Auth | Normal cookies / headers | Custom |
| Scaling | Stateless if events are stored | Connection state |

Chat input goes up as an ordinary POST; tokens come back as an SSE stream on that response. Nothing here needs a duplex socket.

**Pipeline progress**

- `GET /evaluation-runs/{id}/events` returns `text/event-stream`. On connect, replay rows from `pipeline_events` after `Last-Event-ID`, then tail.
- Tail via Valkey pub/sub (workers publish a "run X has new events" hint; the API re-reads from Postgres) with a slow polling fallback. Postgres remains the source of truth, so a lost pub/sub message only delays an update. Postgres `LISTEN/NOTIFY` is an alternative that removes the Valkey dependency but needs a dedicated non-pooled connection.
- Dashboards with hundreds of submissions should use **one stream per event** (`/events/{id}/stream`), not one per submission; browsers cap HTTP/1.1 connections at six per origin.
- Always also expose plain `GET` status endpoints. SSE is an enhancement; TanStack Query polling is the fallback.

**Chat streaming**

- `POST /qa/sessions/{id}/messages` with `Accept: text/event-stream`; FastAPI's native `EventSourceResponse` works with POST. Event types: `token`, `citation`, `usage`, `done`, `error`.
- Browser `EventSource` is GET-only and cannot set headers, so consume with `fetch` + `ReadableStream` (or `@microsoft/fetch-event-source`).
- Persist the user message before streaming and the assistant message (with token usage) at the end. Detect client disconnect and cancel the upstream LLM call to stop spending.
- Rate-limit and meter chat per tenant like any other LLM use.

**Next.js integration**

- Prefer the browser talking **directly to the API origin** for streams (same registrable domain, e.g. `app.` and `api.`, so cookies or a bearer token work). This avoids buffering and timeouts in an intermediate hop.
- If proxying through a Next.js Route Handler, return the upstream `ReadableStream` untouched, `export const dynamic = "force-dynamic"`, Node runtime, and no compression on that route.
- Reverse proxy: disable buffering (`X-Accel-Buffering: no` is set by FastAPI), raise idle/read timeouts above the keep-alive interval (15 s), and prefer HTTP/2.

---

## 7. Billing

### Provider facts

- **Stripe India is invite-only.** New Indian businesses cannot self-sign-up and must request an invite; Stripe states it supports "a select number of businesses, with a focus on international expansion" `[V]`. RBI rules effective 2026-01-01 also require video KYC for new onboarding `[S]`. Stripe did add UPI as a payment method (API changelog 2026-03-25), with recurring UPI capped at ₹15,000 `[S]`, but availability to a given Indian account is `[U]`.
- **Stripe usage billing** is meter-based; the legacy usage-records API was removed in API version 2025-03-31 `[S]`.
- **Razorpay** supports UPI, UPI Autopay, cards, netbanking, Subscriptions (plans, add-ons), invoices, and international cards in 100+ currencies; it holds the cross-border payment-aggregator licence `[S]`. It is a gateway, **not a merchant of record** — tax obligations on foreign sales remain with the seller.
- **RBI e-mandate rules:** recurring debits up to ₹15,000 need no extra authentication after mandate setup; above that, each debit needs it. A 24-hour pre-debit notification is mandatory `[S]`. Annual institutional plans will exceed this, so support **invoice + bank transfer / payment link** for larger customers, not only auto-debit.
- **GST:** 18% on SaaS `[U — confirm with accountant]`; invoices need supplier and (for B2B) customer GSTIN, SAC code, place of supply, and CGST/SGST vs IGST split. E-invoicing (IRN) is mandatory above ₹5 crore aggregate turnover `[S]` — not a day-one concern, but the invoice model should be able to carry an IRN.
- Webhooks from both providers are at-least-once. Razorpay sends a unique `x-razorpay-event-id` header and an HMAC-SHA256 `X-Razorpay-Signature` over the **raw body** `[S]`. Stripe uses `event.id` and a `Stripe-Signature` header.

### Recommendation

**Razorpay first, Stripe as a second adapter** once there is a non-Indian entity or an invite. Keep the provider as a payment rail only; **entitlements and usage live in our database.**

```python
class BillingProvider(Protocol):
    async def create_customer(self, tenant: TenantBillingProfile) -> ProviderRef: ...
    async def create_checkout(self, tenant_id, item: PlanOrCreditPack, idempotency_key) -> CheckoutSession: ...
    async def create_subscription(...); async def cancel_subscription(...)
    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> ProviderEvent: ...
    def to_domain_events(self, event: ProviderEvent) -> list[BillingEvent]: ...
```

**Do not use provider-side usage metering as the source of truth.** Model usage as **prepaid credits**: a plan grants N credits per period; packs top up. This is portable (Razorpay has no direct equivalent of Stripe meters), suits Indian buyers who prefer prepaid, and avoids surprise invoices. Postpaid overage can be added later as an end-of-period invoice computed from our ledger.

### Credit ledger

Append-only, never updated or deleted:

```
credit_ledger(id, tenant_id, entry_type, amount INT,        -- signed
              bucket_id, reference_type, reference_id,
              idempotency_key, created_at, created_by,
              UNIQUE (tenant_id, idempotency_key))
credit_buckets(id, tenant_id, source [plan|pack|promo|manual], granted, expires_at)
credit_reservations(id, tenant_id, run_id UNIQUE, amount, status [held|captured|released], expires_at)
```

- Entry types: `grant`, `purchase`, `reserve`, `capture`, `release`, `expire`, `refund`, `adjustment`.
- **Balance = SUM(amount)**; a cached `tenant_credit_balance` row is updated in the same transaction under `SELECT … FOR UPDATE` on that row, which serialises concurrent spends and prevents going negative. A nightly job reconciles cache against the ledger.
- **Reserve → capture/release** around each evaluation run; the unique `run_id` makes it idempotent under retries. Expired reservations are released by a sweeper.
- Buckets with expiry are consumed earliest-expiry-first.
- Full double-entry (debits and credits across accounts) is more than needed here. A single-sided append-only ledger with typed entries and unique idempotency keys gives the same auditability for one asset type. If real money balances (wallets, payouts) ever appear, move to double-entry then.
- Manual adjustments require a reason and actor and appear in the audit log.

### Webhook idempotency

1. Read the **raw body**; verify the signature before parsing; reject on failure.
2. `INSERT INTO billing_webhook_events(provider, event_id, type, payload, received_at) ON CONFLICT (provider, event_id) DO NOTHING`. If nothing was inserted, return 200 — duplicate.
3. Return 200 quickly; process in a job (deferred in the same transaction as the insert).
4. Handlers are idempotent and order-tolerant: on any subscription/payment event, **re-fetch the current object from the provider** and reconcile, rather than trusting event order.
5. Ledger writes use `idempotency_key = "{provider}:{payment_id}"`, so a replay cannot double-grant.
6. A daily reconciliation job compares provider payments with ledger purchases.
7. Never grant credits from the browser redirect; only from the verified webhook (or a verified server-side fetch).

**Invoices.** Own `invoices` / `invoice_lines` tables with a gapless series per financial year, GSTIN fields, SAC, place of supply and tax split; generate the PDF ourselves so invoices are identical across providers. Collect the customer's GSTIN and billing state at checkout.

---

## 8. Frontend stack

| Package | Version `[V]` | Notes |
|---|---|---|
| Next.js | 16.3.8 | Node >= 20.9; Turbopack is the default bundler |
| React | 19.3.0 | |
| TypeScript | 7.0.2 (npm `latest`) | Native-compiler line. Toolchain compatibility (typescript-eslint, editor plugins, codegen) is `[U]`; if anything lags, pin 6.x |
| @tanstack/react-query | 5.104.0 | |
| Tailwind CSS | 4.3.3 | CSS-first config (`@theme`), no `tailwind.config.js` needed |
| shadcn CLI | v4 | Base UI is the default primitive library since July 2026; Radix still supported |
| react-hook-form | 7.89.0 | |
| zod | 4.6.5 | zod 4 API; check resolver compatibility |
| @hey-api/openapi-ts | 0.99.0 | **Requires Node >= 22.18**; pre-1.0 |
| openapi-typescript / openapi-fetch | 7.13.0 / 0.17.0 | Fallback |
| orval | 8.39.0 | Alternative (generates hooks) |
| pnpm | 12.8.1 | |
| turbo | 2.11.5 | |
| Vitest | 5.0.3 | |
| @playwright/test | 1.63.0 | |

Use **Node 24 LTS** for tooling and runtime (satisfies hey-api's requirement) `[U — confirm current LTS line]`.

### Next.js 16 points that affect design

- `middleware.ts` is deprecated in favour of **`proxy.ts`** (Node runtime). Use it only for cheap redirects (unauthenticated → login); real authorisation happens in the API.
- `params` and `searchParams` are async.
- Caching is opt-in via Cache Components / `"use cache"`. For this app nearly everything is per-user and per-tenant: **default to dynamic rendering and do not cache authenticated data in the Next.js layer.** A cached tenant page is a cross-tenant leak waiting to happen.
- React Compiler is stable; enable it and skip manual `useMemo`/`useCallback`.
- **Portability:** build with `output: "standalone"` and ship a Node container. Avoid Vercel-only features (Edge runtime, ISR tied to their cache, image optimisation assumptions). If multiple web replicas are run, any use of the Next.js data cache needs a shared cache handler — another reason to avoid it.

### App Router patterns

- **The FastAPI backend is the only API.** No business logic in Route Handlers or Server Actions. The web app is a thin BFF: auth routes, optional stream passthrough, and nothing else.
- Server Components fetch initial data with the generated client (forwarding the access token) and hydrate TanStack Query (`prefetchQuery` + `HydrationBoundary`). Client Components own interactivity, mutations and polling/SSE.
- Mutations go through TanStack Query calling the API directly, not Server Actions — keeps one contract (OpenAPI) and one error model.
- Route structure: `app/(marketing)`, `app/(auth)`, `app/(app)/[tenantSlug]/…` with the tenant in the URL so links are shareable and tenant switching is explicit.
- Feature folders (`features/events`, `features/submissions`, …) hold components, hooks and query-option wrappers; `app/` only composes them.
- Include the tenant id in every query key; clear the query cache on tenant switch and sign-out.

### API client generation

**@hey-api/openapi-ts** with the TanStack Query plugin (generates `queryOptions` / `mutationOptions` and key helpers rather than hooks) and the zod plugin (form validation that cannot drift from the API). Pin the exact version — it is pre-1.0 and has frequent breaking changes.

Pipeline: FastAPI emits `openapi.json` via a script (no server needed) → committed to `packages/api-client/openapi.json` → generator runs → **CI fails if the committed spec or generated code is stale**. Set explicit `operation_id`s in FastAPI (e.g. `events_list`) so generated function names are stable.

Fallback if hey-api's churn becomes a cost: `openapi-typescript` + `openapi-fetch` (types only, tiny runtime, very stable) with hand-written query options. Orval is the choice if generated hooks and MSW mocks are preferred.

### Forms, UI, tests

- react-hook-form + zod resolver; server validation errors (RFC 9457 problem details with field pointers) mapped back onto fields with one helper.
- shadcn components live in `packages/ui`; Tailwind 4 theme tokens in one CSS file. Decide Base UI vs Radix at init and do not mix.
- Tables/dashboards: TanStack Table with server-side pagination, sorting and filtering — organisers will have hundreds of rows.
- Vitest + Testing Library for components and hooks; MSW for API mocking. Playwright for the critical flows (sign-up, create event, upload, watch progress, view report, judge Q&A, purchase credits) against the Docker Compose stack, plus `@axe-core/playwright` accessibility checks.

---

## 9. Observability and operations

**Tracing — OpenTelemetry (SDK 1.45).**
- Auto-instrument FastAPI, SQLAlchemy, psycopg, httpx, Redis client; export OTLP to a collector. The collector is the portability seam: the backend can be Grafana Tempo, Jaeger, SigNoz, or a vendor without code changes. Docker Compose ships a collector plus one local UI.
- **Propagate context API → worker.** Inject the W3C `traceparent` into job arguments when deferring; extract it in a worker middleware and start the job span as a child (or link). Without this the trace stops at the enqueue.
- Standard attributes on every span: `tenant.id`, `user.id` (id only), `run.id`, `submission.id`, `pipeline.step`. No personal data or document text in span attributes.

**Logging — structlog (26.1).**
- JSON to stdout; `contextvars` binding for `request_id`, `trace_id`, `span_id`, `tenant_id`, `principal_id`, `run_id`. Route stdlib and uvicorn logging through the same processors so every line has the same shape.
- A redaction processor for emails, tokens, API keys and prompt/document content. Logs are personal data under DPDP if they contain identifiers; keep them minimal and set retention deliberately (section 10).

**Errors — Sentry (sdk 2.71).** Behind a thin `ErrorReporter` port; `send_default_pii=False`; scrub request bodies; tag tenant and release. GlitchTip is a self-hostable Sentry-protocol alternative for customers who cannot send data out `[S]`.

**LLM tracing and cost accounting.**
- All model calls go through one `LLMGateway` port. It records, per call, a row in **`llm_calls`**: tenant, run, step, provider, model, prompt template id + version, input/output/cached tokens, latency, status, retry count, cost computed from a versioned price table, and request hash. This table — not a third-party tool — is the source of truth for cost per tenant, per event and per evaluation, and reconciles against credits.
- Emit OTel spans using the GenAI semantic conventions `[S — conventions' stability status not checked]`.
- **Langfuse** (self-hostable, OTel ingestion) is a good optional UI for prompt debugging and evals, but v3 self-hosting needs ClickHouse, Redis/Valkey and S3 in addition to Postgres — a heavy addition. Make it opt-in via the OTel exporter, not a dependency.
- Store prompts/responses only as long as needed for the report and debugging; they contain the deck content and fall under the retention policy.

**Health endpoints.**
- `/healthz` (liveness): process is up; no dependency checks.
- `/readyz` (readiness): DB reachable, migrations at expected head, storage reachable; Valkey optional/degraded.
- Worker: heartbeat row or file, plus queue-depth and oldest-job-age metrics. Alert on age, not just depth.
- Graceful shutdown: stop accepting, let in-flight requests and the current job step finish, then exit. Steps are idempotent, so a hard kill is also safe.

**Metrics.** OTel metrics or Prometheus: request rate/latency/errors per route, job duration per step, retries, failure rate, queue age, LLM tokens and cost, credits consumed, SSE connection count.

**Rate limiting.**
- Edge / reverse proxy: coarse per-IP limits and body-size limits.
- Application (Valkey token bucket / sliding window, atomic Lua): per-IP on auth endpoints; per-user and per-tenant on API; per-API-key with plan-based quotas; a separate tight bucket for chat and for "start evaluation". Return `429` with `Retry-After` and `RateLimit-*` headers.
- Define behaviour when Valkey is down: fail open for general API, fail closed for auth and cost-incurring endpoints.
- Plan quotas (credits, concurrency) are enforced in Postgres, not in the rate limiter.

**Audit log.** Append-only `audit_log(id, tenant_id, actor_type, actor_id, action, target_type, target_id, metadata JSONB, ip, user_agent, request_id, created_at)`.
- Written **in the same transaction** as the change it records, by the application layer (not by HTTP middleware, which cannot know intent).
- Covers: sign-in events, membership/role changes, API key lifecycle, rubric changes, score overrides by judges, exports, downloads of submissions, deletions, consent changes, billing changes, platform-staff access.
- The runtime role gets `INSERT` and `SELECT` only — no `UPDATE`/`DELETE`. Partition by month for retention.
- Exposed to tenant owners as a filterable, exportable view.

---

## 10. Compliance

### India — DPDP Act 2023 and DPDP Rules 2025

**Status.** The Digital Personal Data Protection Rules, 2025 were notified on 13 November 2025 with staggered commencement `[S]`:

| Phase | Date | What |
|---|---|---|
| 1 | 13 Nov 2025 | Data Protection Board established; definitions and procedural provisions |
| 2 | 13 Nov 2026 | Consent Manager registration framework |
| 3 | **13 May 2027** | Substantive obligations: notice, consent, security safeguards, breach reporting, children's data, data principal rights, retention/erasure |

As of today the substantive obligations are about seven months away. A product launching now should be built compliant from the start. Confirm dates and rule numbers against the gazette text; the citations below are from secondary summaries.

**Roles — this needs a decision and a contract.**
- For **organisation tenants**, the college/organiser decides why and how student data is processed and is the *Data Fiduciary*; we are their *Data Processor* and need a written contract (a DPA) with each tenant. The fiduciary remains responsible for the processor's compliance.
- For **personal workspaces**, and for account/billing data generally, **we are the Data Fiduciary**.
- LLM providers, email, payments, error tracking and hosting are our processors/sub-processors: maintain a list, sign DPAs, and use API terms that exclude training on customer data.

**Obligations relevant here**

| Area | Obligation | Source |
|---|---|---|
| Notice | Standalone, plain-language notice at or before collection: itemised data, specific purposes, how to withdraw consent, how to exercise rights, how to complain to the Board | Act s.5; Rule 3 `[S]` |
| Consent | Free, specific, informed, unambiguous, by clear affirmative action; limited to the stated purpose; **withdrawal as easy as giving** | Act s.6 |
| Security | Reasonable safeguards: encryption, access control, logging/monitoring, backups, processor contracts | Act s.8(5); Rule 6 `[S]` |
| Log retention | Retain processing logs for **at least one year** for breach detection and investigation | Rules 6 / 8(3) `[S — sub-rule numbering differs between sources]` |
| Breach | Inform affected individuals and the Board **without delay**; detailed report to the Board **within 72 hours** of becoming aware | Rule 7 `[S]` |
| Retention | Erase when the purpose is served or consent is withdrawn, unless law requires retention; the fixed inactivity periods and 48-hour pre-erasure notice in the Third Schedule apply to large e-commerce, gaming and social platforms, not to this product | Act s.8(7); Rule 8 `[S]` |
| Rights | Access/summary, correction, completion, erasure, nomination, grievance redressal; publish how to exercise them | Act ss.11–14; Rule 14 `[S]` |
| Grievance | Publish a contact and a response period **not exceeding 90 days** | Rule 14 `[S]` |
| Children | A child is anyone **under 18**. Verifiable parental consent before processing; **no tracking, behavioural monitoring or targeted advertising** directed at children | Act s.9; Rule 10 `[S]` |
| Cross-border | Permitted except to countries the government restricts by notification | Act s.16 — current restricted list `[U]` |
| Penalties | Up to ₹250 crore (security failure); up to ₹200 crore (breach notification, children's obligations) | Act Schedule `[S]` |

**Children's data is the sharpest issue for this product.** First-year college students and school hackathon participants are frequently 17. The Fourth Schedule exempts educational institutions from parental-consent and monitoring restrictions only for narrowly defined purposes (educational activities, safety) `[S]`; whether that exemption extends to a third-party SaaS acting for the institution, or to a non-institution hackathon organiser, is a legal question — `[U]`, get counsel's view.

Engineering position until counsel says otherwise:
- Age gate at sign-up (date of birth or an 18+ declaration). **Personal workspaces are 18+ only.**
- Under-18 participation only through an organisation tenant that attests it has obtained verifiable parental consent, recorded per event; provide a parental-consent capture flow as a later feature.
- No behavioural analytics, ad pixels or profiling for accounts flagged as minors. Simplest safe default: no third-party tracking for anyone inside the app.
- Collect the minimum from students: name, email, institution, team. No phone or ID numbers unless an organiser justifies it.

**Significant Data Fiduciary** duties (DPO in India, DPIA, audits) apply only if the government designates us; unlikely at this scale, but DPIA-style documentation is cheap and useful for selling to institutions.

### GDPR basics (for later)

- **Roles** map directly: controller ≈ fiduciary, processor ≈ processor. Article 28 DPA with tenants; sub-processor list with change notification.
- **Lawful basis** per purpose (contract for the service; legitimate interests for security; consent for optional things). Do not lean on consent where contract fits.
- **Rights:** access, rectification, erasure, restriction, portability, objection — respond within one month.
- **Breach:** notify the supervisory authority within 72 hours; individuals when high risk.
- **Transfers:** SCCs (and transfer assessments) for data leaving the EEA; an India-hosted deployment serving EU users, and US-based LLM providers, both need them. Offer an EU-region deployment — the portable design supports it.
- **Article 22 / automated decisions:** LLM scoring that determines who advances in a competition is close to automated decision-making with significant effect. Design scores as **decision support with a human judge making the decision**, show the rubric and reasoning, and provide a way to contest. This is good product design regardless of jurisdiction.
- **Records of processing, DPIA** for large-scale profiling, privacy by design and default; EU representative if targeting the EU without an establishment.
- Children: digital consent age is 13–16 depending on member state, lower than India's 18 — key age logic on a per-jurisdiction setting, not a constant.

### What this means for the data model and code

| Need | Concretely |
|---|---|
| Notices | `policy_documents(id, kind, version, locale, content_hash, effective_at)` — versioned privacy notice, terms, DPA |
| Consent records | `consent_records(id, tenant_id, user_id, purpose, policy_document_id, status [granted\|withdrawn], method, ip, user_agent, granted_at, withdrawn_at, guardian_ref)` — append-only; one row per purpose per change. Purposes are an enum (`service`, `originality_index`, `marketing_email`, `product_analytics`, …) |
| Purpose limitation | Storing a deck's embedding for future originality comparison against *other* people's decks is a separate purpose from evaluating it; make it explicit in the notice and a tenant/event-level setting |
| Age | `users.age_band` or `is_minor` + `declared_at`; event-level `minor_participants_allowed` with organiser attestation record |
| Rights requests | `data_subject_requests(id, tenant_id, user_id, type [access\|export\|correction\|erasure\|grievance], status, due_at, completed_at, handled_by)` with due-date alerts |
| Export | `POST /me/data-export` → async job → machine-readable archive (JSON + original files) in the exports prefix → short-lived download link → auto-expiry. Tenant-level export for organisers (portability, offboarding) |
| Erasure | `DELETE /me` and tenant deletion → soft delete → hard-delete job that cascades to objects, derived artefacts, embeddings, LLM call payloads and chat history; anonymise rather than delete rows that must be kept (ledger, invoices, audit log) by replacing the user reference with a tombstone id |
| Processor erasure | When acting as processor, erasure requests from students are routed to the tenant; provide organisers the tools to execute them |
| Retention | `retention_policies(tenant_id, data_class, retain_days)` + defaults; a nightly retention job (privileged role, audited) deletes expired submissions, artefacts, exports, chat logs, and stale invitations; every run writes a summary to the audit log |
| Logs | Application/audit logs retained at least one year (DPDP); minimise personal data in them; fixed maximum retention |
| Legal hold | `legal_holds` flag that the retention and erasure jobs respect |
| Breach readiness | Audit log, access logs, per-tenant data map, an incident runbook with the 72-hour clock, and the ability to list affected users per tenant quickly |
| Sub-processors | Published list; per-tenant setting for allowed LLM providers/regions; provider calls configured for zero data retention where offered |
| Data residency | `tenants.data_region`; India-region deployment by default (data-localisation is not generally mandated by DPDP today, but institutions will ask) |
| Encryption | TLS everywhere; storage and DB encryption at rest; application-level encryption for secrets such as SSO configs and webhook secrets |
| Grievance | Published contact, in-app form creating a `data_subject_requests` row, 90-day SLA tracked |

---

## 11. Repository layout

```
deck-evaluator/
├─ apps/
│  ├─ api/                      # FastAPI composition root (thin): app factory, routers wiring, DI, settings
│  │  ├─ src/deck_api/
│  │  ├─ tests/                 # API-level and e2e tests
│  │  ├─ Dockerfile
│  │  └─ pyproject.toml
│  ├─ worker/                   # Procrastinate app + task registration (thin); same core package
│  │  ├─ src/deck_worker/
│  │  ├─ Dockerfile
│  │  └─ pyproject.toml
│  └─ web/                      # Next.js (App Router)
│     ├─ app/  features/  lib/  e2e/
│     ├─ Dockerfile
│     └─ package.json
├─ packages/
│  ├─ py/
│  │  ├─ core/                  # deck_core: ALL domain + application + infrastructure code (see below)
│  │  └─ testing/               # shared fixtures, factories, fakes for ports
│  ├─ api-client/               # openapi.json + generated TS client (hey-api)
│  ├─ ui/                       # shadcn components, Tailwind theme
│  └─ config/                   # shared tsconfig, eslint, prettier presets
├─ db/
│  └─ migrations/               # Alembic (single history); RLS helpers; seed scripts
├─ infra/
│  ├─ compose/                  # docker-compose.yml (+ overrides): postgres, valkey, s3, clamav, otel, mailpit
│  ├─ docker/                   # shared base images, entrypoints
│  └─ deploy/                   # reference manifests (Helm/Kustomize or plain compose for a VM); env templates
├─ docs/
│  ├─ adr/                      # 0001-record-architecture-decisions.md, 0002-postgres-job-queue.md, …
│  ├─ research/
│  ├─ runbooks/                 # incident/breach, restore, rotate keys
│  └─ reference/
├─ scripts/                     # export-openapi, gen-client, dev bootstrap
├─ .github/workflows/
├─ pyproject.toml               # uv workspace root, ruff/mypy/pytest config
├─ uv.lock
├─ package.json  pnpm-workspace.yaml  turbo.json
├─ .pre-commit-config.yaml
├─ Makefile (or justfile)       # one-command dev: make up / make test / make gen
└─ README.md
```

**API and worker are two thin entrypoints over one core package.** Same image base, different command. This keeps the "modular monolith" honest: one codebase, one set of use cases, two delivery mechanisms (HTTP and jobs).

### Backend internal layout — bounded contexts first, layers inside

```
packages/py/core/src/deck_core/
├─ shared_kernel/               # ids, TenantId, Money/Credits, clock, Result/errors, domain event base, pagination
├─ platform/                    # cross-cutting infrastructure
│  ├─ db/                       # engine, session factory, unit of work with tenant context, RLS helpers
│  ├─ jobs/                     # JobQueue port + Procrastinate adapter, trace propagation
│  ├─ storage/                  # ObjectStorage port + S3 adapter
│  ├─ llm/                      # LLMGateway port + provider adapters, pricing, llm_calls recorder
│  ├─ outbox/  audit/  events/  # outbox dispatcher, audit writer, in-process event bus
│  ├─ observability/            # otel, structlog, sentry setup
│  └─ ratelimit/  cache/
├─ identity/                    # users, external identities, sessions/tokens verification, API keys
├─ tenancy/                     # tenants (orgs + personal), memberships, roles, invitations, SSO connections
├─ events/                      # competitions/"events", rubrics + versions, judge assignments
├─ submissions/                 # submissions, uploads, scanning, parsing artefacts
├─ evaluation/                  # evaluation runs, pipeline state machine, scoring, reports
├─ originality/                 # embeddings, similarity search, originality findings
├─ qa/                          # judge Q&A sessions, messages, retrieval, streaming
├─ billing/                     # plans, subscriptions, credit ledger, invoices, provider adapters, webhooks
└─ compliance/                  # consent, policy documents, DSRs, retention, export/erasure orchestration

each context:
├─ domain/                      # entities, value objects, domain services, domain events, repository PROTOCOLS
│                               #   pure Python; no FastAPI, SQLAlchemy, httpx imports
├─ application/                 # use cases (commands/queries), DTOs, permission checks, ports for external services
├─ infrastructure/              # SQLAlchemy models + mappers, repository implementations, external adapters
├─ interfaces/
│  ├─ http/                     # APIRouter, Pydantic request/response schemas, dependencies
│  └─ jobs/                     # task handlers (thin: parse args → call use case)
└─ public.py                    # the ONLY module other contexts may import (facade + published events)
```

Rules, enforced by tooling (section 12):

- Dependency direction: `interfaces → application → domain`; `infrastructure → application/domain`; domain imports nothing outward.
- Contexts talk only through another context's `public.py` (synchronous facade calls) or domain events (via the in-process bus, and the outbox when it must survive a crash). No cross-context table joins and no importing another context's ORM models.
- `compliance` is a real context, not an afterthought: erasure and export need each context to implement a small `PersonalDataHandler` port (`export(user)`, `erase(user)`), which is how deletion stays complete as features are added.
- Keep the layering pragmatic: simple CRUD contexts (e.g. `tenancy` invitations) do not need a rich domain model — a use case and a repository are enough. Reserve the full pattern for `evaluation` and `billing`, where invariants are real.
- Event naming collision: the product's "events" (competitions) vs domain events. Name the context package `events` but call the platform mechanism `domain_events`/`messages` to avoid confusion.

**ADRs to write first** (MADR format, one page each): monorepo and modular monolith; Postgres as system of record and RLS tenancy; Postgres-based job queue; psycopg 3; auth split (IdP for authn, backend for authz); S3 port and no-MinIO; SSE only; billing port and credit ledger; Python 3.14; OpenAPI-first client.

---

## 12. CI and quality gates

**Pre-commit (fast, local):** `ruff format`, `ruff check --fix`, prettier/eslint on staged files, `gitleaks` (secrets), end-of-file/whitespace/large-file checks, `uv lock --check`, commit-msg hook for Conventional Commits. Type checking and tests stay in CI/pre-push to keep commits quick.

**Conventional Commits:** `commitlint` (or `commitizen`) on commit messages and PR titles; squash-merge so the PR title is the commit. Feeds `release-please` (or similar) for changelog and version tags.

**CI pipeline (GitHub Actions; portable to any runner — every step is a `make` target):**

| Stage | Gate |
|---|---|
| Change detection | Path filters / `turbo --affected` so web-only PRs skip Python jobs and vice versa |
| Python lint | `ruff format --check`, `ruff check` |
| Python types | `mypy --strict` over all workspace packages |
| Architecture | `import-linter` contracts: layer direction, context independence, only `public.py` importable across contexts |
| Python unit tests | Domain + application with fakes; no I/O; fast |
| Python integration tests | testcontainers Postgres (pgvector), Valkey, S3 container; run as `app_rw`; includes RLS suite |
| Coverage | `pytest-cov`, branch coverage; fail under 80% overall and **90% on `domain/` and `application/`**; diff coverage on changed lines ≥ 85% |
| Migrations | `alembic upgrade head` from empty; `alembic check` (no model drift); single head (`alembic heads` returns one); downgrade/upgrade round-trip of the latest revision; RLS meta-test |
| API contract | Export `openapi.json`; fail if it differs from the committed file; `oasdiff` breaking-change check against `main` |
| Client generation | Regenerate TS client; fail on diff |
| JS lint / types | `eslint`, `tsc --noEmit` |
| JS tests | Vitest with coverage threshold |
| Build | `next build`; Docker build for api, worker, web |
| E2E | Playwright against the Compose stack (LLM calls stubbed by a fake provider adapter) — on main and nightly, smoke subset on PRs |
| Dependency vulnerabilities | `pip-audit` (or `uv`'s audit command if available `[U]`), `pnpm audit`, Trivy on images; Dependabot or Renovate for updates (group minor/patch, weekly) |
| Licence scanning | `pip-licenses` and `license-checker` against an allow-list (MIT, BSD, Apache-2.0, ISC, PSF, MPL-2.0); fail on GPL/AGPL/SSPL; explicit decision required for LGPL. This is what flags Dramatiq (LGPL) and Redis 8 (AGPL/SSPL/RSAL) |
| Secrets | `gitleaks` on full history in CI |
| SAST | Ruff `S` rules (bandit), CodeQL or Semgrep |
| Containers | hadolint; non-root user; pinned base image digests; SBOM (Syft / CycloneDX) attached to releases |

**Branch protection:** required checks, one review, linear history, no direct pushes to `main`. **Definition of done** for a tenant-scoped feature includes: RLS policy on new tables, a cross-tenant test, audit-log entries for mutations, a `PersonalDataHandler` update if personal data is stored, and an ADR when a decision in this document is changed.

---

## Open items to resolve before or during the first sprint

1. Spike: Procrastinate transactional defer on a SQLAlchemy/psycopg connection, plus trace propagation. `[U]`
2. Spike: Better Auth JWT → FastAPI JWKS verification; evaluate the SSO plugin against a test SAML IdP. `[U]`
3. Choose SeaweedFS vs Garage after running the S3 compatibility test suite (presigned POST in particular). `[U]`
4. Confirm TypeScript 7 compatibility with the lint and codegen toolchain; otherwise pin 6.x. `[U]`
5. Legal: processor vs fiduciary position, under-18 handling and the Fourth Schedule, DPA template, GST rate and invoice format.
6. Razorpay: confirm subscription + credit-pack flows, international card enablement, and settlement/GST reporting for the entity type.
7. Re-check Python 3.15 and PostgreSQL 19 in about three months; neither should be adopted at launch.

---

## Sources

**Versions (registry metadata, read 2026-10-01)**
- https://www.python.org/downloads/ · https://peps.python.org/pep-0790/ · https://devguide.python.org/versions/
- https://pypi.org/pypi/fastapi/json · https://pypi.org/pypi/pydantic/json · https://pypi.org/pypi/sqlalchemy/json · https://pypi.org/pypi/asyncpg/json · https://pypi.org/pypi/psycopg/json · https://pypi.org/pypi/alembic/json · https://pypi.org/pypi/pgvector/json
- https://pypi.org/pypi/uv/json · https://pypi.org/pypi/ruff/json · https://pypi.org/pypi/mypy/json · https://pypi.org/pypi/pyright/json · https://pypi.org/pypi/ty/json
- https://pypi.org/pypi/pytest/json · https://pypi.org/pypi/pytest-asyncio/json · https://pypi.org/pypi/testcontainers/json
- https://pypi.org/pypi/celery/json · https://pypi.org/pypi/dramatiq/json · https://pypi.org/pypi/arq/json · https://pypi.org/pypi/taskiq/json · https://pypi.org/pypi/procrastinate/json · https://api.github.com/repos/procrastinate-org/procrastinate/releases · https://api.github.com/repos/temporalio/sdk-python/releases
- https://pypi.org/pypi/structlog/json · https://pypi.org/pypi/sentry-sdk/json · https://pypi.org/pypi/opentelemetry-sdk/json
- https://registry.npmjs.org/next/latest · https://registry.npmjs.org/react/latest · https://registry.npmjs.org/typescript/latest · https://registry.npmjs.org/@tanstack/react-query/latest · https://registry.npmjs.org/tailwindcss/latest · https://registry.npmjs.org/zod/latest · https://registry.npmjs.org/react-hook-form/latest · https://registry.npmjs.org/@hey-api/openapi-ts/latest · https://registry.npmjs.org/openapi-typescript/latest · https://registry.npmjs.org/openapi-fetch/latest · https://registry.npmjs.org/orval/latest · https://registry.npmjs.org/turbo/latest · https://registry.npmjs.org/pnpm/latest · https://registry.npmjs.org/vitest/latest · https://registry.npmjs.org/@playwright/test/latest · https://registry.npmjs.org/better-auth/latest

**Backend and data**
- SQLAlchemy 2.1 migration notes: https://docs.sqlalchemy.org/en/21/changelog/migration_21.html
- FastAPI SSE: https://fastapi.tiangolo.com/tutorial/server-sent-events/ · https://fastapi.tiangolo.com/reference/sse/ · https://github.com/fastapi/fastapi/pull/15030
- pgvector: https://github.com/pgvector/pgvector
- PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html · PostgreSQL 18 release notes: https://www.postgresql.org/docs/current/release-18.html
- asyncpg and PgBouncer: https://github.com/MagicStack/asyncpg/issues/1058
- pytest-asyncio changelog: https://pytest-asyncio.readthedocs.io/en/latest/reference/changelog.html
- Procrastinate: https://procrastinate.readthedocs.io/en/stable/ · locks: https://procrastinate.readthedocs.io/en/stable/howto/advanced/locks.html · retries: https://procrastinate.readthedocs.io/en/stable/howto/advanced/retry.html · connectors: https://procrastinate.readthedocs.io/en/stable/howto/basics/connector.html
- Valkey: https://valkey.io/ · Redis licence timeline (secondary): https://redisvsmemcached.com/redis-license-timeline/
- MinIO archival (secondary): https://www.infoq.com/news/2025/12/minio-s3-api-alternatives/ · https://pinggy.io/blog/minio_archived_self_hosted_s3_alternatives/
- ClamAV: https://docs.clamav.net/manual/Usage/ClamdProtocol.html · https://docs.clamav.net/manual/Installing/Docker.html · https://github.com/Cisco-Talos/clamav/releases · https://docs.clamav.net/faq/faq-eol.html
- S3 presigned POST: https://docs.aws.amazon.com/botocore/latest/reference/services/s3/client/generate_presigned_post.html · multipart: https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html

**Auth**
- Better Auth: https://better-auth.com/docs/plugins · SSO: https://better-auth.com/docs/plugins/sso · API keys: https://better-auth.com/docs/plugins/api-key · Auth.js transfer: https://better-auth.com/blog/authjs-joins-better-auth
- Keycloak: https://www.keycloak.org/docs/latest/release_notes/index.html · https://www.keycloak.org/2026/04/keycloak-2660-released
- WorkOS pricing (secondary): https://stackcostlab.com/providers/workos

**Billing**
- Stripe India invite-only: https://support.stripe.com/questions/stripe-accounts-are-invite-only-in-india · video KYC: https://support.stripe.com/questions/video-kyc-for-india-onboarding · UPI: https://docs.stripe.com/changelog/dahlia/2026-03-25/adds-support-for-the-upi-payment-method · India recurring: https://docs.stripe.com/india-recurring-payments · legacy usage billing removal: https://docs.stripe.com/changelog/basil/2025-03-31/deprecate-legacy-usage-based-billing
- Razorpay: webhooks https://razorpay.com/docs/webhooks/validate-test/ · best practices https://razorpay.com/docs/webhooks/best-practices/ · UPI Autopay https://razorpay.com/docs/payments/payment-gateway/s2s-integration/recurring-payments/upi/ · e-mandate https://razorpay.com/docs/announcements/rbi-card-mandate-guidelines/subscriptions/ · MoR vs gateway https://razorpay.com/blog/merchant-of-record-vs-international-payment-gateway-decision-guide/ · GST e-invoicing https://razorpay.com/learn/gst-e-invoicing-system/

**Frontend**
- Next.js 16: https://nextjs.org/blog/next-16
- shadcn/ui: https://ui.shadcn.com/docs/changelog · https://ui.shadcn.com/docs/tailwind-v4
- Hey API: https://heyapi.dev/openapi-ts/plugins/tanstack-query

**Observability**
- Langfuse self-hosting: https://langfuse.com/self-hosting/deployment/infrastructure/clickhouse

**Compliance (secondary summaries — confirm against the gazette)**
- Timeline: https://www.sansalegal.com/post/dpdp-act-2023-and-rules-2025-phased-implementation-timeline-and-business-compliance-deadlines · https://www.consent.in/blog/dpdp-rules
- Rules text mirrors: https://www.dpdpa.com/dpdparules/rule6.html · https://www.dpdpa.com/dpdparules/rule8.html · https://www.dpdpa.com/dpdparules/rule10.html · https://www.dpdpa.com/dpdparules/rule14.html · Fourth Schedule: https://dpdprules.org/rules/fourth-schedule
- Breach timeline: https://www.medianama.com/2025/11/223-data-breach-reporting-timeline-of-dpdp-rules-2025-explained/
- KPMG overview: https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2025/11/dpdp-rules-2025-guidance-to-dpdp-act-implementation.pdf
