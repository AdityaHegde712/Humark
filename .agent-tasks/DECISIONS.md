# Architecture Decision Records (ADRs)

## ADR-001: Monorepo Architecture & Stack Selection
- **Status**: Accepted
- **Context**: Humark is an evaluation harness and portfolio project demonstrating AI infrastructure, statistical rigor, and applied ML engineering.
- **Decision**: Monorepo with FastAPI (Python 3.11+), PostgreSQL 16, React 18+ (TypeScript, Vite, Tailwind CSS, Lucide Icons), and Docker Compose.
- **Consequences**: Single repository, straightforward local development via `docker compose up`, zero Kubernetes overhead, unified test directory (`tests/`).

## ADR-002: Statistical Significance Hard Gate (Two-Proportion Z-Test)
- **Status**: Accepted
- **Context**: Challenges require statistically defensible ground truth to benchmark humans against models without noise or false positive winners.
- **Decision**: Ingestion rejects any challenge where variant sample size $N < 20,000$ impressions or two-tailed two-proportion z-test $p \ge 0.05$. Exact $z$ score, $p$-value, and standard error must be computed and stored in provenance metadata.
- **Consequences**: Flawed or under-powered A/B tests cannot enter active challenge pools.

## ADR-003: Model Baseline Runner & Deterministic Mocking
- **Status**: Accepted
- **Context**: The app must run completely out-of-the-box without requiring paid API keys, but support frontier multimodal models when keys are supplied.
- **Decision**: Implement a deterministic mock vision model baseline that generates stable, reproducible predictions, tokens, and latency based on challenge hashes. Support LiteLLM / provider adapters via pinned prompt templates and versioned evaluation runs. All baseline predictions are pre-computed in Postgres and hidden from users until after they answer.
- **Consequences**: Zero-dependency offline verification and grading; reproducible model evaluation logs.

## ADR-004: Anti-Luck Verification Protocol
- **Status**: Accepted
- **Context**: Prevent lucky guessing and ensure skill verification across rounds.
- **Decision**: 3 sequential rounds of 10 challenges each (30 challenges total). Unseen-item selection is strictly enforced in PostgreSQL using session attempt history. Verification requires $>70\%$ cumulative accuracy ($\ge 22/30$ correct answers) across all 3 rounds.
- **Consequences**: Users cannot replay questions to inflate scores.

## ADR-005: Scorecard Confidence Telemetry (Wilson Score Interval)
- **Status**: Accepted
- **Context**: Raw percentages on small sample sizes (e.g. 7/10 = 70%) misrepresent statistical confidence.
- **Decision**: Scorecards compute Wilson score intervals at 95% confidence level alongside raw accuracy, accompanied by sample-size confidence labels.
- **Consequences**: Rigorous statistical presentation matching AI evaluation harness standards.

## ADR-006: Dark Flat UI Theme & Component Architecture
- **Status**: Accepted
- **Context**: Replicate the feel of the Lovable demo while adhering to User Decision Profile.
- **Decision**: Dark minimal flat UI (`#121212` background, `#262626` hairline borders, `#e0e0e0` text, high-contrast accent), Tailwind CSS, Lucide icons, responsive card layouts, no Bootstrap.
- **Consequences**: Clean, fast, modern developer-centric UX.

## ADR-007: Quick Mode Git Workflow
- **Status**: Accepted
- **Context**: Streamline development velocity and task commits.
- **Decision**: Locked to Quick Mode: single `main` branch, linear commits, no dev/feature branches.
- **Consequences**: Direct commits to main after each verified task phase.

## ADR-008: OpenRouter LLM Provider Target
- **Status**: Accepted
- **Context**: Frontier multimodal model benchmarking needs standardized access to vision models without managing multiple vendor SDKs.
- **Decision**: OpenRouter (`OPENROUTER_API_KEY`) is the primary provider target for live frontier models; deterministic mock runner remains default zero-key runner. Real keys are never written to version control.
- **Consequences**: Flexible multi-model access including free-tier models without vendor lock-in.

## ADR-009: Automated Database Seeding & Startup Lifecycle
- **Status**: Accepted
- **Context**: Zero-setup developer and evaluator experience requires benchmark challenges and baseline predictions to be ready immediately on `docker compose up` without requiring manual database migration or seed commands.
- **Decision**: Implement dual auto-seed guarantees:
  1. `docker-compose.yml` invokes `sh -c "python -m app.scripts.seed && uvicorn app.main:app ..."` on startup.
  2. `backend/app/main.py` FastAPI `lifespan` checks `auto_seed_if_empty()` on startup, ensuring that standalone server runs and test runners also seed automatically when encountering an unseeded database.
  All 36 seed challenges and 108 model predictions are ingested idempotently.
- **Consequences**: Out-of-the-box playable experience on clean clone.

## ADR-010: Top 2% Human Edge Percentile Distribution Model
- **Status**: Accepted
- **Context**: Replicate the central finding of WONO's empirical study (7,030 humans vs Frontier AI): frontier AI outperformed 98% of humans, but top ~2% of humans beat it by a wide margin.
- **Decision**: Model human baseline distribution as a Gaussian $\mathcal{N}(\mu=0.528, \sigma=0.094)$ anchored on empirical trial results. Compute user percentile ranking, distance to frontier AI, and render an interactive SVG bell curve visualization on the scorecard.
- **Consequences**: Connects user scorecard directly to the viral benchmark narrative.

## ADR-011: Strict Asset XML Escaping & Seed Stratification
- **Status**: Accepted
- **Context**: Visual benchmark assets must pass strict XML parsers, and evaluation seed datasets must be stratified 50/50 across choice variants to prevent heuristic positional bias.
- **Decision**: All dynamic text within SVG assets must escape reserved XML characters (`&amp;`). Seed challenges must maintain equal ground truth distribution (18 Variant A / 18 Variant B) across active challenge tracks. Frontend confidence models must tolerate both canonical naming (`lower`/`upper`) and legacy interval keys.
- **Consequences**: Zero SVG XML parse errors, unbiased evaluation baselines, and robust scorecard metrics without NaN artifacts.
