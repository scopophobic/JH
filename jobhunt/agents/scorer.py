"""JD Scorer agent — scores job descriptions against the candidate profile."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobhunt.llm.prompts import scorer_system_prompt, scorer_user_prompt
from jobhunt.llm.provider import get_model_for_agent, llm_call_json
from jobhunt.models import ScoreResult

if TYPE_CHECKING:
    from jobhunt.config import AppConfig


def score_jd(cfg: AppConfig, jd_text: str) -> ScoreResult:
    """Score a job description against the loaded candidate profile."""
    system = scorer_system_prompt(
        cfg.profile,
        threshold=cfg.system.pipeline.score_threshold,
    )
    user = scorer_user_prompt(jd_text)
    model = get_model_for_agent(cfg, "scorer")

    try:
        data = llm_call_json(system, user, model, max_tokens=600)
        return ScoreResult(**data)
    except Exception:
        return ScoreResult(
            score=0,
            apply=False,
            variant="backend",
            summary="Error scoring this JD",
            red_flags="parse_error",
        )
