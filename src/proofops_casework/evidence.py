"""A public allowlist of explicitly exported synthetic evidence, never a DB proxy."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .models import Digest, StrictModel

StrictBool = Annotated[bool, Field(strict=True)]
Commit = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]


class CaptureChecks(StrictModel):
    same_action: StrictBool
    same_build: StrictBool
    different_runtime_a_b: StrictBool
    different_process_a_b: StrictBool
    exact_dispute_recalled: StrictBool
    denied_review_blocked: StrictBool
    escalation_persisted: StrictBool
    unrelated_stays_ready: StrictBool
    partial_resolution_still_denied: StrictBool
    all_resolved_needs_review: StrictBool
    restored_with_new_proof: StrictBool
    descendant_recovered: StrictBool
    deleted_memory_stops_core: StrictBool


class PublicCapture(StrictModel):
    schema_version: Literal["casework-public-evidence/2.1"] = "casework-public-evidence/2.1"
    captured_at: datetime
    build_commit: Commit
    source_digest: Digest
    git_clean: StrictBool
    backend: Literal["OFFICIAL_SIBYL", "TEST_DOUBLE"]
    sdk_version: Annotated[str, Field(pattern=r"^[0-9A-Za-z.+_-]{1,64}$")]
    process_count: Annotated[int, Field(strict=True, ge=0, le=32)]
    checks: CaptureChecks
    remote_reports: Annotated[int, Field(strict=True, ge=0, le=500)] = 0
    synthetic_data: Literal[True] = True
    independent_evaluation: Literal[False] = False
    continuous_video: Literal[False] = False
    partner_bonus_awarded: Literal[False] = False
    executable: Literal[False] = False

    @field_validator("captured_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capture timestamp needs timezone")
        return value.astimezone(timezone.utc)


def source_digest(root: Path) -> str:
    """Hash files shipped by this app, independent of mtime and .git availability.

    Deliberately excludes evidence/media/credentials, test outputs and node_modules.
    This is a runtime source fingerprint, not a reproducible container attestation.
    """
    root = root.resolve()
    files: set[Path] = set()
    for directory, suffixes in (("src", {".py"}), ("apps", {".py", ".js", ".css", ".html"})):
        for path in (root / directory).rglob("*"):
            if (path.is_file() and path.suffix in suffixes
                    and not {"node_modules", "__pycache__", ".next"}.intersection(path.parts)):
                files.add(path)
    for name in ("pyproject.toml", "config/memoryguard-policy.json"):
        if (root / name).is_file():
            files.add(root / name)
    records = []
    for path in sorted(files):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("runtime source cannot escape root")
        records.append([path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()])
    if not records:
        raise ValueError("empty runtime source set")
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def git_identity(root: Path) -> tuple[str, bool]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                              text=True, timeout=15).stdout.strip()
    return git("rev-parse", "HEAD"), not bool(git("status", "--porcelain", "--untracked-files=normal"))


def public_summary(path: Path | None, *, current_commit: str | None,
                   current_source_digest: str | None) -> dict:
    result = {"schema_version": "casework-evidence-summary/2.1", "state": "NOT_RECORDED",
              "current_build_commit": current_commit, "current_source_digest": current_source_digest,
              "current_build_matches": False, "source_matches": False,
              "contest_gate_awarded": False, "partner_bonus_awarded": False,
              "scope": "Self-recorded synthetic engineering evidence; not a video, PMF, independent audit or judge award.",
              "executable": False}
    if path is None:
        return result
    try:
        if not path.is_file():
            return result
        if path.stat().st_size > 256_000:
            raise ValueError("capture too large")
        payload = path.read_bytes()
        if len(payload) > 256_000:
            raise ValueError("capture too large")
        capture = PublicCapture.model_validate_json(payload)
        build_matches = capture.build_commit == current_commit
        source_matches = capture.source_digest == current_source_digest
        passed = all(capture.checks.model_dump().values())
        if capture.backend != "OFFICIAL_SIBYL":
            status = "TEST_ONLY"
        elif not (build_matches and source_matches and capture.git_clean):
            status = "HISTORICAL_OR_UNCOMMITTED"
        elif not passed or capture.process_count < 3:
            status = "CHECKS_INCOMPLETE"
        else:
            status = "CURRENT_SELF_RECORDED"
        return result | {"state": status, "current_build_matches": build_matches,
                         "source_matches": source_matches, "capture": capture.model_dump(mode="json"),
                         "artifact_sha256": hashlib.sha256(payload).hexdigest()}
    except (OSError, ValueError):
        return result | {"state": "INVALID_ARTIFACT"}
