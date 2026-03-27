# ============================================================
#  config.py  —  Load configuration and secrets from .env
# ============================================================

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

# ------ Telegram ------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ------ Anthropic ------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ------ Resume ------
RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

# ------ Fallback profile (used only if RESUME_PATH is empty or fails) ------
USER_PROFILE_FALLBACK = """
Total experience: 5 years
Current role: Software Engineer
 
Skills: Python, Java, Spring Boot, FastAPI, PostgreSQL, Redis,
Docker, Kubernetes, AWS (EC2, S3, RDS, Lambda), Microservices, REST APIs
 
Preferred roles: Senior Backend Engineer, Senior Software Engineer, Software Engineer 2
Open to: Senior SWE, Staff SWE
Not interested in: Pure frontend, data analyst, QA roles
"""
 
# ------ Job Search ------
SEARCH_KEYWORDS = [
    "Senior Software Engineer",
    "Software Engineer",
    "SDE2",
    "SDE 2",
    "SDE3",
    "SDE 3",
    "Backend Engineer",
    "Platform Engineer",
    "Senior Backend Engineer",
    "Senior Software Engineer Java",
    "Senior Software Engineer Python",
]
 
LOCATIONS = ["India", "Bangalore", "Hyderabad", "Remote India"]
MIN_YEARS_EXPERIENCE = 4  # use this to prefer jobs aligned to your experience level
 
MATCH_THRESHOLD       = 80   # alert only for jobs scoring >= this
CHECK_INTERVAL_HOURS  = 3    # how often the agent runs
MAX_RESULTS_PER_QUERY = 10   # per keyword per location (LinkedIn)
 