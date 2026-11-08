# Humark Task Master Checklist

## Phase 1: Project Setup & Monorepo Foundation
- [x] Task 01: Scaffold monorepo structure, Docker Compose, FastAPI skeleton, Vite React setup, and `.env.example`
  - Acceptance Criteria: `docker compose build` succeeds; backend `/health` returns status ok; frontend displays dark theme skeleton on port 5173; `.env.example` lists configuration placeholders.
  - File Paths: `docker-compose.yml`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/app/main.py`, `frontend/Dockerfile`, `frontend/package.json`, `frontend/src/App.tsx`, `.env.example`

## Phase 2: Statistical Significance Gate & Data Ingestion
- [x] Task 02: Implement statistical significance engine (two-proportion z-test, Wilson intervals) and contract tests
  - Acceptance Criteria: `tests/spec/test_significance_gate.py` passes; engine rejects items where $N < 20,000$ per variant or $p \ge 0.05$; computes correct z-scores, p-values, and 95% Wilson confidence intervals.
  - File Paths: `backend/app/core/stats.py`, `tests/spec/test_significance_gate.py`
- [x] Task 03: Challenge data model, schema migrations, and JSON ingestion pipeline with validation errors
  - Acceptance Criteria: PostgreSQL models for `challenges` and `model_predictions`; ingestion CLI/endpoint validates provenance, rejects invalid items with HTTP 422/CLI error; ingests 30+ seed items.
  - File Paths: `backend/app/models/challenge.py`, `backend/app/schemas/challenge.py`, `backend/app/core/ingestion.py`, `backend/data/seed_challenges.json`, `backend/app/static/thumbnails/`

## Phase 3: Model Baseline Runner & Evaluation Harness
- [x] Task 04: Implement deterministic mock vision model & baseline runner with token/cost logging
  - Acceptance Criteria: Mock runner scores seed items deterministically with pinned prompt version `v1.0.0`; records token counts, latency, and predictions; LiteLLM adapter interface ready.
  - File Paths: `backend/app/eval/runner.py`, `backend/app/eval/prompts.py`, `backend/app/models/eval_run.py`, `tests/spec/test_eval_runner.py`

## Phase 4: Game Engine, Session Management & Anti-Luck Verification
- [ ] Task 05: Session management, backend unseen-item selection, and attempt submission
  - Acceptance Criteria: Unseen items selected via SQL query filtering previous attempts for session; answer submission immediately returns receipt with ground truth + model answers; guarantees no duplicate items.
  - File Paths: `backend/app/models/session.py`, `backend/app/core/game.py`, `backend/app/api/challenges.py`, `backend/app/api/sessions.py`, `tests/spec/test_game_engine.py`
- [ ] Task 06: Verification state machine & round progression (3 rounds x 10 items)
  - Acceptance Criteria: Enforces 3 rounds of 10 items; computes cumulative accuracy; marks `verified=true` strictly when cumulative accuracy >70% ($\ge 22/30$); logs verification audit event.
  - File Paths: `backend/app/core/verification.py`, `backend/app/api/verification.py`, `tests/spec/test_verification.py`

## Phase 5: Scorecard Engine & Wilson Interval Telemetry
- [ ] Task 07: Scorecard aggregation endpoint with model comparison and Wilson confidence
  - Acceptance Criteria: Returns overall accuracy, sample size warning, Wilson 95% confidence interval, model head-to-head comparison (beats/ties/losses), and category breakdown.
  - File Paths: `backend/app/core/scoring.py`, `backend/app/api/scorecard.py`, `tests/spec/test_scorecard.py`

## Phase 6: Frontend Challenge UI & Interactive Scorecard
- [ ] Task 08: Frontend core shell, dark theme layout, and challenge card interface
  - Acceptance Criteria: Responsive UI (#121212 theme, hairline borders); displays A/B thumbnail cards with ~30s progress feel; supports keyboard/click selection.
  - File Paths: `frontend/src/components/ChallengeCard.tsx`, `frontend/src/components/Header.tsx`, `frontend/src/index.css`
- [ ] Task 09: Receipt modal and model comparison reveal
  - Acceptance Criteria: Immediately on selection, reveals ground truth winner, actual CTR, impression count, p-value, and how each baseline model answered.
  - File Paths: `frontend/src/components/ReceiptModal.tsx`, `frontend/src/components/ModelBadge.tsx`
- [ ] Task 10: Scorecard view, verification badges, and round progression UI
  - Acceptance Criteria: Displays round 1 scorecard; displays accuracy with Wilson confidence interval; displays "Take Round 2" / "Verification Track"; displays verified badge when unlocked.
  - File Paths: `frontend/src/components/Scorecard.tsx`, `frontend/src/components/VerificationBadge.tsx`, `frontend/src/pages/GamePage.tsx`

## Phase 7: End-to-End Hardening & Documentation
- [ ] Task 11: Production readiness audit, E2E verification test, and comprehensive documentation
  - Acceptance Criteria: `docker compose up` verified working end-to-end; comprehensive README with architecture, stats explanation, and model integration guide; CODEBASE.md generated.
  - File Paths: `README.md`, `CODEBASE.md`, `tests/integration/test_e2e_gameplay.py`
