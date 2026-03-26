"""Multi-model LLM abstraction powered by LiteLLM."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from jobhunt.config import AppConfig

litellm.drop_params = True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def llm_call(
    system: str,
    user: str,
    model: str,
    max_tokens: int = 1000,
    temperature: float = 0.3,
) -> str:
    """Send a prompt to any LLM via LiteLLM and return the text response."""
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


def llm_call_json(
    system: str,
    user: str,
    model: str,
    max_tokens: int = 1000,
    temperature: float = 0.1,
) -> dict:
    """Call LLM and parse the response as JSON, stripping markdown fences."""
    text = llm_call(system, user, model, max_tokens, temperature)
    text = re.sub(r"```json\s*|```\s*", "", text).strip()
    return json.loads(text)


def get_model_for_agent(cfg: AppConfig, agent: str) -> str:
    """Resolve which model to use for a given agent name."""
    return cfg.get_model(agent)
