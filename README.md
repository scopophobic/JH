# JobHunt — Automated Job Search Pipeline

Automated pipeline that searches for jobs, scores them against your profile, generates tailored resume PDFs, writes outreach messages, and syncs everything to Google Sheets.

**Swap the `profile/` folder and the entire pipeline works for a different person — zero code changes.**

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your profile (or use the existing one)
python main.py init          # creates template profile/ folder
# Then edit: profile/profile.yaml, profile/preferences.yaml, profile/base_resume.md

# 3. Configure API keys
cp .env.example .env
# Edit .env with your keys (at least one LLM provider required)

# 4. Set up Google Sheets (see below)

# 5. Run
python main.py process       # full pipeline: search → score → tailor → outreach
```

## Commands

| Command | What it does |
|---------|-------------|
| `python main.py init` | Create a fresh `profile/` folder with template files |
| `python main.py validate` | Check that profile and config are properly filled in |
| `python main.py search` | Run job search across all enabled sources |
| `python main.py score` | Score unscored jobs in the RawJobs sheet |
| `python main.py process` | Full pipeline (search + score + tailor + outreach + PDF) |
| `python main.py followup` | Generate follow-ups for stale applications |
| `python main.py run` | Start scheduler (daily pipeline + weekly follow-ups) |
| `python main.py status` | Show pipeline statistics from Google Sheet |

## Project Structure

```
profile/                    ← YOUR DATA (the "control unit")
├── profile.yaml            ← Identity, experience, projects, skills
├── preferences.yaml        ← Search criteria, resume variants, outreach style
├── base_resume.md          ← Your resume in markdown
└── generated/              ← Tailored PDFs + notes output here

config.yaml                 ← System config (models, sources, thresholds)
.env                        ← API keys (gitignored)
main.py                     ← CLI entry point

jobhunt/
├── config.py               ← Config loader (profile + system)
├── models.py               ← Pydantic data models
├── llm/
│   ├── provider.py         ← Multi-model LLM abstraction (LiteLLM)
│   └── prompts.py          ← Jinja2 prompt templates
├── agents/
│   ├── scorer.py           ← JD scoring agent
│   ├── tailor.py           ← Resume tailoring agent
│   ├── outreach.py         ← Cold email / LinkedIn / Wellfound writer
│   └── followup.py         ← Follow-up message writer
├── scrapers/               ← 9 job source scrapers
├── sheets/client.py        ← Google Sheets CRUD
├── resume/
│   ├── generator.py        ← Tailored PDF generation
│   └── templates/          ← HTML resume templates
├── pipeline.py             ← Full orchestration
└── scheduler.py            ← APScheduler cron jobs
```

## LLM Model Configuration

Use any model from Anthropic, OpenAI, or Google. Set per-agent in `config.yaml`:

```yaml
llm:
  default_model: "claude-sonnet-4-20250514"
  models:
    scorer: "gemini/gemini-2.0-flash"        # cheap + fast for scoring
    tailor: "claude-sonnet-4-20250514"        # strong at writing
    outreach: "gpt-4o"                        # or any model you prefer
    followup: null                            # uses default_model
```

Model strings follow [LiteLLM conventions](https://docs.litellm.ai/docs/providers):
- Anthropic: `claude-sonnet-4-20250514`, `claude-haiku-4-20250514`
- OpenAI: `gpt-4o`, `gpt-4o-mini`
- Google: `gemini/gemini-2.0-flash`, `gemini/gemini-1.5-pro`

## Job Sources

| Source | Method | API Key Required |
|--------|--------|-----------------|
| RemoteOK | Free JSON API | No |
| Wellfound | RSS feeds | No |
| YC Jobs | Web scraping | No |
| Custom RSS | RSS feeds | No |
| Google Jobs | SerpAPI | `SERPAPI_KEY` |
| LinkedIn | SerpAPI | `SERPAPI_KEY` |
| Indeed | SerpAPI | `SERPAPI_KEY` |
| Glassdoor | SerpAPI | `SERPAPI_KEY` |
| Naukri | Web scraping | No |

Enable/disable in `config.yaml` under `sources`.

SerpAPI free tier: 100 searches/month at [serpapi.com](https://serpapi.com).

## Google Sheets Setup

1. Create a Google Cloud project and enable the Google Sheets API
2. Create a service account and download the JSON key
3. Place it at `credentials/google_service_account.json`
4. Create a Google Sheet with two tabs:

**Tab 1: `RawJobs`** — columns:
`title | company | jd_url | jd_text | source | date_found | status`

**Tab 2: `StagingReview`** — columns:
`company | title | jd_url | score | variant | summary | missing_keywords | red_flags | tailored_resume_notes | outreach_draft | resume_pdf_path | date_generated | status | your_notes | date_sent`

5. Share the sheet with the service account email
6. Put the sheet ID in `config.yaml` → `sheets.spreadsheet_id`

## Daily Workflow (10 minutes)

1. Run `python main.py process` (or let the scheduler handle it)
2. Open StagingReview sheet, filter `status = awaiting_review`
3. Review score + summary + red flags for each row
4. Download the tailored resume PDF from `profile/generated/`
5. Edit outreach if needed, mark status as `approved`, then `sent`

## Cost Estimate

- LLM: ~$0.002 per application (score + tailor + outreach) → 50 apps/month < $0.15
- SerpAPI: free tier covers 100 searches/month
- Google Sheets API: free
- Total: effectively free for individual use
