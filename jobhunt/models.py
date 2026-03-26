"""Data models for the entire pipeline."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Profile Models (loaded from profile/*.yaml) ──


class Links(BaseModel):
    github: str = ""
    portfolio: str = ""
    linkedin: str = ""
    leetcode: str = ""


class Experience(BaseModel):
    title: str
    company: str
    period: str
    stack: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class OpenSourceContribution(BaseModel):
    project: str
    contributions: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    stack: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class Skills(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    graduation: str = ""
    links: Links = Field(default_factory=Links)
    experience: list[Experience] = Field(default_factory=list)
    open_source: list[OpenSourceContribution] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    achievements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


# ── Preferences Models (loaded from profile/preferences.yaml) ──


class SearchCriteria(BaseModel):
    roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    experience_years: list[int] = Field(default_factory=lambda: [0, 2])
    keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)


class OutreachPreferences(BaseModel):
    tone: str = "direct, credential-first, no fluff"
    sign_off: str = ""
    no_openers: list[str] = Field(default_factory=list)
    strongest_credentials: dict[str, str] = Field(default_factory=dict)


class Preferences(BaseModel):
    search: SearchCriteria = Field(default_factory=SearchCriteria)
    resume_variants: dict[str, str] = Field(default_factory=dict)
    outreach: OutreachPreferences = Field(default_factory=OutreachPreferences)


# ── System Config Models (loaded from config.yaml) ──


class LLMModels(BaseModel):
    scorer: Optional[str] = None
    tailor: Optional[str] = None
    outreach: Optional[str] = None
    followup: Optional[str] = None


class LLMConfig(BaseModel):
    default_model: str = "claude-sonnet-4-20250514"
    models: LLMModels = Field(default_factory=LLMModels)


class SourcesConfig(BaseModel):
    google_jobs: bool = True
    linkedin: bool = True
    wellfound: bool = True
    ycombinator: bool = True
    indeed: bool = True
    naukri: bool = True
    glassdoor: bool = True
    remoteok: bool = True
    rss_feeds: list[str] = Field(default_factory=list)


class PipelineConfig(BaseModel):
    score_threshold: int = 60
    max_jobs_per_run: int = 50
    dedup_window_days: int = 30


class ScheduleConfig(BaseModel):
    search_cron: str = "0 9 * * *"
    followup_cron: str = "0 10 * * 1"
    followup_after_days: int = 7


class SheetsConfig(BaseModel):
    spreadsheet_id: str = "YOUR_GOOGLE_SHEET_ID"
    raw_jobs_tab: str = "RawJobs"
    staging_tab: str = "StagingReview"


class ResumeConfig(BaseModel):
    template: str = "modern"


class SystemConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    profile_dir: str = "./profile"
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    sheets: SheetsConfig = Field(default_factory=SheetsConfig)
    resume: ResumeConfig = Field(default_factory=ResumeConfig)


# ── Pipeline Data Models ──


class JobStatus(str, Enum):
    NEW = "new"
    SCORED_SKIP = "scored_skip"
    SCORED_APPLY = "scored_apply"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"
    REJECTED = "rejected"


class RawJob(BaseModel):
    title: str
    company: str
    jd_url: str = ""
    jd_text: str = ""
    source: str = ""
    date_found: date = Field(default_factory=date.today)
    status: str = "new"


class ScoreResult(BaseModel):
    score: int = 0
    apply: bool = False
    variant: str = "backend"
    summary: str = ""
    missing_keywords: str = ""
    red_flags: str = "none"
    why_strong: str = ""


class StagingRow(BaseModel):
    company: str
    title: str
    jd_url: str = ""
    score: int = 0
    variant: str = ""
    summary: str = ""
    missing_keywords: str = ""
    red_flags: str = ""
    tailored_resume_notes: str = ""
    outreach_draft: str = ""
    resume_pdf_path: str = ""
    date_generated: date = Field(default_factory=date.today)
    status: str = "awaiting_review"
    your_notes: str = ""
    date_sent: str = ""
