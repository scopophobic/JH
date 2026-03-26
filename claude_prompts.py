"""
Job Hunt Agent — Claude API Prompts
Adithyan Madhu | 2025

Usage:
  pip install anthropic
  export ANTHROPIC_API_KEY=your_key_here
  python claude_prompts.py

Each function takes the relevant input and returns Claude's response text.
Drop these into n8n HTTP Request nodes or run standalone.
"""

import anthropic
import json
import re

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ─────────────────────────────────────────────
# CANDIDATE PROFILE (update this as you grow)
# ─────────────────────────────────────────────
CANDIDATE_PROFILE = """
Name: Adithyan Madhu
Graduation: August 2025, B.Tech Computer Science, KCC Institute of Technology

EXPERIENCE:
1. SDE Intern — Paramount Products (Jan 2026–Present)
   Flask, Django, React, MySQL | Built internal platform managing 10,000+ garment designs
   RESTful APIs for design upload workflow | Reduced manual processing time by 25%

2. SDE Intern — Newgen Software Technologies (Apr–Oct 2024)
   Core Java, Servlets, Python, SQL, QdrantDB
   Built RAG-based HR policy assistant (200+ docs indexed, used org-wide)
   Resolved 50+ UI/backend bugs | 20% form load speed improvement

3. Campus Ambassador — GeeksforGeeks (Jun 2022–Jun 2023)
   Organized events for 300+ students | Mentored 50+ peers in DSA

OPEN SOURCE — Intel Auto-Round:
   PR #1348: Refactored FP8 dequantization using registry pattern (merged)
   PR #1365: Migrated to PyTorch get_submodule/set_submodule APIs (merged)
   Collaborated directly with Intel engineers on ML inference quality

PROJECTS:
- Vinci UI: Node-based AI image generation platform
  React, Tailwind, Express.js, AWS EC2+RDS+Nginx, Stable Diffusion, Gemini API, Google OAuth
  Deployed and tested on AWS Cloud

- ReadingRoom: Social reading platform with AI features
  Next.js frontend, Django+PostgreSQL backend
  RAG system with ChromaDB+Gemini, ~30% API perf improvement, ~35% relevance boost
  Web-scraped metadata, semantic book recommendation

SKILLS:
Languages: C++, Python, Go, TypeScript, Java
Frameworks: Django, FastAPI, React, Next.js
Databases: PostgreSQL, MySQL, SQLite, ChromaDB, AWS RDS
Tools: Git, GitHub Actions, Docker, AWS EC2/RDS/S3

ACHIEVEMENTS:
- LeetCode 1800+ rating, top 8% worldwide, 500+ problems solved
- GATE 2025 qualified (Computer Science)
- ISRO Ideate for Space Innovation — Finalist at IIT Delhi
- Adobe Creative Challenge 2020 — National Winner (1st Rank)
- Certificates: ML Specialization (Andrew Ng), Git & GitHub (Google), Python (Coursera)
"""

# Resume variants — what changes per role type
RESUME_VARIANTS = {
    "backend": "Emphasise: Newgen RAG backend, Paramount APIs, Intel OSS, Go/Python/Java skills. De-emphasise: frontend work, design achievements.",
    "fullstack": "Emphasise: Vinci UI (full AWS deployment), ReadingRoom (Next.js+Django), React experience. Balance frontend and backend equally.",
    "ml": "Emphasise: Intel Auto-Round PRs (FP8, PyTorch), RAG system at Newgen, ChromaDB/vector work, ML Specialization cert. Lead with OSS contributions.",
    "devops": "Emphasise: AWS EC2/RDS/S3, Nginx, Docker, GitHub Actions, system deployment experience from Vinci UI. LeetCode less relevant here."
}


# ─────────────────────────────────────────────
# AGENT 1: JD SCORER
# ─────────────────────────────────────────────

