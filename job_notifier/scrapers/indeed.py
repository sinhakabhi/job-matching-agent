"""
scrapers/indeed.py
Indeed is fully bot-blocked. This module now scrapes Glassdoor job listings
via their public search page as a replacement.
"""
import time
import hashlib
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://www.glassdoor.co.in/Job/jobs.htm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.glassdoor.co.in/",
}


def scrape(keywords: List[str], locations: List[str], max_per_query: int = 10) -> List[dict]:
    session = requests.Session()
    # Grab cookies first
    try:
        session.get("https://www.glassdoor.co.in/", headers=HEADERS, timeout=10)
    except Exception:
        pass

    jobs = []
    seen_ids = set()

    for keyword in keywords:
        for location in locations:
            try:
                params = {
                    "sc.keyword": keyword,
                    "locT":       "N",
                    "locId":      "115" if "India" in location else "",
                    "jobType":    "",
                    "fromAge":    "1",    # last 1 day
                    "minSalary":  "0",
                    "includeNoSalaryJobs": "true",
                    "radius":     "100",
                    "cityId":     "",
                    "minRating":  "0.0",
                    "industryId": "",
                    "sgocId":     "",
                    "seniorityType": "",
                    "companyId":  "",
                    "employerSizes": "0",
                    "applicationType": "0",
                    "remoteWorkType": "0",
                }
                resp = session.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("li", class_=lambda c: c and "JobsList_jobListItem" in c)

                count = 0
                for card in cards:
                    if count >= max_per_query:
                        break
                    job = _parse_card(card)
                    if job and job["id"] not in seen_ids:
                        seen_ids.add(job["id"])
                        job["source"] = "Glassdoor"
                        jobs.append(job)
                        count += 1

                time.sleep(2)

            except Exception as e:
                logger.warning(f"Glassdoor scrape failed [{keyword} | {location}]: {e}")

    logger.info(f"Glassdoor: found {len(jobs)} jobs")
    return jobs


def _parse_card(card) -> Optional[dict]:
    try:
        title_tag   = card.find("a", class_=lambda c: c and "JobCard_jobTitle" in c) or \
                      card.find("a", {"data-test": "job-title"})
        company_tag = card.find("span", class_=lambda c: c and "EmployerProfile_compactEmployerName" in c) or \
                      card.find("div", class_=lambda c: c and "JobCard_companyName" in c)
        location_tag = card.find("div", class_=lambda c: c and "JobCard_location" in c)

        title   = title_tag.get_text(strip=True)   if title_tag   else "N/A"
        company = company_tag.get_text(strip=True)  if company_tag  else "N/A"

        href = title_tag["href"] if title_tag and title_tag.get("href") else ""
        url  = f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href

        job_id = hashlib.md5(f"{title}{company}".encode()).hexdigest()[:12]

        return {
            "id":          f"gd_{job_id}",
            "title":       title,
            "company":     company,
            "location":    location_tag.get_text(strip=True) if location_tag else "N/A",
            "url":         url,
            "posted_date": "",
            "description": "",
        }
    except Exception:
        return None