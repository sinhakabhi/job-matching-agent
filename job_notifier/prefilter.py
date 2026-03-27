"""
prefilter.py
Cheap title-based filter that cuts irrelevant jobs BEFORE sending to Gemini.
Avoids wasting API calls on React developers, QA engineers, data analysts, etc.
"""

import config

# If ANY of these appear in the title, job is excluded immediately
EXCLUDE_TITLE_KEYWORDS = [
    "react", "angular", "vue", "frontend", "front-end", "front end",
    "ios", "android", "mobile", "flutter", "swift", "kotlin",
    "qa ", "quality assurance", "quality engineer", "test engineer", "test automation", "sdet", "automation tester",
    "data analyst", "data scientist", "machine learning engineer", "ml engineer",
    "product manager", "program manager", "scrum master", "project manager",
    "ui developer", "ui engineer", "ux ", "designer",
    "devops engineer",   # keep platform/infra but skip pure devops titles
    "junior", "fresher", "entry level", "intern",
    "cobol", "mainframe", "sap", "salesforce", "php", "wordpress",
    "ruby", ".net developer", "c# developer",
]

# At least ONE of these must appear somewhere in title OR description
REQUIRE_ANY_KEYWORD = [
    "backend", "back-end", "back end",
    "software engineer", "software developer", "sde", "swe",
    "platform", "infrastructure", "distributed", "microservice",
    "api", "cloud", "aws", "kubernetes", "docker",
    "fullstack", "full stack", "full-stack",
    "senior", "staff", "principal", "lead",
]

SKILL_KEYWORDS = ["python", "java", "django", "spring", "springboot", "fastapi", "postgresql", "redis", "kubernetes", "aws", "lambda"]

EXCLUDE_COMPANY_KEYWORDS = [
    "consulting", "services", "outsourcing", "staffing", "vendor",
    "implementation", "contract", "temporary", "third party", "client-facing",
]

PREFERRED_COMPANY_TERMS = [
    "product", "platform", "saas", "cloud", "developer platform",
    "security", "analytics", "infrastructure", "enterprise", "fintech",
    "marketplace", "ai", "machine learning", "data",
]


def _location_matches_preference(location: str) -> bool:
    location = location.lower()
    preferred_locations = [loc.lower() for loc in config.LOCATIONS]
    remote_allowed = any("remote" in loc for loc in preferred_locations)

    if "remote" in location:
        return remote_allowed

    for pref in preferred_locations:
        if pref and pref in location:
            return True

    return False


def _is_product_focused(job: dict) -> bool:
    text = " ".join([
        (job.get("title") or ""),
        (job.get("description") or ""),
        (job.get("company") or ""),
    ]).lower()

    for kw in PREFERRED_COMPANY_TERMS:
        if kw in text:
            return True

    return False


def _is_service_or_contract_role(job: dict) -> bool:
    text = " ".join([
        (job.get("title") or ""),
        (job.get("description") or ""),
        (job.get("company") or ""),
    ]).lower()

    for kw in EXCLUDE_COMPANY_KEYWORDS:
        if kw in text:
            return True

    return False


def is_relevant(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    combined = f"{title} {description}"

    # Hard exclude
    for kw in EXCLUDE_TITLE_KEYWORDS:
        if kw in title:
            return False

    if _is_service_or_contract_role(job):
        return False

    # Drop jobs with a location outside preferred config locations,
    # but keep jobs if location is not provided.
    if location and not _location_matches_preference(location):
        return False

    # Must match at least one positive role keyword
    for kw in REQUIRE_ANY_KEYWORD:
        if kw in combined:
            break
    else:
        return False

    # Require at least one of the core skills we want to see in the job.
    if not any(kw in combined for kw in SKILL_KEYWORDS):
        return False

    return True


def filter_jobs(jobs: list) -> tuple[list, int]:
    """
    Returns (filtered_jobs, excluded_count)
    """
    relevant = [j for j in jobs if is_relevant(j)]
    excluded = len(jobs) - len(relevant)
    return relevant, excluded