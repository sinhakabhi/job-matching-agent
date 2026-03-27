"""
store.py
Tracks which job IDs have already been notified about,
so the agent never sends duplicate alerts.
Persists to a local JSON file.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STORE_FILE = Path(__file__).parent / "seen_jobs.json"


def load_seen() -> set:
    try:
        if STORE_FILE.exists():
            data = json.loads(STORE_FILE.read_text())
            return set(data.get("seen", []))
    except Exception as e:
        logger.warning(f"Could not load seen_jobs.json: {e}")
    return set()


def save_seen(seen: set) -> None:
    try:
        STORE_FILE.write_text(json.dumps({"seen": list(seen)}, indent=2))
    except Exception as e:
        logger.error(f"Could not save seen_jobs.json: {e}")


def is_new(job_id: str, seen: set) -> bool:
    return job_id not in seen


def mark_seen(job_id: str, seen: set) -> None:
    seen.add(job_id)