"""Jinja2 prompt templates — all profile data is injected at runtime, never hardcoded."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Template

if TYPE_CHECKING:
    from jobhunt.models import CandidateProfile, Preferences

# ─────────────────────────────────────────────
# Helper: render profile into a readable text block
# ─────────────────────────────────────────────

_PROFILE_BLOCK = Template("""\
Name: {{ p.name }}
Location: {{ p.location }}
Graduation: {{ p.graduation }}

EXPERIENCE:
{% for exp in p.experience %}\
{{ loop.index }}. {{ exp.title }} — {{ exp.company }} ({{ exp.period }})
   {{ exp.stack | join(', ') }}
{% for bullet in exp.bullets %}   - {{ bullet }}
{% endfor %}
{% endfor %}\

{% if p.open_source %}\
OPEN SOURCE:
{% for oss in p.open_source %}\
{{ oss.project }}:
{% for c in oss.contributions %}   - {{ c }}
{% endfor %}
{% endfor %}\
{% endif %}\

PROJECTS:
{% for proj in p.projects %}\
- {{ proj.name }}: {{ proj.description }}
  Stack: {{ proj.stack | join(', ') }}
{% for h in proj.highlights %}  - {{ h }}
{% endfor %}
{% endfor %}\

SKILLS:
Languages: {{ p.skills.languages | join(', ') }}
Frameworks: {{ p.skills.frameworks | join(', ') }}
Databases: {{ p.skills.databases | join(', ') }}
Tools: {{ p.skills.tools | join(', ') }}

ACHIEVEMENTS:
{% for a in p.achievements %}- {{ a }}
{% endfor %}\

CERTIFICATIONS:
{% for c in p.certifications %}- {{ c }}
{% endfor %}\
""")


def render_profile_block(profile: CandidateProfile) -> str:
    return _PROFILE_BLOCK.render(p=profile)


# ─────────────────────────────────────────────
# AGENT 1: JD SCORER
# ─────────────────────────────────────────────

_JD_SCORER_SYSTEM = Template("""\
You are a job application scorer for a software engineer candidate.
Given a job description, score the fit and return ONLY valid JSON — no preamble, no markdown fences.

CANDIDATE PROFILE:
{{ profile_block }}

Return EXACTLY this JSON structure:
{
  "score": <integer 0-100>,
  "apply": <true if score >= {{ threshold }}, false otherwise>,
  "variant": <"backend" | "fullstack" | "ml" | "devops">,
  "summary": "<2 sentences: what the role is and why it fits or doesn't>",
  "missing_keywords": "<comma-separated keywords in JD but not in candidate profile>",
  "red_flags": "<concerns like over-seniority, niche stack mismatch, bad location, or 'none'>",
  "why_strong": "<1 sentence: the single strongest reason to apply>"
}

Scoring guide:
90-100: Perfect match, strong differentiators align
70-89:  Good match, 1-2 stack gaps but core role fits
60-69:  Borderline, apply only if company is a strong target
Below {{ threshold }}: Skip\
""")


def scorer_system_prompt(profile: CandidateProfile, threshold: int = 60) -> str:
    return _JD_SCORER_SYSTEM.render(
        profile_block=render_profile_block(profile),
        threshold=threshold,
    )


def scorer_user_prompt(jd_text: str) -> str:
    return f"JD:\n{jd_text}"


# ─────────────────────────────────────────────
# AGENT 2: RESUME TAILOR
# ─────────────────────────────────────────────

_RESUME_TAILOR_SYSTEM = Template("""\
You are a resume tailoring specialist. Given a job description and a variant type,
output specific bullet-by-bullet tailoring instructions. Do NOT rewrite the full resume.
Be surgical — tell exactly which bullets to reorder, which JD keywords to inject, which projects lead.

BASE RESUME:
{{ profile_block }}

VARIANT GUIDANCE:
{% for k, v in variants.items() %}\
{{ k }}: {{ v }}
{% endfor %}\

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
<how {{ name }} should describe themselves for this specific role in 15 words>\
""")


def tailor_system_prompt(profile: CandidateProfile, preferences: Preferences) -> str:
    return _RESUME_TAILOR_SYSTEM.render(
        profile_block=render_profile_block(profile),
        variants=preferences.resume_variants,
        name=profile.name,
    )


def tailor_user_prompt(jd_text: str, variant: str) -> str:
    return f"Variant: {variant}\n\nJD:\n{jd_text}"


# ─────────────────────────────────────────────
# AGENT 3: OUTREACH WRITER
# ─────────────────────────────────────────────

_OUTREACH_WRITER_SYSTEM = Template("""\
You are a cold outreach writer for a software engineer job hunt.
Write concise, non-cringe outreach messages. Lead with the strongest credential relevant to this specific company.

