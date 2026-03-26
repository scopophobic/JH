"""Google Sheets client — CRUD for RawJobs and StagingReview tabs."""

from __future__ import annotations

import hashlib
import os
from datetime import date, timedelta
from typing import TYPE_CHECKING

import gspread
from google.oauth2.service_account import Credentials

from jobhunt.models import RawJob, StagingRow

if TYPE_CHECKING:
    from jobhunt.config import AppConfig

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsClient:
    def __init__(self, cfg: AppConfig):
        self._cfg = cfg
        creds_path = os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "./credentials/google_service_account.json",
        )
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self._gc = gspread.authorize(creds)
        self._spreadsheet = self._gc.open_by_key(cfg.system.sheets.spreadsheet_id)

    @property
    def _raw_ws(self) -> gspread.Worksheet:
        return self._spreadsheet.worksheet(self._cfg.system.sheets.raw_jobs_tab)

    @property
    def _staging_ws(self) -> gspread.Worksheet:
        return self._spreadsheet.worksheet(self._cfg.system.sheets.staging_tab)

    # ── Deduplication ──

    @staticmethod
    def _job_hash(company: str, title: str) -> str:
        key = f"{company.strip().lower()}|{title.strip().lower()}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get_existing_hashes(self, window_days: int = 30) -> set[str]:
        """Get dedup hashes for jobs found within the window."""
        rows = self._raw_ws.get_all_records()
        cutoff = date.today() - timedelta(days=window_days)
        hashes: set[str] = set()
        for row in rows:
            try:
                found = date.fromisoformat(str(row.get("date_found", "")))
                if found >= cutoff:
                    hashes.add(self._job_hash(
                        str(row.get("company", "")),
                        str(row.get("title", "")),
                    ))
            except (ValueError, TypeError):
                continue
        return hashes

    # ── RawJobs ──

    def append_raw_jobs(self, jobs: list[RawJob], existing_hashes: set[str] | None = None) -> int:
        """Append new jobs to RawJobs, skipping duplicates. Returns count added."""
        if existing_hashes is None:
            existing_hashes = self.get_existing_hashes(
                self._cfg.system.pipeline.dedup_window_days
            )

        new_rows: list[list[str]] = []
        for job in jobs:
            h = self._job_hash(job.company, job.title)
            if h in existing_hashes:
                continue
            existing_hashes.add(h)
            new_rows.append([
                job.title,
                job.company,
                job.jd_url,
                job.jd_text,
                job.source,
                job.date_found.isoformat(),
                job.status,
            ])

        if new_rows:
            self._raw_ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        return len(new_rows)

    def get_new_jobs(self) -> list[dict]:
        """Read all rows with status='new' from RawJobs."""
        rows = self._raw_ws.get_all_records()
        return [r for r in rows if str(r.get("status", "")).strip().lower() == "new"]

    def update_raw_job_status(self, jd_url: str, new_status: str) -> None:
        """Update the status of a job in RawJobs by jd_url."""
        cell = self._raw_ws.find(jd_url, in_column=3)
        if cell:
            status_col = 7  # status is column G
            self._raw_ws.update_cell(cell.row, status_col, new_status)

    # ── StagingReview ──

    def append_staging_row(self, row: StagingRow) -> None:
        """Append a processed application to StagingReview."""
        self._staging_ws.append_row(
            [
                row.company,
                row.title,
                row.jd_url,
                row.score,
                row.variant,
                row.summary,
                row.missing_keywords,
                row.red_flags,
                row.tailored_resume_notes,
                row.outreach_draft,
                row.resume_pdf_path,
                row.date_generated.isoformat(),
                row.status,
                row.your_notes,
                row.date_sent,
            ],
            value_input_option="USER_ENTERED",
        )

    def get_stale_applications(self, days: int = 7) -> list[dict]:
        """Get applications with status='sent' that are older than `days`."""
        rows = self._staging_ws.get_all_records()
        cutoff = date.today() - timedelta(days=days)
        stale: list[dict] = []
        for row in rows:
            if str(row.get("status", "")).strip().lower() != "sent":
                continue
            try:
                sent = date.fromisoformat(str(row.get("date_sent", "")))
                if sent <= cutoff:
                    row["_days_since"] = (date.today() - sent).days
                    stale.append(row)
            except (ValueError, TypeError):
                continue
        return stale

    def get_stats(self) -> dict[str, int]:
        """Get summary statistics for the status command."""
        raw_rows = self._raw_ws.get_all_records()
        staging_rows = self._staging_ws.get_all_records()

        raw_statuses: dict[str, int] = {}
        for r in raw_rows:
            s = str(r.get("status", "unknown")).strip().lower()
            raw_statuses[s] = raw_statuses.get(s, 0) + 1

        staging_statuses: dict[str, int] = {}
        for r in staging_rows:
            s = str(r.get("status", "unknown")).strip().lower()
            staging_statuses[s] = staging_statuses.get(s, 0) + 1

        return {
            "Total raw jobs": len(raw_rows),
            "New (unscored)": raw_statuses.get("new", 0),
            "Skipped (low score)": raw_statuses.get("scored_skip", 0),
            "Total applications": len(staging_rows),
            "Awaiting review": staging_statuses.get("awaiting_review", 0),
            "Approved": staging_statuses.get("approved", 0),
            "Sent": staging_statuses.get("sent", 0),
            "Replied": staging_statuses.get("replied", 0),
            "Rejected": staging_statuses.get("rejected", 0),
        }