JD_SCORER_SYSTEM = f"""You are a job application scorer for a software engineer candidate.
Given a job description, score the fit and return ONLY valid JSON — no preamble, no markdown fences.

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

Return EXACTLY this JSON structure:
{{
  "score": <integer 0-100>,
  "apply": <true if score >= 60, false otherwise>,
  "variant": <"backend" | "fullstack" | "ml" | "devops">,
  "summary": "<2 sentences: what the role is and why it fits or doesn't>",
  "missing_keywords": "<comma-separated keywords in JD but not in candidate profile>",
  "red_flags": "<concerns like over-seniority, niche stack mismatch, bad location, or 'none'>",
  "why_strong": "<1 sentence: the single strongest reason to apply>"
}}

Scoring guide:
90-100: Perfect match, strong differentiators align (OSS, RAG, AWS)
70-89:  Good match, 1-2 stack gaps but core role fits
60-69:  Borderline, apply only if company is a strong target
Below 60: Skip"""


def score_jd(jd_text: str) -> dict:
    """Score a job description against Adithyan's profile. Returns parsed JSON dict."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=JD_SCORER_SYSTEM,
        messages=[{"role": "user", "content": f"JD:\n{jd_text}"}]
    )
    text = response.content[0].text.strip()
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


# ─────────────────────────────────────────────
# AGENT 2: RESUME TAILOR
# ─────────────────────────────────────────────

RESUME_TAILOR_SYSTEM = f"""You are a resume tailoring specialist. Given a job description and a variant type,
output specific bullet-by-bullet tailoring instructions. Do NOT rewrite the full resume.
Be surgical — tell exactly which bullets to reorder, which JD keywords to inject, which projects lead.

BASE RESUME:
{CANDIDATE_PROFILE}

VARIANT GUIDANCE:
{json.dumps(RESUME_VARIANTS, indent=2)}

Output format (use these exact headers):
## LEAD WITH
<which experience/project to place first>

## REORDER BULLETS
<list specific bullets to move up, by abbreviated content>

## INJECT THESE KEYWORDS
<exact phrases from the JD to weave into existing bullets — do not fabricate new achievements>

## PROJECTS TO HIGHLIGHT (pick 1-2)
<which projects and why>

## SKILLS SECTION — FRONT LOAD
<which skills to list first>

## DE-EMPHASISE
<anything that weakens this specific application>

## ONE-LINE POSITIONING STATEMENT
<how Adithyan should describe himself for this specific role in 15 words>"""


def tailor_resume(jd_text: str, variant: str) -> str:
    """Returns resume tailoring instructions as markdown string."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=RESUME_TAILOR_SYSTEM,
        messages=[{"role": "user", "content": f"Variant: {variant}\n\nJD:\n{jd_text}"}]
    )
    return response.content[0].text


# ─────────────────────────────────────────────
# AGENT 3: OUTREACH WRITER
# ─────────────────────────────────────────────

OUTREACH_WRITER_SYSTEM = """You are a cold outreach writer for a software engineer job hunt.
Write concise, non-cringe outreach messages. No "I've always been passionate about..." openers.
No generic subject lines. Lead with the strongest credential relevant to this specific company.

CANDIDATE CONTEXT:
Name: Adithyan Madhu
Strongest credentials (pick the most relevant 1-2 for this company):
  - Merged PRs at Intel Auto-Round (ML inference library, PyTorch/FP8) — use for ML/AI companies
  - Built production RAG system at Newgen Software (200+ docs, org-wide deployment) — use for SaaS/enterprise
  - AWS-deployed AI image generation platform (Vinci UI) — use for infra/cloud/product companies
  - Full Django+PostgreSQL backend with 30% perf gains (ReadingRoom) — use for backend/data companies
GitHub: https://github.com/adithyanmadhu (update with real URL)
Portfolio: https://adithyanmadhu.dev (update with real URL)

WRITE THREE MESSAGES — clearly labelled:

---COLD EMAIL---
Subject line: 5-8 words, credential-first, specific to their domain
Body: MAX 110 words
Structure:
  Line 1: One specific thing about their company/product (not generic praise)
  Line 2-3: Your most relevant credential + what you built
  Line 4: Single ask — "Would you have 15 minutes this week?"
  Sign-off: Name + GitHub URL

---WELLFOUND MESSAGE---
MAX 70 words, no subject line
2-3 sentences: what you built relevant to them → why their company specifically
End with GitHub link

---LINKEDIN INMAIL---
Subject: MAX 5 words, credential-first
Body: MAX 80 words, same structure as cold email but slightly warmer
No LinkedIn buzzwords ("synergies", "leverage", "passionate about")"""


