"""Pipeline orchestration — wires search → score → tailor → outreach → sheet update."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from jobhunt.agents.followup import write_followup
from jobhunt.agents.outreach import write_outreach
from jobhunt.agents.scorer import score_jd
from jobhunt.agents.tailor import tailor_resume
from jobhunt.models import RawJob, StagingRow
from jobhunt.resume.generator import generate_tailored_resume
from jobhunt.scrapers import get_active_scrapers
from jobhunt.sheets.client import SheetsClient

if TYPE_CHECKING:
    from jobhunt.config import AppConfig

console = Console()


# ── Stage 1: Search ──


async def run_search(cfg: AppConfig) -> int:
    """Run all enabled scrapers concurrently, deduplicate, and write to RawJobs sheet."""
    scrapers = get_active_scrapers(cfg)
    criteria = cfg.preferences.search

    if not scrapers:
        console.print("[yellow]No scrapers enabled. Check config.yaml sources.[/yellow]")
        return 0

    console.print(f"[cyan]Searching {len(scrapers)} sources...[/cyan]")

    tasks = [scraper.search(criteria) for scraper in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: list[RawJob] = []
    for i, result in enumerate(results):
        name = scrapers[i].name
        if isinstance(result, Exception):
            console.print(f"  [red]✗ {name}: {result}[/red]")
        else:
            console.print(f"  [green]✓ {name}: {len(result)} jobs[/green]")
            all_jobs.extend(result)

    if not all_jobs:
        console.print("[yellow]No jobs found across any source.[/yellow]")
        return 0

    sheets = SheetsClient(cfg)
    existing = sheets.get_existing_hashes(cfg.system.pipeline.dedup_window_days)
    added = sheets.append_raw_jobs(all_jobs, existing)
    console.print(f"[green]Added {added} new jobs (filtered {len(all_jobs) - added} duplicates).[/green]")
    return added


# ── Stage 2: Score ──


def run_score(cfg: AppConfig) -> tuple[int, int]:
    """Score all unscored jobs. Returns (total_scored, total_worth_applying)."""
    sheets = SheetsClient(cfg)
    new_jobs = sheets.get_new_jobs()

    if not new_jobs:
        console.print("[yellow]No unscored jobs found.[/yellow]")
        return 0, 0

    scored = 0
    applied = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scoring jobs...", total=len(new_jobs))

        for job_row in new_jobs[: cfg.system.pipeline.max_jobs_per_run]:
            jd_text = str(job_row.get("jd_text", ""))
            jd_url = str(job_row.get("jd_url", ""))
            company = str(job_row.get("company", ""))
            title = str(job_row.get("title", ""))

            if not jd_text.strip():
                sheets.update_raw_job_status(jd_url, "scored_skip")
                progress.advance(task)
                continue

            result = score_jd(cfg, jd_text)
            scored += 1

            if result.apply:
                applied += 1
                sheets.update_raw_job_status(jd_url, "scored_apply")
                progress.console.print(
                    f"  [green]✓ {result.score}/100[/green] {title} @ {company} → {result.variant}"
                )
            else:
                sheets.update_raw_job_status(jd_url, "scored_skip")
                progress.console.print(
                    f"  [dim]✗ {result.score}/100 {title} @ {company}[/dim]"
                )

            progress.advance(task)

    return scored, applied


# ── Stage 3+4: Tailor + Outreach + PDF ──


def _process_single_job(
    cfg: AppConfig,
    sheets: SheetsClient,
    job_row: dict,
) -> bool:
    """Process a single scored job: tailor → generate PDF → write outreach → update sheet."""
    company = str(job_row.get("company", ""))
    title = str(job_row.get("title", ""))
    jd_url = str(job_row.get("jd_url", ""))
    jd_text = str(job_row.get("jd_text", ""))

    if not jd_text.strip():
        return False

    # Score (if not already scored in this pass)
    result = score_jd(cfg, jd_text)
    if not result.apply:
        sheets.update_raw_job_status(jd_url, "scored_skip")
        return False

    console.print(f"\n[cyan]Processing: {title} @ {company}[/cyan]")

    # Tailor
    console.print("  [dim]Generating tailoring notes...[/dim]")
    tailoring_notes = tailor_resume(cfg, jd_text, result.variant)

    # Generate PDF
    console.print("  [dim]Generating tailored resume PDF...[/dim]")
    try:
        pdf_path, notes_path = generate_tailored_resume(
            cfg, jd_text, tailoring_notes, company, title
        )
    except Exception as e:
        console.print(f"  [yellow]PDF generation failed: {e}[/yellow]")
        pdf_path = ""

    # Outreach
    console.print("  [dim]Writing outreach messages...[/dim]")
    outreach = write_outreach(cfg, company, title, jd_text)

    # Write to StagingReview
    staging = StagingRow(
        company=company,
        title=title,
        jd_url=jd_url,
        score=result.score,
        variant=result.variant,
        summary=result.summary,
        missing_keywords=result.missing_keywords,
        red_flags=result.red_flags,
        tailored_resume_notes=tailoring_notes,
        outreach_draft=outreach,
        resume_pdf_path=pdf_path,
        date_generated=date.today(),
        status="awaiting_review",
    )
    sheets.append_staging_row(staging)
    sheets.update_raw_job_status(jd_url, "processing")

    console.print(f"  [green]✓ Done — score {result.score}, variant: {result.variant}[/green]")
    return True


# ── Stage 5: Follow-ups ──


def run_followups(cfg: AppConfig) -> int:
    """Generate follow-up messages for stale applications."""
    sheets = SheetsClient(cfg)
    stale = sheets.get_stale_applications(cfg.system.schedule.followup_after_days)

    if not stale:
        console.print("[yellow]No stale applications found.[/yellow]")
        return 0

    count = 0
    for row in stale:
        company = str(row.get("company", ""))
        title = str(row.get("title", ""))
        days = row.get("_days_since", 7)

        console.print(f"  [cyan]Follow-up: {title} @ {company} ({days} days)[/cyan]")
        msg = write_followup(cfg, company, title, days)
        console.print(f"  [dim]{msg[:150]}...[/dim]")
        count += 1

    return count


# ── Full Pipeline ──


async def run_full_pipeline(cfg: AppConfig) -> dict:
    """Run the complete pipeline: search → score → tailor → outreach → sheet update."""
    warnings = cfg.validate_keys()
    for w in warnings:
        console.print(f"[yellow]Warning: {w}[/yellow]")

    # Search
    searched = await run_search(cfg)

    # Score
    scored, applied = run_score(cfg)

    # Process (tailor + PDF + outreach) for jobs marked scored_apply
    sheets = SheetsClient(cfg)
    apply_jobs = [
        r for r in sheets._raw_ws.get_all_records()
        if str(r.get("status", "")).strip().lower() == "scored_apply"
    ]

    pdfs = 0
    for job_row in apply_jobs[: cfg.system.pipeline.max_jobs_per_run]:
        if _process_single_job(cfg, sheets, job_row):
            pdfs += 1

    return {
        "searched": searched,
        "scored": scored,
        "applied": applied,
        "pdfs": pdfs,
    }