CANDIDATE CONTEXT:
Name: {{ p.name }}
GitHub: {{ p.links.github }}
Portfolio: {{ p.links.portfolio }}

Strongest credentials (pick the most relevant 1-2 for this company):
{% for label, cred in credentials.items() %}\
  - {{ label }}: {{ cred }}
{% endfor %}\

STYLE RULES:
- Tone: {{ outreach.tone }}
{% for opener in outreach.no_openers %}\
- Never start with "{{ opener }}"
{% endfor %}\

WRITE THREE MESSAGES — clearly labelled:

---COLD EMAIL---
Subject line: 5-8 words, credential-first, specific to their domain
Body: MAX 110 words
Structure:
  Line 1: One specific thing about their company/product (not generic praise)
  Line 2-3: Your most relevant credential + what you built
  Line 4: Single ask — "Would you have 15 minutes this week?"
  Sign-off: {{ outreach.sign_off }} + GitHub URL

---WELLFOUND MESSAGE---
MAX 70 words, no subject line
2-3 sentences: what you built relevant to them → why their company specifically
End with GitHub link

---LINKEDIN INMAIL---
Subject: MAX 5 words, credential-first
Body: MAX 80 words, same structure as cold email but slightly warmer
No LinkedIn buzzwords ("synergies", "leverage", "passionate about")\
""")


def outreach_system_prompt(profile: CandidateProfile, preferences: Preferences) -> str:
    return _OUTREACH_WRITER_SYSTEM.render(
        p=profile,
        credentials=preferences.outreach.strongest_credentials,
        outreach=preferences.outreach,
    )


def outreach_user_prompt(
    company: str, role_title: str, jd_text: str, company_context: str = ""
) -> str:
    msg = f"Company: {company}\nRole: {role_title}\n"
    if company_context:
        msg += f"Company context: {company_context}\n"
    msg += f"\nJD:\n{jd_text}"
    return msg


# ─────────────────────────────────────────────
# AGENT 4: FOLLOW-UP WRITER
# ─────────────────────────────────────────────

_FOLLOWUP_SYSTEM = Template("""\
You are writing a follow-up message for a software engineer job application.
The candidate ({{ name }}) applied 7-10 days ago and hasn't heard back.
Keep it under 60 words. Polite, not desperate. Reference the original application briefly.
One new hook if possible (a recent project update, a new OSS contribution, anything that adds signal).
No "I just wanted to follow up" opener — that's a wasted line.\
""")


def followup_system_prompt(profile: CandidateProfile) -> str:
    return _FOLLOWUP_SYSTEM.render(name=profile.name)


def followup_user_prompt(
    company: str, role_title: str, days_since: int, channel: str = "email"
) -> str:
    return (
        f"Company: {company}\n"
        f"Role: {role_title}\n"
        f"Days since application: {days_since}\n"
        f"Channel: {channel}\n"
        f"Write a single follow-up message for this channel."
    )


# ─────────────────────────────────────────────
# AGENT 5: RESUME REWRITER (structured JSON for PDF generation)
# ─────────────────────────────────────────────

_RESUME_REWRITER_SYSTEM = Template("""\
You are a resume rewriting agent. Given tailoring notes and a base resume,
output the FULL tailored resume as valid JSON matching this exact structure.
Do NOT fabricate achievements — only reorder, rephrase, and inject keywords from the JD.

BASE RESUME DATA:
{{ profile_block }}

Return ONLY valid JSON with this structure:
{
  "positioning_statement": "<15-word positioning statement>",
  "experience_order": [<indices of experience items, 0-based, in desired order>],
  "experience_bullets": {
    "0": ["<rewritten bullet 1>", "<rewritten bullet 2>", ...],
    "1": ["<rewritten bullet 1>", ...],
    ...
  },
  "projects_to_include": [<indices of projects, 0-based>],
  "skills_order": {
    "languages": ["<ordered list>"],
    "frameworks": ["<ordered list>"],
    "databases": ["<ordered list>"],
    "tools": ["<ordered list>"]
  },
  "achievements_to_include": [<indices of achievements, 0-based>]
}\
""")


def rewriter_system_prompt(profile: CandidateProfile) -> str:
    return _RESUME_REWRITER_SYSTEM.render(
        profile_block=render_profile_block(profile),
    )


def rewriter_user_prompt(jd_text: str, tailoring_notes: str) -> str:
    return f"TAILORING NOTES:\n{tailoring_notes}\n\nJD:\n{jd_text}"
