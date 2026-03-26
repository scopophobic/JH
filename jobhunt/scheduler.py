"""Scheduler — runs the pipeline on a cron schedule using APScheduler."""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

if TYPE_CHECKING:
    from jobhunt.config import AppConfig

console = Console()


def _parse_cron(expr: str) -> dict:
    """Parse a 5-field cron expression into APScheduler CronTrigger kwargs."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {expr}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def _run_full_pipeline_sync(cfg: AppConfig) -> None:
    """Synchronous wrapper for the async pipeline."""
    from jobhunt.pipeline import run_full_pipeline
    console.print(f"\n[cyan]{'='*50}[/cyan]")
    console.print("[cyan]Scheduled pipeline run starting...[/cyan]")
    try:
        results = asyncio.run(run_full_pipeline(cfg))
        console.print(f"[green]Pipeline complete — {results['applied']} applications generated.[/green]")
    except Exception as e:
        console.print(f"[red]Pipeline error: {e}[/red]")


def _run_followups_sync(cfg: AppConfig) -> None:
    """Synchronous wrapper for the follow-up check."""
    from jobhunt.pipeline import run_followups
    console.print(f"\n[cyan]{'='*50}[/cyan]")
    console.print("[cyan]Scheduled follow-up check starting...[/cyan]")
    try:
        count = run_followups(cfg)
        console.print(f"[green]Generated {count} follow-up messages.[/green]")
    except Exception as e:
        console.print(f"[red]Follow-up error: {e}[/red]")


def start_scheduler(cfg: AppConfig) -> None:
    """Start the blocking scheduler with pipeline and follow-up jobs."""
    scheduler = BlockingScheduler()

    search_cron = _parse_cron(cfg.system.schedule.search_cron)
    followup_cron = _parse_cron(cfg.system.schedule.followup_cron)

    scheduler.add_job(
        _run_full_pipeline_sync,
        trigger=CronTrigger(**search_cron),
        args=[cfg],
        id="full_pipeline",
        name="Full Pipeline (search + score + tailor + outreach)",
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        _run_followups_sync,
        trigger=CronTrigger(**followup_cron),
        args=[cfg],
        id="followup_check",
        name="Follow-up Check",
        misfire_grace_time=3600,
    )

    def _shutdown(signum, frame):
        console.print("\n[yellow]Shutting down scheduler...[/yellow]")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    console.print("[green]Scheduler started. Press Ctrl+C to stop.[/green]")
    console.print(f"  Next pipeline run: {scheduler.get_job('full_pipeline').next_run_time}")
    console.print(f"  Next follow-up:    {scheduler.get_job('followup_check').next_run_time}")

    scheduler.start()
