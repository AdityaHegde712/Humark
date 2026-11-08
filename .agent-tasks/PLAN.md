# Humark System Architecture & Execution Plan

## 1. Executive Summary & System Architecture
Humark is a human-vs-AI benchmark platform and rigorous evaluation harness for predicting YouTube thumbnail performance.
It operates as a monorepo containing a FastAPI backend, PostgreSQL database, and React (Vite) frontend.

```
                           +---------------------------------------+
                           |       React + Vite Frontend (SPA)     |
                           |  - Dark Flat Theme (#121212)          |
                           |  - Round 1..3 Challenge Flow (~30s)   |
                           |  - Receipt & Model Comparison Modal   |
                           |  - Statistical Scorecard & Badges     |
                           +-------------------+-------------------+
                                               |
                                     REST / JSON (Session UUID)
                                               |
                                               v
+----------------------------------------------------------------------------------+
|                             FastAPI Backend Service                              |
|                                                                                  |
|  +------------------------+  +------------------------+  +--------------------+  |
|  |     Session Engine     |  |   Ingestion & Gate     |  |   Eval Harness     |  |
|  | - Guest token creation |  | - Two-proportion Z-test|  | - Versioned prompt |  |
|  | - Unseen item selector |  | - p < 0.05 hard gate   |  | - Mock model       |  |
|  | - Verification state   |  | - N >= 20k gate        |  | - LiteLLM vision   |  |
|  +------------------------+  +------------------------+  +--------------------+  |
|                                                                                  |
|  +----------------------------------------------------------------------------+  |
|  | Statistical Scoring Engine: Wilson score intervals, accuracy, model delta  |  |
|  +----------------------------------------------------------------------------+  |
|                                               |                                  |
+-----------------------------------------------|----------------------------------+
                                                v
                           +---------------------------------------+
                           |          PostgreSQL Database          |
                           |  - challenges (A/B items, metadata)   |
                           |  - model_predictions (pre-computed)   |
                           |  - sessions & session_attempts        |
                           |  - verification_audit_log             |
                           +---------------------------------------+
```

## 2. Active Execution Phases & Dependency Chains

- **Phase 1: Project Setup & Monorepo Foundation**
  - Dependency: None
  - Affected paths: `docker-compose.yml`, `backend/`, `frontend/`, `.env.example`
  - Exit criteria: Docker Compose boots Postgres, FastAPI backend, and Vite frontend with passing healthchecks.

- **Phase 2: Statistical Significance Gate & Data Ingestion (COMPLETED)**
  - Dependency: Phase 1
  - Affected paths: `backend/app/core/stats.py`, `backend/app/models/challenge.py`, `backend/app/schemas/challenge.py`, `backend/app/core/ingestion.py`, `backend/app/api/admin.py`, `backend/data/seed_challenges.json`, `backend/app/static/thumbnails/`, `tests/spec/test_significance_gate.py`, `tests/spec/test_ingestion.py`
  - Exit criteria: Z-test significance gate rejects p >= 0.05 or N < 20,000; 36 bundled demo items with 72 SVGs ingest successfully.

- **Phase 3: Model Baseline Runner & Evaluation Harness (COMPLETED)**
  - Dependency: Phase 2
  - Affected paths: `backend/app/eval/`, `backend/app/models/eval_run.py`, `tests/spec/test_eval_runner.py`
  - Exit criteria: Deterministic mock model produces reproducible predictions, tokens, and latency; pre-computes answers for all seed items.

- **Phase 4: Game Engine, Session Management & Anti-Luck Verification (COMPLETED)**
  - Dependency: Phase 3
  - Affected paths: `backend/app/core/game.py`, `backend/app/api/challenges.py`, `backend/app/api/sessions.py`, `backend/app/core/verification.py`, `backend/app/api/verification.py`, `tests/spec/test_game_engine.py`, `tests/spec/test_verification.py`
  - Exit criteria: Unseen-item selection guarantees zero repeats across 3 rounds of 10 items; verified status triggers strictly at >=22/30 (cumulative >70%).

- **Phase 5: Scorecard Engine & Wilson Interval Telemetry (COMPLETED)**
  - Dependency: Phase 4
  - Affected paths: `backend/app/core/scoring.py`, `backend/app/api/scorecard.py`, `tests/spec/test_scorecard.py`
  - Exit criteria: Computes overall accuracy, Wilson 95% confidence intervals, and head-to-head model differentials.

- **Phase 6: Frontend Challenge UI & Interactive Scorecard (COMPLETED)**
  - Dependency: Phase 5
  - Affected paths: `frontend/src/`
  - Completed: Task 08 (API client, dark theme shell, header, challenge card interface), Task 09 (Receipt modal and model comparison reveal), Task 10 (Scorecard view, verification badges, and round progression UI)
  - Exit criteria: Complete playable loop: Round 1 launch -> ~30s challenge card -> receipt reveal -> scorecard -> rounds 2 & 3 verification track.

- **Phase 7: End-to-End Hardening & Documentation (COMPLETED)**
  - Dependency: Phase 6
  - Affected paths: `tests/integration/test_e2e_gameplay.py`, `backend/app/main.py`, `backend/app/scripts/seed.py`, `docker-compose.yml`, `README.md`, `CODEBASE.md`
  - Completed: Task 11 (E2E 3-round gameplay integration test and seed automation)
  - Exit criteria: Production readiness review passes; zero-setup `docker compose up` verified on clean clone; all unit, spec, and integration tests pass.

- **Phase 8: Feature Deepening & Visual Motif Analysis (COMPLETED)**
  - Dependency: Phase 7
  - Affected paths: `backend/app/models/challenge.py`, `backend/app/schemas/challenge.py`, `backend/app/core/motif_analysis.py`, `backend/app/schemas/scorecard.py`, `backend/app/core/scoring.py`, `backend/data/seed_challenges.json`, `frontend/src/api/types.ts`, `frontend/src/components/MotifBreakdown.tsx`, `frontend/src/components/Scorecard.tsx`, `tests/spec/test_motif_analysis.py`
  - Completed: Task 12 (Percentile curve), Task 13 (Landing hero), Task 14 (Visual motif tagging & failure mode analysis engine)
  - Exit criteria: 36 seed challenges tagged across 4 canonical visual motifs; motif breakdown computes human vs frontier AI advantage; scorecard displays "Where Human Intuition Beats Frontier AI" with dual perceptual/algorithmic strengths; all contract tests pass; frontend builds with 0 errors.
