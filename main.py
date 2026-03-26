"""JobHunt CLI — entry point for all pipeline commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="jobhunt",
    help="Automated job search, scoring, resume tailoring, and outreach pipeline.",
    no_args_is_help=True,
)
console = Console()


def _get_config():
    from jobhunt.config import load_config
    return load_config()


@app.command()
def init():
    """Create a fresh profile/ folder with template files for a new user."""
    import shutil
    profile = Path("profile")
    if profile.exists() and any(profile.iterdir()):
        console.print("[yellow]profile/ folder already exists and has files.[/yellow]")
        overwrite = typer.confirm("Overwrite with blank templates?", default=False)
        if not overwrite:
            raise typer.Abort()

    profile.mkdir(exist_ok=True)
    (profile / "generated").mkdir(exist_ok=True)

    template_profile = {
        "name": "Your Name",
        "email": "you@example.com",
        "phone": "+91-XXXXXXXXXX",
        "location": "Your City, Country",
        "graduation": "Year, Degree, University",
        "links": {
            "github": "https://github.com/yourusername",
            "portfolio": "https://yoursite.dev",
            "linkedin": "https://linkedin.com/in/yourusername",
            "leetcode": "",
        },
        "experience": [
            {
                "title": "Role Title",
                "company": "Company Name",
                "period": "Start – End",
                "stack": ["Python", "Django"],
                "bullets": [
                    "What you built or accomplished",
                    "Quantified impact",
                ],
            }
        ],
        "open_source": [],
        "projects": [
            {
                "name": "Project Name",
                "description": "One-line description",
                "stack": ["React", "Node.js"],
                "highlights": ["Key achievement"],
            }
        ],
        "skills": {
            "languages": ["Python", "JavaScript"],
            "frameworks": ["Django", "React"],
            "databases": ["PostgreSQL"],
            "tools": ["Git", "Docker"],
        },
        "achievements": ["Notable achievement"],
        "certifications": ["Certification Name (Provider)"],
    }
    template_prefs = {
        "search": {
            "roles": ["Software Engineer", "Backend Engineer"],
            "locations": ["Remote", "Your City"],
            "experience_years": [0, 2],
            "keywords": ["python", "backend"],
            "exclude_keywords": ["senior", "staff", "10+ years"],
            "target_companies": [],
        },
        "resume_variants": {
            "backend": "Emphasise backend experience...",
            "fullstack": "Balance frontend and backend...",
        },
        "outreach": {
            "tone": "direct, credential-first, no fluff",
            "sign_off": "Your Name",
            "no_openers": ["I've always been passionate about"],
            "strongest_credentials": {
                "default": "Your strongest credential here",
            },
        },
    }

    import yaml
    with open(profile / "profile.yaml", "w", encoding="utf-8") as f:
        f.write("# Edit this file with your personal info\n")
        yaml.dump(template_profile, f, default_flow_style=False, sort_keys=False)

    with open(profile / "preferences.yaml", "w", encoding="utf-8") as f:
        f.write("# Edit this file with your job search preferences\n")
        yaml.dump(template_prefs, f, default_flow_style=False, sort_keys=False)

    (profile / "base_resume.md").write_text(
        "# Your Name\n\nPaste your full resume here in markdown format.\n",
        encoding="utf-8",
    )

    console.print("[green]Profile folder created![/green]")
    console.print("Edit these files to get started:")
    console.print("  profile/profile.yaml      — your identity & experience")
    console.print("  profile/preferences.yaml   — search criteria & outreach style")
    console.print("  profile/base_resume.md     — your resume in markdown")


@app.command()
def validate():
    """Check that profile/ and config.yaml are properly filled in."""
    cfg = _get_config()
    warnings = cfg.validate_keys()

    if cfg.profile.name in ("Your Name", ""):
        warnings.append("profile/profile.yaml: name is still the placeholder")
    if cfg.profile.email in ("you@example.com", "your.email@example.com", ""):
        warnings.append("profile/profile.yaml: email is still the placeholder")
    if not cfg.profile.experience:
        warnings.append("profile/profile.yaml: no experience entries")
    if not cfg.preferences.search.roles:
        warnings.append("profile/preferences.yaml: no target roles defined")
    if not cfg.base_resume_md or "Paste your full resume" in cfg.base_resume_md:
        warnings.append("profile/base_resume.md: still has placeholder content")

    if warnings:
        console.print("[yellow]Issues found:[/yellow]")
        for w in warnings:
            console.print(f"  [red]✗[/red] {w}")
    else:
        console.print("[green]All checks passed — ready to run![/green]")


@app.command()
def search():
    """Run job search across all enabled sources."""
    cfg = _get_config()
    from jobhunt.pipeline import run_search
    import asyncio
    count = asyncio.run(run_search(cfg))
    console.print(f"[green]Found {count} new jobs.[/green]")


@app.command()
def score():
    """Score all unscored jobs in the RawJobs sheet."""
    cfg = _get_config()
    from jobhunt.pipeline import run_score
    scored, applied = run_score(cfg)
    console.print(f"[green]Scored {scored} jobs — {applied} worth applying to.[/green]")


@app.command()
def process():
    """Run the full pipeline: search → score → tailor → outreach → update sheet."""
    cfg = _get_config()
    from jobhunt.pipeline import run_full_pipeline
    import asyncio
    results = asyncio.run(run_full_pipeline(cfg))
    console.print(f"\n[green]Pipeline complete![/green]")
    console.print(f"  Jobs found:    {results['searched']}")
    console.print(f"  Jobs scored:   {results['scored']}")
    console.print(f"  Applications:  {results['applied']}")
    console.print(f"  PDFs generated: {results['pdfs']}")


@app.command()
def followup():
    """Generate follow-up messages for stale applications."""
    cfg = _get_config()
    from jobhunt.pipeline import run_followups
    count = run_followups(cfg)
    console.print(f"[green]Generated {count} follow-up messages.[/green]")


@app.command()
def run():
    """Start the scheduler — runs search daily and follow-ups weekly."""
    cfg = _get_config()
    from jobhunt.scheduler import start_scheduler
    console.print("[cyan]Starting scheduler...[/cyan]")
    console.print(f"  Search:    {cfg.system.schedule.search_cron}")
    console.print(f"  Follow-up: {cfg.system.schedule.followup_cron}")
    start_scheduler(cfg)


@app.command()
def status():
    """Show pipeline statistics from the Google Sheet."""
    cfg = _get_config()
    from jobhunt.sheets.client import SheetsClient

    client = SheetsClient(cfg)

    table = Table(title="JobHunt Pipeline Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")

    stats = client.get_stats()
    for label, count in stats.items():
        table.add_row(label, str(count))

    console.print(table)


if __name__ == "__main__":
    app()
