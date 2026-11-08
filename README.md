# Humark

**Humark** is a human-vs-AI benchmark platform and evaluation harness designed to test whether humans can predict real-world audience behavior better than frontier vision models. 

The initial vertical evaluates **YouTube Thumbnail A/B Tests**: predicting which of two thumbnails generated a higher Click-Through Rate (CTR) in high-volume, statistically significant experiments ($N \ge 20,000$ impressions per variant, two-tailed two-proportion z-test $p < 0.05$).

---

## 1. System Architecture

Humark is structured as a clean, production-hardened monorepo orchestrated with Docker Compose:

```
                            +---------------------------------------+
                            |       React + Vite Frontend (SPA)     |
                            |  - Dark Flat Theme (#121212)          |
                            |  - Round 1..3 Challenge Flow (~30s)   |
                            |  - Ground Truth Receipt Reveal        |
                            |  - Statistical Scorecard & Badges     |
                            +-------------------+-------------------+
                                                |
                                     REST / JSON (Session UUID)
                                                |
                                                v
+-----------------------------------------------------------------------------------+
|                             FastAPI Backend Service                               |
|                                                                                   |
|  +------------------------+  +------------------------+  +---------------------+  |
|  |     Session Engine     |  |   Ingestion & Gate     |  |    Eval Harness     |  |
|  | - Guest token creation |  | - Two-proportion Z-test|  | - Pinned prompt v1  |  |
|  | - Unseen item selector |  | - p < 0.05 hard gate   |  | - Deterministic mock|  |
|  | - Verification state   |  | - N >= 20k gate        |  | - OpenRouter live   |  |
|  +------------------------+  +------------------------+  +---------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Statistical Scoring Engine: Wilson score intervals, accuracy, model delta   |  |
|  +-----------------------------------------------------------------------------+  |
|                                               |                                   |
+-----------------------------------------------|-----------------------------------+
                                                v
                            +---------------------------------------+
                            |          PostgreSQL 16 DB             |
                            |  - challenges (A/B items, metadata)   |
                            |  - model_predictions (pre-computed)   |
                            |  - game_sessions & session_attempts   |
                            |  - verification_audit_logs            |
                            +---------------------------------------+
```

### Component Breakdown
- **FastAPI Backend (`backend/app/`)**: High-performance asynchronous API, SQLAlchemy 2.0 ORM, Pydantic v2 schemas, and scientific statistical computing routines.
- **PostgreSQL 16 Database**: Persists active challenges, pre-computed baseline predictions, guest player sessions, attempts, and verification audit logs.
- **React 18 + TypeScript Frontend (`frontend/src/`)**: Dark minimal flat UI (`#121212`, hairline `#27272a` borders) styled with Tailwind CSS and Lucide icons.
- **Model Baseline Runner (`backend/app/eval/`)**: Zero-key deterministic mock vision runner (`mock-frontier-v1`, `mock-compact-v1`, `mock-heuristic-v1`) plus live OpenRouter multimodal adapter.

---

## 2. Statistical Foundations

### A. The Significance Hard Gate (Two-Proportion Z-Test)
In high-variance domains like YouTube CTR, trivial sample sizes or small percentage differences frequently produce false-positive winners. Humark enforces a non-bypassable ingestion gate in `backend/app/core/stats.py`:

1. **Minimum Sample Size Gate**:
   $$\text{impressions}_A \ge 20,000 \quad \text{and} \quad \text{impressions}_B \ge 20,000$$
2. **Two-Tailed Pooled Z-Test**:
   $$\hat{p}_{pool} = \frac{x_A + x_B}{n_A + n_B}$$
   $$SE = \sqrt{\hat{p}_{pool}(1 - \hat{p}_{pool}) \left(\frac{1}{n_A} + \frac{1}{n_B}\right)}$$
   $$z = \frac{\hat{p}_A - \hat{p}_B}{SE}$$
   $$p\text{-value} = 2 \times (1 - \Phi(|z|))$$
3. **Significance Threshold**:
   $$p < 0.05$$
Any challenge failing either criterion is permanently rejected during ingestion.

### B. Scorecard Confidence: Wilson Score Intervals
Reporting raw percentages on small samples (e.g. 7/10 = 70%) misrepresents true predictive capability. Humark computes 95% Wilson score confidence intervals:

