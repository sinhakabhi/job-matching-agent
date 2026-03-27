"""
matcher.py
Scores jobs against the resume using Gemini.
Batches 5 jobs per API call and keeps requests below 10 per minute.
"""
import json
import time
import logging
import requests
from requests.exceptions import HTTPError, RequestException
import config

logger = logging.getLogger(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-lite:generateContent?key={api_key}"
)

BATCH_SIZE            = 5    # jobs per Gemini call
DELAY_BETWEEN_BATCHES = 7    # seconds — keeps us under 10 Gemini requests per minute
MAX_RETRIES           = 3
BACKOFF_SECONDS       = 60


def score_jobs(jobs: list, resume_text: str) -> list:
    """
    Score a list of jobs against the resume.
    Returns the same list with a 'match' dict added to each job.
    Processes in batches to minimise API calls.
    """
    results = []
    batches = [jobs[i:i+BATCH_SIZE] for i in range(0, len(jobs), BATCH_SIZE)]

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"Scoring batch {batch_num}/{len(batches)} ({len(batch)} jobs)...")
        scores = _score_batch(batch, resume_text)

        for job, score_data in zip(batch, scores):
            results.append({**job, "match": score_data})

        # Rate limit pause between batches (skip after last batch)
        if batch_num < len(batches):
            time.sleep(DELAY_BETWEEN_BATCHES)

    return results


def _score_batch(jobs: list, resume_text: str, attempt: int = 1) -> list:
    """Score a batch of jobs in a single Gemini call. Returns list of score dicts."""
    jobs_text = ""
    for i, job in enumerate(jobs):
        jobs_text += (
            f"\nJOB {i+1}:\n"
            f"Title: {job.get('title', 'N/A')}\n"
            f"Company: {job.get('company', 'N/A')}\n"
            f"Location: {job.get('location', 'N/A')}\n"
            f"Description: {job.get('description', 'N/A')[:600]}\n"
        )

    prompt = f"""You are a technical recruiter. Score each job against this candidate's resume.

## Candidate Resume
{resume_text.strip()[:2500]}

## Candidate preferences
- Preferred locations: {', '.join(config.LOCATIONS)}
- Candidate experience: {config.MIN_YEARS_EXPERIENCE}-{config.MIN_YEARS_EXPERIENCE + 1} years
- Prefer senior-level software engineering roles such as SDE2, SDE3, or equivalent

## Jobs to Score
{jobs_text}

## Instructions
Use the resume as the authoritative source for what work this candidate actually does, their skills, seniority, and background.
Prefer product-led or product-engineering roles, and deprioritize consulting/service/contracting roles.
Prefer jobs that clearly align with the resume and preferred locations.
If a job is outside the preferred locations or appears to be a poorer fit for the candidate's experience level, score it lower.

Score each job 0-100 for candidate fit:
- 90-100: Near-perfect fit
- 80-89: Strong fit, worth applying
- 60-79: Partial fit
- Below 60: Poor fit

Respond ONLY with a JSON array with exactly {len(jobs)} objects, no markdown:
[
  {{"score": <int>, "reason": "<1 sentence>"}},
  ...
]"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 800},
    }

    try:
        resp = requests.post(
            GEMINI_URL.format(api_key=config.GEMINI_API_KEY),
            json=payload,
            timeout=30,
        )

        if resp.status_code == 429:
            raise HTTPError("429 Too Many Requests", response=resp)

        resp.raise_for_status()
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)

        # Ensure we got back the right number of results
        if len(parsed) != len(jobs):
            logger.warning(f"Gemini returned {len(parsed)} scores for {len(jobs)} jobs — padding with zeros")
            while len(parsed) < len(jobs):
                parsed.append({"score": 0, "reason": "Missing score"})

        for item in parsed:
            item["score"] = int(item.get("score", 0))

        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini batch response: {e}")
        return [{"score": 0, "reason": "Parsing error"}] * len(jobs)
    except HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 429 and attempt < MAX_RETRIES:
            wait = BACKOFF_SECONDS * attempt
            logger.warning(
                f"Gemini rate limited (429) on attempt {attempt}/{MAX_RETRIES}. Waiting {wait}s before retry..."
            )
            time.sleep(wait)
            return _score_batch(jobs, resume_text, attempt + 1)

        logger.error(f"Gemini HTTP error [{status}]: {e}")
        return [{"score": 0, "reason": "API error"}] * len(jobs)
    except RequestException as e:
        logger.error(f"Gemini request error: {e}")
        if attempt < MAX_RETRIES:
            wait = BACKOFF_SECONDS * attempt
            logger.warning(
                f"Retrying Gemini request after {wait}s (attempt {attempt}/{MAX_RETRIES})..."
            )
            time.sleep(wait)
            return _score_batch(jobs, resume_text, attempt + 1)
        return [{"score": 0, "reason": "API error"}] * len(jobs)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return [{"score": 0, "reason": "API error"}] * len(jobs)