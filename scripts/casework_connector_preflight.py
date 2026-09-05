#!/usr/bin/env python3
"""Local configuration checks only. Does not open a DB, call API or invoke ACP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from proofops_casework.auth import TokenRegistry
from proofops_casework.source_models import ConnectorConfig


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--registry',type=Path,required=True)
    args=parser.parse_args()
    try:
        cfg=ConnectorConfig.from_file(args.config);registry=TokenRegistry.from_file(args.registry)
        visible={(a.tenant_id,subject) for a in registry.actors.values() for subject in a.subjects}
        missing=[]
        for source in cfg.sources:
            if any((source.tenant_id,s) not in visible for s in source.subjects):
                missing.append('SOURCE_SCOPE_NOT_IN_REGISTRY')
            if source.token_env and not os.environ.get(source.token_env):
                missing.append('SOURCE_CREDENTIAL_MISSING')
        for incident in cfg.incidents:
            actor=registry.actors.get(incident.actor_id)
            if not actor or actor.role not in {'owner','investigator'} or incident.scope.subject_id not in actor.subjects:
                missing.append('INCIDENT_ACTOR_INVALID')
            if len(os.environ.get(incident.secret_env,''))<32: missing.append('INCIDENT_SECRET_MISSING')
        if cfg.virtuals:
            path=Path(cfg.virtuals.cli_executable)
            if (not path.is_file() or path.is_symlink() or path.stat().st_mode&0o022
                    or hashlib.sha256(path.read_bytes()).hexdigest()!=cfg.virtuals.cli_sha256):
                missing.append('ACP_WRAPPER_PIN_INVALID')
            if not Path(cfg.virtuals.cli_home).is_dir(): missing.append('ACP_HOME_MISSING')
        output={'state':'CONFIG_VALID_LOCAL_ONLY' if not missing else 'CONFIG_INCOMPLETE',
                'sources':len(cfg.sources),'resolution_policies':len(cfg.policies),
                'incident_sources':len(cfg.incidents),'virtuals_configured':cfg.virtuals is not None,
                'errors':sorted(set(missing)),'network_called':False,'database_opened':False,
                'cli_invoked':False,'runtime_verified':False}
        print(json.dumps(output));return 0 if not missing else 1
    except Exception as exc:
        print(json.dumps({'state':'CONFIG_INVALID','error_type':type(exc).__name__,'runtime_verified':False}));return 2

if __name__=='__main__': raise SystemExit(main())