$$\tilde{p} = \frac{\hat{p} + \frac{z^2}{2n}}{1 + \frac{z^2}{n}}, \quad \text{Margin} = \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{\hat{p}(1 - \hat{p})}{n} + \frac{z^2}{4n^2}}$$

When $n < 30$, the system attaches a `sample_size_warning: true` alert to prevent participants or evaluators from drawing premature conclusions.

### C. Anti-Luck Verification Protocol
To eliminate luck:
- A complete evaluation run requires **3 sequential rounds of 10 challenges** (30 total).
- **Backend Unseen-Item Guarantee**: Challenge queries strictly exclude all items previously attempted by that session (`NOT IN (SELECT challenge_id FROM session_attempts WHERE session_id = :id)`).
- **Verification Threshold**: Status = `VERIFIED` strictly if cumulative accuracy $> 70\%$ ($\ge 22 / 30$ correct).
- **Tamper-Evident Audit Receipt**: Upon completion, the system generates a canonical SHA-256 HMAC digest over the participant's attempt sequence, certifying the score without manual DB intervention.

---

## 3. Quick Start (Run Locally)

### Prerequisites
- Docker & Docker Compose **OR** Python 3.11+ and Node.js 18+

### One-Command Docker Run
```bash
docker compose up --build
```
- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Healthcheck: [http://localhost:8000/health](http://localhost:8000/health)

The database automatically seeds 36 statistically significant demo challenges with pre-computed baseline model predictions on first boot.

### Local Development (Without Docker)
1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m app.scripts.seed
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 4. Running Tests

The test suite enforces immutable behavioral contracts across statistical gates, unseen-item queries, verification thresholds, and complete E2E gameplay:

```bash
pytest -v
```

### Test Coverage Highlights
- `tests/spec/test_significance_gate.py`: 17 tests verifying pooled z-score math, edge cases, Wilson intervals, and rejection of $p \ge 0.05$ or $N < 20,000$.
- `tests/spec/test_ingestion.py`: Ingestion pipeline validation, schema information hiding, and seed JSON integrity.
- `tests/spec/test_eval_runner.py`: Baseline runner determinism, token/cost tracking, prompt versioning (`v1.0.0`), and mock models.
- `tests/spec/test_game_engine.py`: Session management, strict unseen-item selection, attempt uniqueness, and receipt reveals.
- `tests/spec/test_verification.py`: 3-round progression state machine, $\ge 22/30$ threshold gating, and tamper-evident audit logs.
- `tests/spec/test_scorecard.py`: Scorecard aggregation, Wilson intervals, and head-to-head model comparison.
- `tests/integration/test_e2e_gameplay.py`: Complete 30-item simulated player run validating zero-repeat selection, receipt reveals, scorecard progression, and verification gating.

---

## 5. How to Add a Real Frontier Vision Model

Humark includes a pluggable multimodal adapter interface in `backend/app/eval/openrouter_adapter.py`.

### 1. Set Your OpenRouter API Key
In `.env` (copy from `.env.example`):
```env
OPENROUTER_API_KEY=sk-or-v1-...
```

### 2. Configure Pinned Models
Add your desired multimodal model identifiers to `backend/app/eval/runner.py`:
```python
AVAILABLE_LIVE_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "openai/gpt-4o-mini",
]
```

### 3. Run the Evaluation Runner
```bash
python -m app.eval.runner --live --model google/gemini-2.0-flash-exp:free
```
The runner uses the pinned prompt template (`v1.0.0`), sends base64/URL thumbnails, records tokens, measured latency, and header cost, and stores predictions in the `model_predictions` table before participants attempt challenges.

---

## 6. What Was Deliberately Excluded from v1

In accordance with architectural scoping:
1. **Recruiter Marketplace & Hiring Portals**: Deliberately omitted to maintain focus on the core statistical eval harness.
2. **Payments / Subscriptions**: Zero payment processing or billing dependencies.
3. **Multi-Vertical Datasets**: Focused exclusively on YouTube thumbnails to ensure dataset density and statistical depth.
4. **Mandatory User Accounts / Social Login**: Uses frictionless guest sessions with UUID tokens; zero signup required for Round 1 or verification runs.
