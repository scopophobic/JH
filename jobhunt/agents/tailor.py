"""Resume Tailor agent — generates bullet-by-bullet tailoring instructions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobhunt.llm.prompts import tailor_system_prompt, tailor_user_prompt
from jobhunt.llm.provider import get_model_for_agent, llm_call

if TYPE_CHECKING:
    from jobhunt.config import AppConfig


def tailor_resume(cfg: AppConfig, jd_text: str, variant: str) -> str:
    """Return markdown tailoring instructions for a specific JD and variant."""
    system = tailor_system_prompt(cfg.profile, cfg.preferences)
    user = tailor_user_prompt(jd_text, variant)
    model = get_model_for_agent(cfg, "tailor")

    return llm_call(system, user, model, max_tokens=1200)
