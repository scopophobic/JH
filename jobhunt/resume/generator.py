"""Resume PDF generator — renders tailored resume HTML via Jinja2, converts to PDF with WeasyPrint."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from jobhunt.llm.prompts import rewriter_system_prompt, rewriter_user_prompt
from jobhunt.llm.provider import get_model_for_agent, llm_call_json

if TYPE_CHECKING:
    from jobhunt.config import AppConfig

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _safe_index(lst: list, indices: list[int]) -> list:
    """Reorder a list by indices, skipping out-of-range."""
    return [lst[i] for i in indices if 0 <= i < len(lst)]


def generate_tailored_resume(
    cfg: AppConfig,
    jd_text: str,
    tailoring_notes: str,
    company: str,
    role: str,
) -> tuple[str, str]:
    """
    Generate a tailored resume PDF.

    Returns (pdf_path, notes_path) as strings.
    """
    profile = cfg.profile

    # Ask LLM to produce structured rewrite instructions
    system = rewriter_system_prompt(profile)
    user = rewriter_user_prompt(jd_text, tailoring_notes)
    model = get_model_for_agent(cfg, "tailor")

    try:
        rewrite = llm_call_json(system, user, model, max_tokens=1500)
    except Exception:
        rewrite = {}

    # Build template context from profile + rewrite instructions
    experience_order = rewrite.get("experience_order", list(range(len(profile.experience))))
    experience = _safe_index(profile.experience, experience_order)

    experience_bullets = rewrite.get("experience_bullets", {})
    experience_data = []
    for i, exp in enumerate(experience):
        original_idx = experience_order[i] if i < len(experience_order) else i
        custom_bullets = experience_bullets.get(str(original_idx))
        experience_data.append({
            "title": exp.title,
            "company": exp.company,
            "period": exp.period,
            "stack": exp.stack,
            "bullets": custom_bullets if custom_bullets else exp.bullets,
        })

    project_indices = rewrite.get("projects_to_include", list(range(len(profile.projects))))
    projects = _safe_index(profile.projects, project_indices)
    projects_data = [
        {
            "name": p.name,
            "description": p.description,
            "stack": p.stack,
            "highlights": p.highlights,
        }
        for p in projects
    ]

    skills_data = rewrite.get("skills_order", {
        "languages": profile.skills.languages,
        "frameworks": profile.skills.frameworks,
        "databases": profile.skills.databases,
        "tools": profile.skills.tools,
    })

    achievement_indices = rewrite.get(
        "achievements_to_include", list(range(len(profile.achievements)))
    )
    achievements = _safe_index(profile.achievements, achievement_indices)

    open_source_data = [
        {"project": oss.project, "contributions": oss.contributions}
        for oss in profile.open_source
    ]

    context = {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "links": {
            "github": profile.links.github,
            "portfolio": profile.links.portfolio,
            "linkedin": profile.links.linkedin,
        },
        "positioning_statement": rewrite.get("positioning_statement", ""),
        "experience": experience_data,
        "open_source": open_source_data,
        "projects": projects_data,
        "skills": skills_data,
        "education": profile.graduation,
        "achievements": achievements,
    }

    # Render HTML
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template_name = f"{cfg.system.resume.template}.html"
    template = env.get_template(template_name)
    html = template.render(**context)

    # Generate PDF
    slug_company = re.sub(r"[^a-zA-Z0-9]", "_", company.lower()).strip("_")
    slug_role = re.sub(r"[^a-zA-Z0-9]", "_", role.lower()).strip("_")
    today = date.today().isoformat()
    base_name = f"{slug_company}_{slug_role}_{today}"

    output_dir = cfg.generated_dir
    pdf_path = output_dir / f"{base_name}.pdf"
    notes_path = output_dir / f"{base_name}_notes.md"

    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(str(pdf_path))
    except ImportError:
        html_path = output_dir / f"{base_name}.html"
        html_path.write_text(html, encoding="utf-8")
        pdf_path = html_path

    notes_path.write_text(
        f"# Resume Tailoring Notes — {company} ({role})\n\n{tailoring_notes}",
        encoding="utf-8",
    )

    return str(pdf_path), str(notes_path)
