"""
scrapers/linkedin.py
Uses LinkedIn's public guest jobs API — no login required.
"""
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

GUEST_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def scrape(keywords: List[str], locations: List[str], max_per_query: int = 10) -> List[dict]:
    jobs = []
    seen_ids = set()

    for keyword in keywords:
        for location in locations:
            try:
                params = {
                    "keywords": keyword,
                    "location": location,
                    "start": 0,
                    "count": max_per_query,
                    "sortBy": "DD",          # date descending
                    "f_TPR": "r86400",       # last 24 hours  (change to r604800 for 1 week)
                }
                print(f"Calling LinkedIn endpoint: {GUEST_SEARCH_URL} with params={params}")
                resp = requests.get(GUEST_SEARCH_URL, params=params, headers=HEADERS, timeout=15)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("li")

                for card in cards:
                    job = _parse_card(card)
                    if job and job["id"] not in seen_ids:
                        seen_ids.add(job["id"])
                        job["source"] = "LinkedIn"
                        jobs.append(job)

                time.sleep(2)   # polite delay between requests

            except Exception as e:
                logger.warning(f"LinkedIn scrape failed [{keyword} | {location}]: {e}")

    logger.info(f"LinkedIn: found {len(jobs)} jobs")
    return jobs


def _parse_card(card) -> Optional[dict]:
    try:
        job_id_tag = card.find("div", {"data-entity-urn": True})
        if not job_id_tag:
            return None

        urn = job_id_tag.get("data-entity-urn", "")
        job_id = urn.split(":")[-1] if urn else None
        if not job_id:
            return None

        title_tag   = card.find("h3", class_=re.compile("base-search-card__title"))
        company_tag = card.find("h4", class_=re.compile("base-search-card__subtitle"))
        location_tag = card.find("span", class_=re.compile("job-search-card__location"))
        link_tag    = card.find("a", class_=re.compile("base-card__full-link"))
        date_tag    = card.find("time")

        description_preview = card.find("p", class_=re.compile("job-search-card__snippet"))

        return {
            "id":          f"li_{job_id}",
            "title":       title_tag.get_text(strip=True)    if title_tag    else "N/A",
            "company":     company_tag.get_text(strip=True)  if company_tag  else "N/A",
            "location":    location_tag.get_text(strip=True) if location_tag else "N/A",
            "url":         link_tag["href"].split("?")[0]    if link_tag     else "",
            "posted_date": date_tag.get("datetime", "")      if date_tag     else "",
            "description": description_preview.get_text(strip=True) if description_preview else "",
        }
    except Exception:
        return None