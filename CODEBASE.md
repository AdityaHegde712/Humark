# Humark Codebase Documentation

## 1. System Overview
Humark is a human-vs-AI evaluation platform for empirical A/B testing of visual media.
It benchmarks human predictive accuracy against multimodal AI models using high-volume, statistically verified real-world datasets.

- **Backend**: FastAPI 0.115+, SQLAlchemy 2.0, Pydantic v2, PostgreSQL 16 / SQLite.
- **Frontend**: React 18, TypeScript 5, Vite 6, Tailwind CSS 3.4, Lucide Icons.
- **Architecture**: Monorepo with Docker Compose orchestration.

---

## 2. Directory Structure

```
Humark/
├── .agent-tasks/              # Orchestrator state tracking & architectural records
│   ├── DECISIONS.md           # Architecture Decision Records (ADR-001 through ADR-009)
│   ├── PLAN.md                # Multi-phase system architecture and execution plan
│   └── TASKS.md               # Atomic task master ledger
├── docs/                      # Engineering teaching artifacts
│   ├── BUGLOG.md              # Confirmed behavioral defect logs
│   └── LESSONS.md             # Architectural design corrections & heuristics
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── api/               # API Route Handlers
│   │   │   ├── admin.py       # Ingestion and administrative endpoints
│   │   │   ├── challenges.py  # Public challenge delivery and answer submission
│   │   │   ├── scorecard.py   # Statistical scorecard aggregation and sharing
│   │   │   ├── sessions.py    # Guest session management
│   │   │   └── verification.py# 3-round verification state machine
│   │   ├── core/              # Domain Services & Business Logic
│   │   │   ├── game.py        # Unseen item selection query and attempt recording
│   │   │   ├── ingestion.py   # Gate validation and batch ingestion engine
│   │   │   ├── scoring.py     # Scorecard calculation and model comparisons
│   │   │   ├── stats.py       # Two-proportion z-test and Wilson score intervals
│   │   │   └── verification.py# Verification evaluation and SHA-256 HMAC digest
│   │   ├── db/                # Database Connections & Session Factory
│   │   │   ├── base.py        # SQLAlchemy 2 DeclarativeBase
│   │   │   └── session.py     # Engine configuration (PostgreSQL / SQLite)
│   │   ├── eval/              # Multimodal Model Evaluation Harness
│   │   │   ├── mock_models.py # Deterministic mock vision baselines
│   │   │   ├── openrouter_adapter.py # Live OpenRouter multimodal adapter
│   │   │   ├── prompts.py     # Pinned prompt versions (v1.0.0)
│   │   │   └── runner.py      # Evaluation runner and prediction persistence
│   │   ├── models/            # SQLAlchemy ORM Models
│   │   │   ├── challenge.py   # Challenge and ModelPrediction entities
│   │   │   ├── eval_run.py    # EvalRun summary tracking
│   │   │   ├── session.py     # GameSession and SessionAttempt entities
│   │   │   └── verification.py# VerificationAuditLog entity
│   │   ├── schemas/           # Pydantic Schemas (Public vs Private Ground Truth)
│   │   │   ├── challenge.py   # ChallengePublic, ChallengeReceipt, ChallengeCreate
│   │   │   └── scorecard.py   # ScorecardResponse, ModelComparisonItem
│   │   ├── scripts/           # Standalone Management Scripts
│   │   │   └── seed.py        # Database seeding CLI
│   │   ├── static/thumbnails/ # Bundled high-contrast SVG thumbnail pairs
│   │   └── main.py            # FastAPI Application entrypoint & CORS middleware
│   ├── data/
│   │   └── seed_challenges.json # 36 statistically verified seed challenges
│   ├── Dockerfile             # Multi-stage container definition
│   └── requirements.txt       # Python package dependencies
├── frontend/                  # React + TypeScript Frontend
│   ├── src/
│   │   ├── api/               # API Client & Data Contracts
│   │   │   ├── client.ts      # Axios/Fetch client with X-Session-ID headers
│   │   │   └── types.ts       # Shared TypeScript interfaces
│   │   ├── components/        # Reusable UI Components
│   │   │   ├── ChallengeCard.tsx # A/B Thumbnail cards with keyboard listeners
│   │   │   ├── Header.tsx     # Navigation header, round pill, and score counter
│   │   │   ├── ModelBadge.tsx # Model prediction, confidence, and reasoning
│   │   │   ├── ReceiptModal.tsx # Ground-truth receipt with p-value proof
│   │   │   ├── Scorecard.tsx  # Scorecard summary, Wilson CI, and model comparison
│   │   │   └── VerificationBadge.tsx # Glowing verified badge and SHA-256 audit
│   │   ├── pages/
│   │   │   └── GamePage.tsx   # Core game state machine orchestrator
│   │   ├── App.tsx            # Root application view
│   │   ├── index.css          # Tailwind CSS theme directives
│   │   └── main.tsx           # React DOM bootstrap
│   ├── Dockerfile             # Multi-stage Nginx/Vite container definition
│   ├── package.json           # Node.js dependencies
│   ├── tailwind.config.js     # Dark theme color token specifications (#121212)
│   └── vite.config.ts         # Vite build configuration and API reverse proxy
├── tests/                     # Automated Test Suites
│   ├── spec/                  # Contract / Specification Tests (Frozen)
│   │   ├── test_eval_runner.py       # Prompt pinning & deterministic model tests
│   │   ├── test_game_engine.py       # Unseen item selection & receipt tests
│   │   ├── test_ingestion.py         # Gate rejection & schema privacy tests
│   │   ├── test_scorecard.py         # Wilson interval & model comparison tests
│   │   ├── test_significance_gate.py # Z-test math & sample size gate tests
│   │   └── test_verification.py      # 3-round state machine & audit log tests
│   ├── integration/           # End-to-End Integration Tests
│   │   └── test_e2e_gameplay.py      # Complete 30-item simulated player run
│   └── test_health.py         # Healthcheck and CORS verification
├── docker-compose.yml         # Local stack orchestration (PostgreSQL, Backend, Frontend)
├── .env.example               # Reference environment variables
└── README.md                  # System overview and quick start guide
```

---

## 3. Key Design Invariants

1. **Information Hiding**:
   - `ChallengePublic` strictly conceals ground truth metrics (`winning_variant`, `ctr_a`, `ctr_b`, `clicks_a`, `clicks_b`, `impressions_a`, `impressions_b`, `z_score`, `p_value`).
   - Ground truth is only accessible via `AttemptReceipt` returned after a valid user attempt is committed to the database.

2. **Backend-Enforced Anti-Luck**:
   - `get_next_unseen_challenge` executes a SQL subquery filtering all challenges previously recorded in `session_attempts` for that session.
   - The frontend never controls or caches question sequencing.

3. **Deterministic Evaluation Harness**:
   - Deterministic mock vision models (`mock-frontier-v1`, `mock-compact-v1`, `mock-heuristic-v1`) use SHA-256 digests over `challenge_id + model_name + prompt_version` to guarantee identical predictions across all client runs without external API dependencies.

4. **Tamper-Evident Verification**:
   - Verification status requires $\ge 22/30$ correct answers across 3 rounds of 10 unseen challenges.
   - Completed runs generate a SHA-256 HMAC digest in `VerificationAuditLog` certifying the authenticity of the verification run.