def write_outreach(company: str, role_title: str, jd_text: str,
                   company_context: str = "") -> str:
    """Returns all three outreach messages as a formatted string."""
    user_msg = f"Company: {company}\nRole: {role_title}\n"
    if company_context:
        user_msg += f"Company context: {company_context}\n"
    user_msg += f"\nJD:\n{jd_text}"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=OUTREACH_WRITER_SYSTEM,
        messages=[{"role": "user", "content": user_msg}]
    )
    return response.content[0].text


# ─────────────────────────────────────────────
# AGENT 4: FOLLOW-UP WRITER
# ─────────────────────────────────────────────

FOLLOWUP_SYSTEM = """You are writing a follow-up message for a software engineer job application.
The candidate applied 7-10 days ago and hasn't heard back.
Keep it under 60 words. Polite, not desperate. Reference the original application briefly.
One new hook if possible (a recent project update, a new OSS contribution, anything that adds signal).
No "I just wanted to follow up" opener — that's a wasted line."""


def write_followup(company: str, role_title: str, days_since: int,
                   channel: str = "email") -> str:
    """Write a follow-up message. channel = 'email' | 'linkedin' | 'wellfound'"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=FOLLOWUP_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Company: {company}\nRole: {role_title}\nDays since application: {days_since}\nChannel: {channel}\nCandidate: Adithyan Madhu, backend/ML engineer"
        }]
    )
    return response.content[0].text


# ─────────────────────────────────────────────
# PIPELINE: run all agents for one JD
# ─────────────────────────────────────────────

def run_pipeline(company: str, role_title: str, jd_text: str,
                 company_context: str = "") -> dict:
    """
    Full pipeline for one job posting.
    Returns dict with score, tailoring notes, and outreach drafts.
    """
    print(f"\n{'='*60}")
    print(f"Processing: {role_title} @ {company}")
    print('='*60)

    # Step 1: Score
    print("\n[1/3] Scoring JD...")
    score_data = score_jd(jd_text)
    print(f"  Score: {score_data['score']}/100 | Apply: {score_data['apply']} | Variant: {score_data['variant']}")
    print(f"  Summary: {score_data['summary']}")
    if score_data.get('red_flags') != 'none':
        print(f"  Red flags: {score_data['red_flags']}")

    if not score_data['apply']:
        print("  -> Skipping (score < 60)")
        return {"company": company, "role": role_title, "score_data": score_data, "skipped": True}

    # Step 2: Tailor resume
    print(f"\n[2/3] Tailoring resume for variant: {score_data['variant']}...")
    resume_notes = tailor_resume(jd_text, score_data['variant'])

    # Step 3: Write outreach
    print("\n[3/3] Writing outreach messages...")
    outreach = write_outreach(company, role_title, jd_text, company_context)

    result = {
        "company": company,
        "role": role_title,
        "score_data": score_data,
        "resume_tailoring_notes": resume_notes,
        "outreach_messages": outreach,
        "skipped": False
    }

    print("\n--- OUTREACH PREVIEW ---")
    print(outreach[:400] + "..." if len(outreach) > 400 else outreach)

    return result


# ─────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sample_jd = """
    Backend Engineer — Razorpay
    We're looking for a backend engineer to join our payments infrastructure team.
    You'll work on high-throughput distributed systems processing millions of transactions.

    Requirements:
    - 1-3 years experience in backend development
    - Strong in Python or Go
    - Experience with distributed systems, queues (Kafka/RabbitMQ)
    - PostgreSQL or similar RDBMS
    - REST API design
    - Docker and Kubernetes basics
    - Bonus: Experience with financial systems or payment flows
    """

    result = run_pipeline(
        company="Razorpay",
        role_title="Backend Engineer",
        jd_text=sample_jd,
        company_context="India's leading payments company, recently expanded into banking and neo-banking products."
    )

    if not result["skipped"]:
        print("\n--- RESUME TAILORING NOTES ---")
        print(result["resume_tailoring_notes"])
        print("\n--- FULL OUTREACH MESSAGES ---")
        print(result["outreach_messages"])
