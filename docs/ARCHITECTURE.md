# Architecture

This is a local-first monorepo. `apps/dashboard` is the minimal Next.js client; `services/api` owns HTTP boundaries; agents, ML, simulator, policy, and executor are isolated Python packages. PostgreSQL/Supabase is the persistence boundary and pgvector is reserved for documents.

Phase 2 quantitative detection is frozen as the MVP evidence engine. Phase 3 adds a LangGraph causal-investigation boundary over typed evidence packets; it recommends hypotheses and recovery candidates but has no financial execution authority. Gemini is provider-abstracted and mockable; detector tools remain read-only and ground-truth blind.
