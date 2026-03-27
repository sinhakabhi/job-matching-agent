# Job Matching Agent

A Python agent that scrapes LinkedIn, Naukri, and Indeed for job postings,
scores each one against your resume using Google Gemini AI (free), and sends
you a Telegram alert when a match is ≥80%.

---

## Project Structure

```
.
├── .env               # Secrets and runtime config (ignored by git)
├── README.md
├── requirements.txt   # Python dependencies
└── job_notifier/
    ├── main.py            # Orchestrator + scheduler loop
    ├── config.py          # Search preferences, score thresholds, locations
    ├── matcher.py         # Gemini AI job scoring
    ├── notifier.py        # Telegram notifications
    ├── resume_parser.py   # Reads your PDF/DOCX resume
    ├── store.py           # Deduplication (seen_jobs.json)
    └── scrapers/
        ├── __init__.py
        ├── linkedin.py    # LinkedIn guest jobs API
        ├── naukri.py      # Naukri JSON search API
        └── indeed.py      # Indeed HTML scraper
```

---

## Setup (10 minutes)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Get your free Gemini API key

Gemini 1.5 Flash is completely free — no credit card required.

1. Go to **[aistudio.google.com](https://aistudio.google.com)**
2. Sign in with your Google account
3. Click **Get API Key** in the left sidebar
4. Click **Create API key in new project**
5. Copy the key — it looks like `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXX`
6. Paste it into `.env` as `GEMINI_API_KEY=`

> **Free tier limits:** 15 requests/minute · 1,500 requests/day
> This is well under what the agent needs running every 3 hours.

---

### 3. Create a Telegram bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `Job Notifier`) and a username (e.g. `myjobnotifier_bot`)
4. BotFather will reply with a token like:
   ```
   123456789:ABCdefGhIJKlmNoPQRstuVWXyz
   ```
5. Paste it into `.env` as `TELEGRAM_BOT_TOKEN=`

---

### 4. Get your Telegram Chat ID

1. Search for your new bot on Telegram and send it any message (e.g. `hello`)
2. Open this URL in your browser — replace `TOKEN` with your bot token:
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
3. You'll see a JSON response. Find this section:
   ```json
   "chat": { "id": 987654321 }
   ```
4. That number is your `TELEGRAM_CHAT_ID` — paste it into `.env` as `TELEGRAM_CHAT_ID=`

---

### 5. Add your resume

Drop your resume file into the project root or a subfolder.
Supported formats: `.pdf`, `.docx`, `.txt`

Update `.env`:
```bash
RESUME_PATH=resume.pdf
```

If you keep the file in another folder, use the relative path, for example:
```bash
RESUME_PATH=./job_notifier/resume.pdf
```

The agent reads your resume once at startup and uses the full text for
every job match — no manual profile editing needed.

---

### 6. Configure your search preferences

Open `config.py` and update:

```python
SEARCH_KEYWORDS = [
    "Backend Engineer Python",
    "Senior Software Engineer Microservices",
    # add or remove keywords as needed
]

LOCATIONS = ["Bangalore", "Hyderabad", "Remote India"]

MATCH_THRESHOLD = 80   # only notify for jobs scoring 80% or above
```

---

### 7. Run the agent

```bash
cd job_notifier
python main.py
```

You'll get a Telegram message confirming the agent is live. After the first
scan completes, you'll receive one message per matched job — just a score,
company, location, and a direct link.

---

## What a Telegram alert looks like

```
✅ 84% match
Senior Backend Engineer — Razorpay
📍 Bangalore, India · LinkedIn
View Job
```

One tap on the link takes you straight to the job posting.

---

## Running in the background (optional)

### Option A: tmux (simplest)

```bash
tmux new -s jobs
python main.py
# Press Ctrl+B, then D to detach and leave it running
# Reattach later with: tmux attach -t jobs
```

### Option B: systemd service (Linux server)

Create `/etc/systemd/system/job-notifier.service`:

```ini
[Unit]
Description=Job Matching Agent
After=network.target

[Service]
WorkingDirectory=/path/to/job_notifier
ExecStart=/usr/bin/python3 /path/to/job_notifier/main.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl enable job-notifier
sudo systemctl start job-notifier
sudo journalctl -u job-notifier -f    # live logs
```

---

## How job matching works

1. Each scraped job (title, company, location, description snippet) is sent
   to Gemini along with your full resume text
2. Gemini scores the fit from 0–100 based on skills, seniority, and role type
3. Only jobs scoring ≥ `MATCH_THRESHOLD` (default 80%) trigger an alert
4. Job IDs are saved to `seen_jobs.json` — you will never be notified twice
   for the same listing

---

## Site access summary

| Site      | Method                | Auth required? |
|-----------|-----------------------|----------------|
| LinkedIn  | Guest Jobs API        | No             |
| Naukri    | Frontend JSON API     | No             |
| Indeed    | HTML scraping         | No             |

No credentials are stored. If a site blocks a request, that source is
skipped gracefully and the agent continues with the others.

---

## Tuning tips

- Raise `MATCH_THRESHOLD` to 85–90 to reduce noise
- Narrow `SEARCH_KEYWORDS` if too many irrelevant jobs are being evaluated
- Set `CHECK_INTERVAL_HOURS = 6` for less frequent but batched scans
- The more detail your resume has (projects, metrics, tech stack), the more
  accurate Gemini's scoring will be