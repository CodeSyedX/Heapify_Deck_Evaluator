# Deck Evaluator

A judge-assist tool for hackathons and pitch competitions. It scores each deck against the event's own rubric, shows the slide evidence behind every score, flags near-duplicates and attempts to game the scorer, and gives organisers a ranked, exportable shortlist. Humans make the final decision.

## Repository layout

| Path | Contents |
|---|---|
| `apps/api` | FastAPI entry point |
| `apps/worker` | Background worker entry point (evaluation pipeline) |
| `apps/web` | Next.js web application |
| `packages/py/core` | `deck_core`: all backend domain, application and infrastructure code |
| `packages/api-client` | OpenAPI document and generated TypeScript client |
| `db/migrations` | Alembic migrations |
| `infra` | Docker Compose stack and Dockerfiles |
| `evals` | Harness that measures the scorer against human-scored decks |
| `docs` | Product requirements, architecture, decision records, research |

## Documentation

- [Product requirements](docs/product/prd.md)
- [Architecture overview](docs/architecture/overview.md)
- [Evaluation pipeline](docs/architecture/evaluation-pipeline.md)
- [Data model](docs/architecture/data-model.md)
- [Engineering conventions](docs/engineering/conventions.md)
- [Decision records](docs/adr)
- [Research](docs/research)
