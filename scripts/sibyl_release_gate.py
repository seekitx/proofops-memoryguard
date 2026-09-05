#!/usr/bin/env python3
"""Unified local release verification. No deployment, live model or wallet actions.

Default records a read-only preflight; --execute explicitly runs local tests,
real SDK probes and local child servers. --contracts executes the pinned npm
installation/test commands ONLY when an existing reviewed lockfile is present.
This gate never publishes posts, marks ready, or awards partner/PMF credit.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("static", "official_sdk", "pytest", "fresh_process", "scenario_matrix",
          "source_experiment", "http_acceptance", "contracts")


def identity():
    def git(*args):
        return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15).stdout.strip()
    return git("rev-parse", "HEAD"), not bool(git("status", "--porcelain", "--untracked-files=normal"))


def hashes(paths):
    files = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def runtime_digest():
    # Byte-for-byte algorithm equivalent to the shipped runtime source_digest.
    files = set()
    for directory, suffixes in (("src", {".py"}), ("apps", {".py", ".js", ".css", ".html"})):
        for path in (ROOT / directory).rglob("*"):
            if (path.is_file() and path.suffix in suffixes
                    and not {"node_modules", "__pycache__", ".next"}.intersection(path.parts)):
                files.add(path)
    for name in ("pyproject.toml", "config/memoryguard-policy.json"):
        if (ROOT / name).is_file():
            files.add(ROOT / name)
    records = []
    for path in sorted(files):
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError("runtime source cannot escape root")
        records.append([path.relative_to(ROOT).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()])
    if not records:
        raise ValueError("empty runtime source set")
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def junit_counts(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    return {"tests": len(cases), "failures": sum(c.find("failure") is not None for c in cases),
            "errors": sum(c.find("error") is not None for c in cases),
            "skipped": sum(c.find("skipped") is not None for c in cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--contracts", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    output = args.out.expanduser().resolve()
    # Logs may contain local paths. Never write them into source/evidence directories.
    if output.is_relative_to(ROOT):
        raise SystemExit("--out must be outside the checkout, to preserve its identity")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit("Choose a new --out path; existing evidence is never overwritten")
    work = output.parent / (output.stem + "-artifacts")
    work.mkdir(mode=0o700, exist_ok=False)
    commit, clean = identity()
    source = runtime_digest()
    verification_digest = hashes(sorted(p for directory in ("src", "apps", "config", "tests", "scripts", "contracts", ".github")
        for p in (ROOT / directory).rglob("*") if p.is_file() and not {"node_modules", "__pycache__", "artifacts", "cache", ".next"}.intersection(p.parts) and p.suffix in {".py", ".js", ".cjs", ".json", ".yml", ".sol", ".html", ".css"}))
    results = {name: {"name": name, "state": "NOT_RUN"} for name in STAGES}
    # Clear deployment and external integration settings from LOCAL probe processes.
    safe = {key: value for key, value in os.environ.items()
            if key in {"PATH", "SYSTEMROOT", "LANG", "HOME", "USER", "TMPDIR", "TEMP", "TMP"}}
    safe.update({"PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
                 "PYTHONDONTWRITEBYTECODE": "1", "BUILD_COMMIT": commit,
                 "AGENT_MODEL_MODE": "deterministic", "APP_ENV": "development"})
    def stage(name, argv, timeout=240, check=None):
        entry = results[name]
        log = work / (name + ".log")
        try:
            with log.open("wb") as stream:
                status = subprocess.run(argv, cwd=ROOT, env=safe, stdout=stream,
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=timeout).returncode
            entry["exit_code"] = status
            if status != 0:
                entry["state"] = "FAILED"
            elif check:
                extra = check()
                entry.update(extra)
                entry["state"] = "PASSED" if extra.pop("gate_ok", False) else "FAILED"
                entry.pop("gate_ok", None)
            else:
                entry["state"] = "PASSED"
        except subprocess.TimeoutExpired:
            entry["state"] = "TIMEOUT"
        except Exception as exc:
            entry.update(state="FAILED", error_type=type(exc).__name__)
        if log.exists():
            entry["log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    try:
        count = 0
        for directory in ("src", "apps", "tests", "scripts"):
            for p in (ROOT / directory).rglob("*.py"):
                if {"node_modules", "__pycache__", ".next"}.intersection(p.parts):
                    continue
                ast.parse(p.read_text(), filename=str(p.relative_to(ROOT)))
                count += 1
        results["static"] = {"name": "static", "state": "PASSED", "parsed_python_files": count}
    except Exception as exc:
        results["static"] = {"name": "static", "state": "FAILED", "error_type": type(exc).__name__}
    if args.execute:
        if not clean or not re.fullmatch(r"[a-f0-9]{40}", commit):
            results["official_sdk"].update(state="BLOCKED", reason="COMMIT_CLEAN_CHANGES_FIRST")
        else:
            stage("official_sdk", [sys.executable, "-c",
                "from proofops_memoryguard.adapters.sibyl_identity import sibyl_sdk_identity; "
                "s=sibyl_sdk_identity(); print(s); assert s['sdk_identity_ready']"])
            if results["official_sdk"]["state"] == "PASSED":
                junit = work / "pytest.xml"
                def test_check():
                    counts = junit_counts(junit)
                    return {**counts, "gate_ok": counts["tests"] > 0 and not (counts["failures"] or counts["errors"] or counts["skipped"])}
                stage("pytest", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                    "--junitxml", str(junit)], timeout=600, check=test_check)
                stage("fresh_process", [sys.executable, "scripts/casework_champion_probe.py", "--out", str(work / "fresh.json")],
                      check=lambda: {"gate_ok": all(json.loads((work / "fresh.json").read_text())["checks"].values())})
                stage("scenario_matrix", [sys.executable, "scripts/casework_benchmark.py", "--backend", "sibyl", "--out", str(work / "matrix.json")])
                stage("source_experiment", [sys.executable, "scripts/casework_source_benchmark.py", "--backend", "sibyl", "--out", str(work / "sources.json")])
                stage("http_acceptance", [sys.executable, "scripts/sibyl_http_acceptance.py", "--out", str(work / "http.json")],
                      check=lambda: {"gate_ok": json.loads((work / "http.json").read_text()).get("all_checks_passed") is True})
            else:
                for name in ("pytest", "fresh_process", "scenario_matrix", "source_experiment", "http_acceptance"):
                    results[name].update(state="BLOCKED", reason="OFFICIAL_SDK_NOT_VERIFIED")
            if args.contracts:
                if not (ROOT / "contracts/package-lock.json").is_file():
                    results["contracts"].update(state="BLOCKED", reason="REVIEW_AND_COMMIT_PACKAGE_LOCK_FIRST")
                elif not shutil.which("npm"):
                    results["contracts"].update(state="BLOCKED", reason="NPM_NOT_INSTALLED")
                else:
                    stage("contracts", [sys.executable, "scripts/sibyl_contract_gate.py"], timeout=600)
    after_commit, after_clean = identity()
    stable = commit == after_commit and after_clean == clean and runtime_digest() == source
    ready = clean and stable and all(row["state"] == "PASSED" for row in results.values())
    report = {"schema_version": "memoryguard-release-gate/1", "captured_at": datetime.now(timezone.utc).isoformat(),
        "build_commit": commit, "git_clean": clean, "source_digest": source,
        "verification_source_digest": verification_digest, "source_stable": stable,
        "mode": "EXECUTED_LOCAL" if args.execute else "PREFLIGHT_ONLY", "stages": list(results.values()),
        "local_release_ready": ready, "contest_submission_ready": False,
        "scope": "Self-recorded local verification only. Hosted browser, remote model, Base, ACP, video and posts require separate evidence.",
        "external_execution_claimed": False, "partner_bonus_claimed": False}
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({"local_release_ready": ready, "stages": {k: v["state"] for k, v in results.items()}, "report": str(output)}, indent=2))
    return 0 if ready else 2

if __name__ == "__main__":
    raise SystemExit(main())
