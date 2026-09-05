"""Public, tightly allowlisted synthetic source experiment summary. Never a DB reader."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CHECKS = {"new_service_reuses_cache", "expired_source_invalidates_report",
          "expired_source_refetched", "failed_refresh_visible",
          "failed_refresh_does_not_reuse_old_evidence", "case_not_auto_resolved"}


def public_source_experiment(path: Path | None, *, commit: str | None, source_digest: str | None) -> dict:
    boundary={"scope":"Self-recorded synthetic HTTP experiment, not live GitHub/Base/ACP, invoice savings, PMF or independent testing",
              "current_build_commit":commit,"partner_bonus_claimed":False,"executable":False}
    if path is None or not path.is_file(): return boundary|{"state":"NOT_RECORDED"}
    try:
        if path.is_symlink() or path.stat().st_size>256_000: raise ValueError()
        value=json.loads(path.read_bytes())
        if (value.get("schema_version")!="casework-source-experiment/1"
                or value.get("external_network")!="SYNTHETIC_HTTP_TRANSPORT"
                or value.get("backend") not in {"OFFICIAL_SIBYL","TEST_DOUBLE"}
                or type(value.get("git_clean")) is not bool): raise ValueError()
        import re
        if not re.fullmatch(r"[0-9a-f]{40}",value.get("build_commit","")): raise ValueError()
        if not re.fullmatch(r"[0-9a-f]{64}",value.get("source_digest","")): raise ValueError()
        at=datetime.fromisoformat(value["captured_at"].replace("Z","+00:00"))
        if at.tzinfo is None or at > datetime.now(timezone.utc): raise ValueError()
        rows=value["arms"]
        if not isinstance(rows,list) or len(rows)!=2: raise ValueError()
        arms={}
        for row in rows:
            name=row["arm"]; requests=row["requests_in_comparison"]; logical=row["logical_reads"]; checks=row["checks"]
            if (name not in {"durable_cache","always_refresh"} or name in arms
                    or type(logical) is not int or not 2<=logical<=40
                    or type(requests) is not int or not 1<=requests<=logical
                    or set(checks)!=CHECKS or any(type(v) is not bool for v in checks.values())): raise ValueError()
            arms[name]={"requests":requests,"logical_reads":logical,"checks":checks}
        if arms['durable_cache']['logical_reads']!=arms['always_refresh']['logical_reads']: raise ValueError()
        matched=value['build_commit']==commit and value['source_digest']==source_digest and value['git_clean']
        all_passed=all(all(row['checks'].values()) for row in arms.values())
        state=("TEST_DOUBLE_RECORD" if value['backend']=='TEST_DOUBLE' else
               "HISTORICAL_OR_UNCOMMITTED" if not matched else
               "CHECKS_INCOMPLETE" if not all_passed else "CURRENT_SYNTHETIC_SELF_RECORD")
        return boundary|{"state":state,"capture_build_commit":value['build_commit'],"source_matches":matched,
                         "captured_at":at.isoformat(),"backend":value['backend'],"arms":arms,
                         "local_request_reduction_fraction":1-arms['durable_cache']['requests']/arms['always_refresh']['requests']}
    except (ValueError,KeyError,TypeError,OSError,AttributeError):
        return boundary|{"state":"INVALID_EXPORT"}
