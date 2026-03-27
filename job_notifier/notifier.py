"""
notifier.py
Sends concise Telegram alerts — just enough to decide if the link is worth clicking.
"""
import logging
import requests
import config

logger = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_job_alert(job: dict, match: dict) -> bool:
    score = match.get("score", 0)
    emoji = "🔥" if score >= 90 else "✅"
    url   = job.get("url", "#")

    message = (
        f"{emoji} *{score}% match*\n"
        f"{_esc(job.get('title', 'N/A'))} — {_esc(job.get('company', 'N/A'))}\n"
        f"📍 {_esc(job.get('location', 'N/A'))} · {_esc(job.get('source', ''))}\n"
        f"[View Job]({url})"
    )
    return _send(message)


def send_summary(total_checked: int, matched_count: int) -> bool:
    if matched_count == 0:
        msg = f"🔍 Scanned {total_checked} jobs — no new matches above {config.MATCH_THRESHOLD}%\\."
    else:
        msg = f"🔍 Scanned {total_checked} jobs — {matched_count} match alert\\(s\\) sent\\."
    return _send(msg)


def send_startup_message() -> bool:
    msg = (
        "🤖 *Job Notifier started*\n"
        f"Threshold: {config.MATCH_THRESHOLD}% · Every {config.CHECK_INTERVAL_HOURS}h\n"
        "Watching LinkedIn, Naukri, Indeed"
    )
    return _send(msg)


def _send(text: str) -> bool:
    url = TELEGRAM_API.format(token=config.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id":    config.TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def _esc(text: str) -> str:
    if not text:
        return ""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text