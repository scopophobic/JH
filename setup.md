# Job Hunt Agent Pipeline — Setup Guide

## What you have
- `n8n_job_hunt_workflow.json` — import into n8n, runs the full pipeline on a schedule
- `claude_prompts.py` — standalone Python module, use directly or as reference for the n8n prompts

---

## Step 1: Set up Google Sheets

Create one spreadsheet with two tabs:

### Tab 1: `RawJobs`
Columns (in order):
`title | company | jd_url | jd_text | source | date_found | status`

Status values: `new` → `scored_skip` or moves to StagingReview

### Tab 2: `StagingReview`
Columns:
`company | title | jd_url | score | variant | summary | missing_keywords | red_flags | tailored_resume_notes | outreach_draft | date_generated | status | your_notes | date_sent`

Status values: `awaiting_review` → `approved` → `sent` → `replied` / `rejected`

---

## Step 2: Get your Anthropic API key

1. Go to console.anthropic.com
2. Create an API key
3. Cost estimate: ~$0.002 per full application processed (score + tailor + outreach)
   - 50 applications/month ≈ ₹8–10

---

## Step 3: Set up n8n (free)

### Option A — n8n Cloud (recommended, zero setup)
1. Sign up at n8n.io (free tier: 5 active workflows, 20 executions/day)
2. Import `n8n_job_hunt_workflow.json` via the workflow menu → Import
3. Set credentials:
   - Google Sheets: connect your Google account via OAuth
   - Anthropic: add as HTTP Header Auth → header name `x-api-key` → your key
4. Update `YOUR_GOOGLE_SHEET_ID` in all Google Sheets nodes
5. Activate the workflow

### Option B — Self-hosted (unlimited, needs Docker)
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```
Then import the workflow at localhost:5678

---

## Step 4: Feed jobs into RawJobs

**Manual (easiest to start):**
Paste job titles, company names, JD text into the RawJobs sheet each morning.
Set status = `new`. The n8n trigger runs at 9am and picks them up.

**Semi-automated options (free):**
- Use n8n's RSS nodes to pull from job board RSS feeds
- Wellfound has RSS: `https://wellfound.com/jobs.rss?role[]=Backend+Engineer`
- YC Jobs: scrape `https://www.ycombinator.com/jobs` with n8n HTTP node
- LinkedIn: no official RSS, but you can use the daily email digest → forward to a webhook

---

## Step 5: Run the Python script standalone (optional)

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python claude_prompts.py
```

Edit the `sample_jd` at the bottom to test with a real JD.

---

## Step 6: Your daily review (10 minutes)

1. Open StagingReview sheet
2. Filter `status = awaiting_review`
3. For each row:
   - Read the score + summary + red flags
   - If applying: read tailored_resume_notes, update your resume PDF accordingly
   - Edit outreach_draft if needed (always personalise at least 1 line)
   - Change status to `approved`
4. Send applications, update `date_sent` and `status = sent`

---

## Customising the prompts

All prompts live in `claude_prompts.py` as constants at the top of each section.
Key things to update over time:

- `CANDIDATE_PROFILE`: add new projects, skills, achievements as you build them
- `JD_SCORER_SYSTEM`: adjust the score threshold (currently 60) if you're getting too many or too few matches
- `OUTREACH_WRITER_SYSTEM`: update the GitHub and Portfolio URLs before using
- `RESUME_VARIANTS`: refine as you learn which variant gets responses

---

## Tracking what works

Add these columns to StagingReview over time:
- `response_received` (yes/no)
- `response_type` (interview / rejection / no reply)
- `days_to_response`

After 30 applications, you'll have enough data to see which variant and outreach style converts.
Double down on what works, kill what doesn't.

---

## The one thing most people skip

The follow-up. After 7-10 days with no reply, send one follow-up using `write_followup()`.
Response rate roughly doubles with a single polite follow-up. Most candidates never send one.