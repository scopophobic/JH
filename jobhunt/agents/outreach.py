"""Outreach Writer agent — generates cold email, LinkedIn InMail, and Wellfound messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobhunt.llm.prompts import outreach_system_prompt, outreach_user_prompt
from jobhunt.llm.provider import get_model_for_agent, llm_call

if TYPE_CHECKING:
    from jobhunt.config import AppConfig


def write_outreach(
    cfg: AppConfig,
    company: str,
    role_title: str,
    jd_text: str,
    company_context: str = "",
) -> str:
    """Return all three outreach messages (cold email, Wellfound, LinkedIn) as a formatted string."""
    system = outreach_system_prompt(cfg.profile, cfg.preferences)
    user = outreach_user_prompt(company, role_title, jd_text, company_context)
    model = get_model_for_agent(cfg, "outreach")

    return llm_call(system, user, model, max_tokens=900)
