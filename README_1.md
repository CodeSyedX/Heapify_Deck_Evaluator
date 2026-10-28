# Heapify Deck Evaluator

[![Python Version](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Next.js-14+-000000.svg)](https://nextjs.org/)
[![Database](https://img.shields.io/badge/PostgreSQL-18%20%2B%20pgvector-336791.svg)](https://www.postgresql.org/)

**Heapify Deck Evaluator** is an open-source, AI-powered judge-assist platform engineered for hackathons, startup accelerators, and pitch competitions. It automates the initial screening phase of pitch deck submissions by evaluating slides against customizable event rubrics, generating evidence-backed scorecards, surfacing near-duplicate or gamed submissions, and delivering a ranked, exportable shortlist to competition organizers.

The system evaluates and explains—**humans make the final decisions.**

---

## Key Features

- **Rubric-Driven Automated Scoring:** Evaluates submitted pitch decks (PDF or PPTX) against custom, immutable event rubrics.
- **Traceable Slide Evidence:** Every assigned score includes exact slide citations, quotes, and visual context to justify the evaluation.
- **Integrity & Game Detection:**
  - **Prompt Injection & Hidden Text:** Flags hidden layers, off-canvas text, invisible characters, and prompt injection phrasing.
  - **Near-Duplicate Detection:** Identifies recycled or copied pitch decks across event submissions using semantic embeddings and lexical shingle matching.
- **Human-in-the-Loop Workflow:** Provides transparent score breakdown bands, confidence intervals, and override capabilities for human judges.
- **Strict Multi-Tenancy:** Enforces tenant isolation at the database level via PostgreSQL Row-Level Security (RLS).
- **Transactional Evaluation Pipeline:** Every pipeline step commits output, progress events, and state atomically to guarantee idempotency and retry safety.

---

## Architecture Overview

Heapify Deck Evaluator is structured as a **modular monolith** inside a Python workspace managed with [`uv`](https://github.com/astral-sh/uv).

```
Browser ──► web (Next.js) ──► api (FastAPI) ──► PostgreSQL 18 + pgvector (State, Jobs)
   │             │                 │       ├──► S3-Compatible Storage (Decks, Exports)
   │             └ sign-in (OIDC)  │       └──► Valkey (Rate Limits, Cache)
   └── direct upload to storage ───┘
                                worker (Procrastinate) ──► LLM Gateway / BAAI/bge-m3
```

### Evaluation Pipeline Steps

```
queued ──► scanning ──► parsing ──► structure_check ──► integrity_check ──► scoring ──► similarity ──► reporting ──► succeeded
```

| Pipeline Step | Description | Failure Behavior |
| :--- | :--- | :--- |
| `scanning` | Magic byte checks, file size validation, malware scan | Fails/Quarantines invalid or infected files |
| `parsing` | Converts PDF/PPTX into canonical `DeckDocument` schema + PNG images | Fails on corrupt or encrypted files |
| `structure_check` | Checks compliance against rubric templates (slide counts, required sections) | Non-terminal (attaches structural report) |
| `integrity_check` | Scans for hidden, off-canvas, or prompt-injection text | Non-terminal (attaches integrity flags) |
| `scoring` | Multi-sample LLM evaluation; quote verification against slide text | Retries on transient provider errors |
| `similarity` | Computes 1024-dim `BAAI/bge-m3` vectors for semantic/lexical overlap | Non-terminal (logs similarity findings) |
| `reporting` | Aggregates totals, score bands, confidence ratings, and settles credits | Completes run state (`succeeded`) |

---

## Repository Structure

```text
├── apps/
│   ├── api/                   # FastAPI application entry point
│   ├── worker/                # Background worker entry point (Procrastinate)
│   └── web/                   # Next.js frontend application
├── packages/
│   ├── py/core/               # deck_core: Bounded contexts, domain models, UoW
│   └── api-client/            # Generated TypeScript API client (OpenAPI)
├── db/migrations/             # Alembic migration scripts
├── evals/                     # Evaluation harness against human-scored gold sets
├── infra/                     # Docker Compose configurations and Dockerfiles
├── docs/                      # Architectural Decision Records (ADRs) and research
├── pyproject.toml             # Python dependencies and uv workspace configuration
└── uv.lock                    # Dependency lockfile
```

---

## Core Technologies

- **Backend:** Python 3.14, FastAPI, SQLAlchemy 2.x Core, Procrastinate, Pydantic v2
- **Frontend:** Next.js, React, TanStack Query, Tailwind CSS, Better Auth (OIDC)
- **Database & Storage:** PostgreSQL 18 + `pgvector`, S3-compatible Object Storage, Valkey
- **AI & ML Integration:** OpenTelemetry, `BAAI/bge-m3` embeddings, LLM Provider Gateways (Anthropic, OpenAI-compatible)
- **Package & Workspace Manager:** `uv`

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- [Python 3.14+](https://www.python.org/)
- [`uv`](https://github.com/astral-sh/uv) (Python package installer)
- [Node.js 20+](https://nodejs.org/) and `pnpm` (for frontend development)

### Local Infrastructure Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/HeapifyGlobalCommunityy/Heapify_Deck_Evaluator.git
   cd Heapify_Deck_Evaluator
   ```

2. **Initialize Environment Variables:**
   ```bash
   cp .env.example .env
   ```

3. **Start Core Services (PostgreSQL, S3, Valkey) via Docker:**
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```

4. **Install Python Dependencies:**
   ```bash
   uv sync --all-groups
   ```

5. **Run Database Migrations:**
   ```bash
   uv run alembic upgrade head
   ```

### Running the Services Locally

1. **Start the API Server:**
   ```bash
   uv run uvicorn apps.api.main:app --reload --port 8000
   ```

2. **Start the Background Worker:**
   ```bash
   uv run python -m apps.worker.main
   ```

3. **Start the Next.js Web App:**
   ```bash
   cd apps/web
   pnpm install
   pnpm dev
   ```

The application will be accessible at `http://localhost:3000`, and API documentation at `http://localhost:8000/docs`.

---

## Development & Code Quality Standards

The repository enforces strict typing and architectural boundary checks:

```bash
# Format code
uv run ruff format .

# Run lint checks
uv run ruff check .

# Static type check
uv run mypy --strict packages/py/core/src

# Check import boundaries across contexts
uv run import-linter

# Validate database migrations
uv run alembic check
```

### Running Tests

Unit tests run in isolation with fakes, while integration tests use real PostgreSQL containers:

```bash
# Run unit tests
uv run pytest tests/unit

# Run integration tests (requires Docker)
uv run pytest tests/integration
```

---

## Contributing

We welcome contributions from the community! Please ensure:
1. All commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).
2. Domain logic remains isolated within `packages/py/core`.
3. New tenant-owned database tables include PostgreSQL RLS enablement policies.

---

## License

This project is licensed under the [MIT License](LICENSE).
