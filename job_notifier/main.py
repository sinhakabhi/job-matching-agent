"""
main.py
Pipeline:
  1. Scrape LinkedIn
  2. Deduplicate against seen_jobs.json
  3. Pre-filter by title/keyword (fast, free)
  4. Batch score remaining jobs with Gemini (5 per API call)
  5. Notify via Telegram for matches >= threshold
  6. Sleep and repeat
"""
import sys
import time
import logging

import config
import store
import notifier
from resume_parser import load_resume
from prefilter import filter_jobs
from matcher import score_jobs
from scrapers.linkedin import scrape as scrape_linkedin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_profile() -> str:
    if config.RESUME_PATH:
        try:
            text = load_resume(config.RESUME_PATH)
            logger.info(f"Resume loaded from '{config.RESUME_PATH}' ({len(text)} chars)")
            return text
        except FileNotFoundError:
            logger.warning(f"Resume not found at '{config.RESUME_PATH}' — using fallback profile")
        except Exception as e:
            logger.warning(f"Resume parse failed: {e} — using fallback profile")

    logger.info("Using USER_PROFILE_FALLBACK from config.py")
    return config.USER_PROFILE_FALLBACK.strip()


def run_cycle(resume_text: str) -> None:
    logger.info("=" * 55)
    logger.info("Starting job scan cycle")
    logger.info("=" * 55)

    # ── 1. Scrape ──────────────────────────────────────────
    try:
        all_jobs = scrape_linkedin(
            config.SEARCH_KEYWORDS,
            config.LOCATIONS,
            config.MAX_RESULTS_PER_QUERY,
        )
    except Exception as e:
        logger.error(f"LinkedIn scraper failed: {e}")
        all_jobs = []

    logger.info(f"Scraped: {len(all_jobs)} jobs from LinkedIn")

    # ── 2. Deduplicate ─────────────────────────────────────
    seen = store.load_seen()
    new_jobs = [j for j in all_jobs if store.is_new(j["id"], seen)]
    logger.info(f"New (not seen before): {len(new_jobs)}")

    if not new_jobs:
        logger.info("Nothing new — skipping scoring")
        notifier.send_summary(len(all_jobs), 0)
        return

    # Mark all new jobs as seen now (before scoring) so we don't
    # re-process them even if the run is interrupted mid-way
    for job in new_jobs:
        store.mark_seen(job["id"], seen)
    store.save_seen(seen)

    # ── 3. Pre-filter ──────────────────────────────────────
    relevant_jobs, excluded = filter_jobs(new_jobs)
    logger.info(f"After pre-filter: {len(relevant_jobs)} relevant, {excluded} excluded (irrelevant titles)")

    if not relevant_jobs:
        logger.info("No relevant jobs after pre-filter")
        notifier.send_summary(len(all_jobs), 0)
        return

    # ── 4. Batch score with Gemini ─────────────────────────
    logger.info(f"Sending {len(relevant_jobs)} jobs to Gemini for scoring (batches of 5)...")
    scored_jobs = score_jobs(relevant_jobs, resume_text)

    # ── 5. Notify matches ──────────────────────────────────
    matched_count = 0
    for job in scored_jobs:
        match = job.get("match", {})
        score = match.get("score", 0)
        logger.info(f"  {score:3d}%  {job['title']} @ {job['company']}")

        if score >= config.MATCH_THRESHOLD:
            ok = notifier.send_job_alert(job, match)
            if ok:
                matched_count += 1

    notifier.send_summary(len(all_jobs), matched_count)
    logger.info(f"Cycle done — {matched_count} match(es) notified")


def main() -> None:
    logger.info("Job Notifier Agent starting up...")
    resume_text = load_profile()
    if not resume_text:
        logger.error("No profile available — exiting")
        sys.exit(1)

    notifier.send_startup_message()

    while True:
        try:
            run_cycle(resume_text)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)

        logger.info(f"Sleeping {config.CHECK_INTERVAL_HOURS}h until next scan...\n")
        time.sleep(config.CHECK_INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()