# Architecture

This is a local-first monorepo. `apps/dashboard` is the minimal Next.js client; `services/api` owns HTTP boundaries; agents, ML, simulator, policy, and executor are isolated Python packages. PostgreSQL/Supabase is the persistence boundary and pgvector is reserved for documents.

Phase 0 defines interfaces and configuration only. The simulator comes next, then quantitative evaluation, then agent orchestration and bounded test-mode execution. No unfinished service is represented as production behavior.
