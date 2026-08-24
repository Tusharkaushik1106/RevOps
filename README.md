# Revenue Incident Commander

Local-first foundation for payment revenue incident intelligence. Phase 0 only: interfaces, schemas, configuration, persistence boundary, tooling, and minimal health/landing routes.

## Architecture

Next.js dashboard → FastAPI API → isolated agents, ML, simulator, policy, and executor services. PostgreSQL/pgvector is the Supabase-compatible persistence and RAG boundary. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Prerequisites

Docker, Python 3.12+, Node.js 20+, npm, and GNU Make (or equivalent commands).

## Setup and run

Copy `.env.example` to `.env`, then use `make install`. Run `docker compose up --build` for the local stack, or run `uvicorn app.main:app --reload` from `services/api` and `npm run dev` from `apps/dashboard` separately.

API health: `http://localhost:8000/health`. Dashboard: `http://localhost:3000`.

## Checks

`make test`, `make lint`, and `make format` provide the root developer commands. Frontend checks are `npm run typecheck` and `npm run lint` inside `apps/dashboard`.

## Environment

See `.env.example`. Secrets are intentionally blank and must remain environment-only.

## Structure

`apps/dashboard`, `services/{api,agents,ml,simulator,policy,executor}`, `packages/schemas`, `data/{synthetic,evaluation}`, `docs`, `infra/docker`, `scripts`, and `tests`.

## Status and phases

Phase 0 foundation and Phase 1 synthetic simulation are implemented. Agent reasoning, incident detection, ML models, real Razorpay test-mode actions, and final UI remain intentionally deferred.

## Simulator (Phase 1)

Generate deterministic synthetic traffic with `python -m services.simulator generate --seed 42 --payments 10000` or add `--scenario issuer_degradation`. Output is JSON under `data/synthetic/`; ground truth is held in the result model separately from observable events. Replay with `python -m services.simulator replay --file data/synthetic/example.json`.

# RevOps

RevOps is the repository for Revenue Incident Commander: a local-first payment revenue intelligence platform. The project is being built in verified phases, beginning with a deterministic synthetic payment environment that preserves strict separation between observable payment events and evaluator-only incident ground truth. This foundation is designed for reproducible incident analysis, revenue-impact measurement, and safe future recovery experimentation without paid infrastructure or production payment credentials.
