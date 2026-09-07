#!/usr/bin/env python3
"""Read a purchased Gloria job and optionally quarantine its news in MemoryGuard.

No job creation, payments, risk opening, review acceptance or reconsideration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import urlparse

PROVIDER = "0x1e895e004049ccc630956163391ed4fcf89eeb0d"
BUYER = "0xf7f81100d5fca4e1b3e5ccfd67ac9ba75f2640b6"


def private_text(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise ValueError("Credential must be a private regular file (0600)")
    if info.st_size > 64000:
        raise ValueError("Credential file too large")
    return path.read_text().strip()


def request(url, header, body=None):
    if any(c in header for c in '\r\n"\\'):
        raise ValueError("Invalid credential encoding")
    args = ["curl", "--silent", "--show-error", "--fail", "--max-time", "25",
            "--max-filesize", "256000", "--proto", "=https", "--config", "-", url]
    config = 'header = "' + header + '"\n'
    if body is not None:
        args += ["--request", "POST", "--data", json.dumps(body, ensure_ascii=False)]
        config += 'header = "Content-Type: application/json"\n'
    result = subprocess.run(args, input=config, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Remote request failed; no automatic retry (curl %d)" % result.returncode)
    if len(result.stdout.encode()) > 256000:
        raise ValueError("Response too large")
    return json.loads(result.stdout)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job-id", required=True)
    p.add_argument("--acp-credentials", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--import-notes", action="store_true")
    p.add_argument("--memoryguard-token", type=Path)
    p.add_argument("--scope", type=Path, help="Existing authorized Scope JSON")
    a = p.parse_args()
    if not re.fullmatch(r"[0-9]{1,20}", a.job_id):
        raise ValueError("Invalid job ID")
    a.out.mkdir(parents=True, exist_ok=False)
    key = json.loads(private_text(a.acp_credentials))["data"]["apiKey"]
    response = request("https://claw-api.virtuals.io/acp/jobs/" + a.job_id, "x-api-key: " + key)
    j = response["data"]
    if (str(j["id"]) != a.job_id or j["providerAddress"].lower() != PROVIDER
            or j["clientAddress"].lower() != BUYER
            or j["phase"] not in {"EVALUATION", "COMPLETED"}):
        raise ValueError("Job identity or delivery state mismatch")
    requirements = json.loads(j["memos"][0]["content"])
    if requirements.get("name") != "news" or requirements.get("requirement") != {"news_category": "AI AGENTS"}:
        raise ValueError("Purchased offering/request mismatch")
    delivery = j["deliverable"]
    news = delivery["value"]["news"]
    if not isinstance(news, list) or not 1 <= len(news) <= 30:
        raise ValueError("Unexpected news count")
    texts = []
    for item in news:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ["signal", "short_context", "tweet_url"]):
            raise ValueError("Malformed news item")
        link = urlparse(item["tweet_url"])
        if link.scheme != "https" or link.hostname not in {"x.com", "twitter.com"}:
            raise ValueError("Unexpected source link; links are never fetched automatically")
        text = canonical({"source": "Gloria", "job_id": a.job_id, "untrusted": True,
                          "claim_truth_verified": False, "article": item})
        if len(text) > 10000:
            raise ValueError("Article exceeds MemoryGuard note limit")
        texts.append(text)
    (a.out / "job.json").write_text(json.dumps(response, ensure_ascii=False, indent=2))
    (a.out / "news.json").write_text(json.dumps(news, ensure_ascii=False, indent=2))
    summary = {"job_id": a.job_id, "provider": "Gloria", "phase": j["phase"],
               "completed": j["phase"] == "COMPLETED", "article_count": len(news),
               "delivery_sha256": hashlib.sha256(canonical(delivery).encode()).hexdigest(),
               "source_truth_verified": False, "independent_security_review": False,
               "authority": False, "imported_notes": []}
    if a.import_notes:
        if not a.memoryguard_token or not a.scope:
            raise ValueError("Import requires operator token and existing authorized scope")
        header = "Authorization: Bearer " + private_text(a.memoryguard_token)
        base = "https://memoryguard.eyesonchain.xyz"
        before = request(base + "/api/v2/casework", header)
        scope = json.loads(a.scope.read_text())
        if not any(t["intent"]["scope"] == scope for t in before["tasks"]):
            raise ValueError("Scope must match an existing visible task")
        revision = before["revision"]
        for i, text in enumerate(texts):
            digest = hashlib.sha256(text.encode()).hexdigest()
            body = {"scope": scope, "text": text, "expected_revision": revision,
                    "session_id": "gloria_news_" + a.job_id,
                    "idempotency_key": "gloria_" + digest[:48]}
            result = request(base + "/api/v2/notes", header, body)
            if (result.get("status") != "QUARANTINED" or result.get("authority") is not False
                    or result.get("model_received_raw_text") is not False):
                raise ValueError("Unexpected quarantine result; stopped")
            summary["imported_notes"].append(result)
            (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
            revision = request(base + "/api/v2/health", header)["revision"]
        after = request(base + "/api/v2/casework", header)
        summary["task_statuses_unchanged"] = ({t["task_id"]: t["status"] for t in before["tasks"]}
                                             == {t["task_id"]: t["status"] for t in after["tasks"]})
        summary["memory_backend"] = after["memory_backend"]
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise SystemExit("Gloria handoff stopped: " + str(exc))
