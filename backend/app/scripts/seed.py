"""Database seed script for Humark challenges.

Loads and ingests benchmark challenges from backend/data/seed_challenges.json.
Enforces ADR-002 statistical significance hard gate during ingestion.
"""

import json
import logging
import sys
from pathlib import Path

from app.core.ingestion import ingest_batch
from app.db.session import SessionLocal, init_db
from app.eval.runner import run_baselines_for_all_challenges
from app.models.challenge import Challenge

logger = logging.getLogger("humark.seed")


def get_seed_file_path() -> Path:
    """Resolve path to seed_challenges.json across different runtime environments."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "data" / "seed_challenges.json",
        Path.cwd() / "backend" / "data" / "seed_challenges.json",
        Path.cwd() / "data" / "seed_challenges.json",
        Path("/app/data/seed_challenges.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def seed_challenges_data(db=None) -> int:
    """Execute ingestion and baseline precomputation for all seed challenges."""
    seed_file = get_seed_file_path()
    if not seed_file.exists():
        logger.error(f"Error: Seed file not found at {seed_file}")
        return 1

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    challenges = data if isinstance(data, list) else data.get("challenges", [])

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        summary = ingest_batch(challenges, db, precompute_baselines=True)
        if summary.rejections:
            logger.error("Seed rejections encountered:")
            for rej in summary.rejections:
                logger.error(f"  - [{rej['index']}] {rej['title']}: {rej['reason']}")
            return 1
        run_baselines_for_all_challenges(db)
        return 0
    finally:
        if should_close:
            db.close()


def auto_seed_if_empty(db=None) -> bool:
    """Auto-seed database if challenge catalog is currently empty."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        challenge_count = db.query(Challenge).count()
        if challenge_count == 0:
            logger.info("Challenge table empty; running automated benchmark seed...")
            res = seed_challenges_data(db)
            return res == 0
        return False
    except Exception as exc:
        logger.warning(f"Auto-seed check encountered non-fatal error: {exc}")
        return False
    finally:
        if should_close:
            db.close()


def run_seed() -> int:
    """Execute database seeding."""
    print("=" * 60)
    print("HUMARK BENCHMARK SEED RUNNER")
    print("=" * 60)

    # Initialize database tables
    print("Initializing database tables...")
    init_db()

    seed_file = get_seed_file_path()
    if not seed_file.exists():
        print(f"Error: Seed file not found at {seed_file}", file=sys.stderr)
        return 1

    print(f"Loading seed file from {seed_file}...")
    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    challenges = data if isinstance(data, list) else data.get("challenges", [])
    print(f"Discovered {len(challenges)} candidate challenge items.")

    db = SessionLocal()
    try:
        summary = ingest_batch(challenges, db, precompute_baselines=True)
        print("-" * 60)
        print(f"Total Submitted: {summary.total_submitted}")
        print(f"Ingested:        {summary.ingested_count}")
        print(f"Rejected:        {summary.rejected_count}")
        print("-" * 60)

        if summary.rejections:
            print("Rejection details:")
            for rej in summary.rejections:
                print(f"  - [{rej['index']}] {rej['title']}: {rej['reason']}")
            return 1

        print("Verifying baseline model evaluations across all benchmark items...")
        eval_summary = run_baselines_for_all_challenges(db)
        print(f"Total Challenges:    {eval_summary['total_challenges']}")
        print(f"Predictions Created: {eval_summary['predictions_created']}")
        print(f"Predictions Reused:  {eval_summary['predictions_reused']}")
        print(f"Models Active:       {', '.join(eval_summary['models'])}")
        print("-" * 60)
        print("Seeding completed successfully with zero rejections and pre-computed baselines.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(run_seed())
