from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone, timedelta

from ..core import CaseworkError, digest
from .http_client import BoundedHTTP


class GitHubIssueSource:
    def __init__(self, http=None):
        self.http = http or BoundedHTTP()

    @staticmethod
    def resource(spec, resource: str, scope):
        match = re.fullmatch(r"([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+)#([1-9][0-9]{0,9})", resource)
        if not match or match[1].lower() not in spec.repositories:
            raise CaseworkError("GITHUB_RESOURCE_NOT_ALLOWLISTED", 403)
        return f"{match[1].lower()}#{match[2]}"

    def fetch(self, spec, resource: str, scope, at):
        resource = self.resource(spec, resource, scope)
        repo, number = resource.split("#")
        url = f"https://api.github.com/repos/{repo}/issues/{number}"
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
        if spec.token_env:
            token = os.environ.get(spec.token_env, "")
            if not token:
                raise CaseworkError("SOURCE_CREDENTIAL_NOT_CONFIGURED", 503)
            headers["Authorization"] = f"Bearer {token}"
        data, raw = self.http.json("GET", url, headers=headers)
        if (data.get("url", "").lower() != url or (type(data.get("number")) is not int or data["number"] != int(number))
                or "pull_request" in data or data.get("state") not in {"open", "closed"}):
            raise CaseworkError("GITHUB_ISSUE_IDENTITY_INVALID", 502)
        try:
            updated = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            if updated.tzinfo is None or updated > at.replace(microsecond=0) + timedelta(minutes=5):
                raise ValueError("invalid update time")
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise CaseworkError("SOURCE_TIMESTAMP_INVALID", 502) from exc
        closed_at = data.get("closed_at")
        try:
            if closed_at is not None:
                closed_time = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                if closed_time.tzinfo is None or closed_time > updated:
                    raise ValueError("invalid close time")
                closed_at = closed_time.astimezone(timezone.utc).isoformat()
            if any(data.get(k) is not None and not isinstance(data[k], str) for k in ("title", "body")):
                raise ValueError("invalid free-text shape")
        except (ValueError, TypeError, AttributeError) as exc:
            raise CaseworkError("SOURCE_SCHEMA_INVALID", 502) from exc
        # Title/body/author are deliberately absent. Closed issue != risk resolved.
        facts = {"repository": repo, "issue_number": int(number), "state": data["state"],
                 "updated_at": updated.astimezone(timezone.utc).isoformat(),
                 "closed_at": closed_at,
                 "text_digest": digest("github-untrusted-text", [data.get("title"), data.get("body")])}
        return {"facts": facts, "payload_sha256": hashlib.sha256(raw).hexdigest(),
                "provenance": "GITHUB_API_OBSERVED", "external_calls": 1,
                "claim_boundary": "API snapshot; not fact truth, customer identity or resolution authority"}
