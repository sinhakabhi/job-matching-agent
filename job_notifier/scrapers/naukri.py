"""
scrapers/naukri.py
Naukri job search using their frontend API with correct headers.
"""
import time
import logging
import traceback
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.naukri.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":           "application/json",
    "Accept-Language":  "en-US,en;q=0.9",
    "Referer":          "https://www.naukri.com/",
    "Origin":           "https://www.naukri.com",
    "appid":            "109",
    "systemid":         "109",
    "gid":              "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
    "x-requested-with": "XMLHttpRequest",
}

LOCATION_MAP = {
    "India":        "",
    "Bangalore":    "bangalore",
    "Hyderabad":    "hyderabad",
    "Mumbai":       "mumbai",
    "Delhi":        "delhi",
    "Remote India": "",
}


def scrape(keywords: List[str], locations: List[str], max_per_query: int = 10) -> List[dict]:
    # Start a session to pick up cookies first (avoids 406)
    session = requests.Session()
    try:
        session.get("https://www.naukri.com/", headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html",
        }, timeout=10)
    except Exception:
        pass  # best-effort cookie grab

    jobs = []
    seen_ids = set()

    for keyword in keywords:
        for location in locations:
            try:
                location_slug = LOCATION_MAP.get(location, location.lower())
                params = {
                    # "noOfResults": max_per_query,
                    # "urlType":     "search_by_key_loc",
                    # "searchType":  "adv",
                    "keyword":     keyword,
                    # "location":    location_slug,
                    "pageNo":      1,
                    # "sort":        "recency",
                    # "experience":  5,
                }
                resp = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("jobDetails", []):
                    job = _parse_item(item)
                    if job and job["id"] not in seen_ids:
                        seen_ids.add(job["id"])
                        job["source"] = "Naukri"
                        jobs.append(job)

                time.sleep(2)

            except Exception as e:
                traceback.print_exc()
                logger.warning(f"Naukri scrape failed [{keyword} | {location}]: {e}")

    logger.info(f"Naukri: found {len(jobs)} jobs")
    return jobs


def _parse_item(item: dict) -> Optional[dict]:
    try:
        job_id = str(item.get("jobId") or item.get("id") or "")
        if not job_id:
            return None

        skills = item.get("tagsAndSkills", "") or ""
        if isinstance(skills, list):
            skills = ", ".join(skills)

        return {
            "id":          f"nk_{job_id}",
            "title":       item.get("title", "N/A"),
            "company":     item.get("companyName", "N/A"),
            "location":    item.get("placeholders", [{}])[0].get("label", "N/A") if item.get("placeholders") else "N/A",
            "url":         item.get("jdURL", "https://www.naukri.com"),
            "posted_date": item.get("createdDate", ""),
            "description": f"{item.get('jobDescription', '')} | Skills: {skills}"[:800],
        }
    except Exception:
        return None