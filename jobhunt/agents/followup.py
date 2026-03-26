"""Follow-up Writer agent — generates follow-up messages for stale applications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobhunt.llm.prompts import followup_system_prompt, followup_user_prompt
from jobhunt.llm.provider import get_model_for_agent, llm_call

if TYPE_CHECKING:
    from jobhunt.config import AppConfig


def write_followup(
    cfg: AppConfig,
    company: str,
    role_title: str,
    days_since: int,
    channel: str = "email",
) -> str:
    """Generate a follow-up message for a specific application."""
    system = followup_system_prompt(cfg.profile)
    user = followup_user_prompt(company, role_title, days_since, channel)
    model = get_model_for_agent(cfg, "followup")

    return llm_call(system, user, model, max_tokens=300)
