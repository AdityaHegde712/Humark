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

- **Phase 2: Statistical Significance Gate & Data Ingestion**
  - Dependency: Phase 1
  - Affected paths: `backend/app/core/stats.py`, `backend/app/api/admin.py`, `backend/data/seed_challenges.json`, `tests/spec/test_significance_gate.py`
  - Exit criteria: Z-test significance gate rejects p >= 0.05 or N < 20,000; 30+ bundled demo items ingest successfully.

- **Phase 3: Model Baseline Runner & Evaluation Harness**
  - Dependency: Phase 2
  - Affected paths: `backend/app/eval/`, `backend/app/models/eval_run.py`, `tests/spec/test_eval_runner.py`
  - Exit criteria: Deterministic mock model produces reproducible predictions, tokens, and latency; pre-computes answers for all seed items.

- **Phase 4: Game Engine, Session Management & Anti-Luck Verification**
  - Dependency: Phase 3
  - Affected paths: `backend/app/core/game.py`, `backend/app/api/challenges.py`, `backend/app/api/sessions.py`, `tests/spec/test_game_engine.py`
  - Exit criteria: Unseen-item selection guarantees zero repeats across 3 rounds of 10 items; verified status triggers strictly at >=22/30 (cumulative >70%).

- **Phase 5: Scorecard Engine & Wilson Interval Telemetry**
  - Dependency: Phase 4
  - Affected paths: `backend/app/core/scoring.py`, `backend/app/api/scorecard.py`, `tests/spec/test_scorecard.py`
  - Exit criteria: Computes overall accuracy, Wilson 95% confidence intervals, and head-to-head model differentials.

- **Phase 6: Frontend Challenge UI & Interactive Scorecard**
  - Dependency: Phase 5
  - Affected paths: `frontend/src/`
  - Exit criteria: Complete playable loop: Round 1 launch -> ~30s challenge card -> receipt reveal -> scorecard -> rounds 2 & 3 verification track.

- **Phase 7: End-to-End Hardening & Documentation**
  - Dependency: Phase 6
  - Affected paths: `README.md`, `CODEBASE.md`, docker verification
  - Exit criteria: Production readiness review passes; zero-setup `docker compose up` verified on clean clone.
