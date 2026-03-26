"""Configuration loader — reads config.yaml + profile/*.yaml into Pydantic models."""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv

from jobhunt.models import CandidateProfile, Preferences, SystemConfig

_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class AppConfig:
    """Single object that holds system config, candidate profile, and preferences."""

    def __init__(self, config_path: Path | None = None):
        load_dotenv(_ROOT / ".env")

        config_path = config_path or (_ROOT / "config.yaml")
        raw = _load_yaml(config_path)
        self.system = SystemConfig(**raw)

        profile_dir = (_ROOT / self.system.profile_dir).resolve()
        self._profile_dir = profile_dir

        self.profile = CandidateProfile(
            **_load_yaml(profile_dir / "profile.yaml")
        )
        self.preferences = Preferences(
            **_load_yaml(profile_dir / "preferences.yaml")
        )

        resume_md = profile_dir / "base_resume.md"
        self.base_resume_md: str = resume_md.read_text("utf-8") if resume_md.exists() else ""

    @property
    def profile_dir(self) -> Path:
        return self._profile_dir

    @property
    def generated_dir(self) -> Path:
        d = self._profile_dir / "generated"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_model(self, agent: str) -> str:
        """Return the LLM model string for a given agent, falling back to default."""
        override = getattr(self.system.llm.models, agent, None)
        return override or self.system.llm.default_model

    def validate_keys(self) -> list[str]:
        """Return list of warnings about missing config."""
        import os
        warnings: list[str] = []
        if self.system.sheets.spreadsheet_id == "YOUR_GOOGLE_SHEET_ID":
            warnings.append("Google Sheet ID not set in config.yaml")
        if not any(
            os.getenv(k)
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")
        ):
            warnings.append("No LLM API key found in .env (need at least one)")
        return warnings


def load_config(config_path: Path | None = None) -> AppConfig:
    return AppConfig(config_path)
