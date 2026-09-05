#!/usr/bin/env python3
"""Verify an explicitly exported report's internal hashes. No network or signing."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from proofops_casework.core import digest


def verify(value):
    if value.get('schema_version')!='casework-report-export/1':
        raise ValueError('unsupported export')
    report=value['report']; record=value.get('source_snapshot')
    if report['report_root']!=digest('investigation',{k:v for k,v in report.items() if k!='report_root'}):
        raise ValueError('report hash mismatch')
    if record is None:
        return {'report_consistent':True,'source_bundle_present':False,'independent_authenticity':False}
    if (record['report_id']!=report['report_id'] or record['case_id']!=report['case_id']
            or record['report_root']!=report['report_root']):
        raise ValueError('source report binding mismatch')
    bundle=record['bundle']
    if bundle['bundle_root']!=digest('evidence-bundle',{k:v for k,v in bundle.items() if k!='bundle_root'}):
        raise ValueError('source bundle hash mismatch')
    events=[x for x in report['trace'] if x.get('tool')=='evidence.inspect']
    if len(events)!=1 or events[0]['output_hash']!=digest('tool-output',bundle):
        raise ValueError('report tool trace mismatch')
    return {'report_consistent':True,'source_bundle_present':True,'trace_bound':True,
            'independent_authenticity':False,'freshness_reverified':False,'executable':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export',type=Path);args=parser.parse_args()
    try:
        if args.export.is_symlink() or args.export.stat().st_size>1_000_000:
            raise ValueError('invalid export file')
        result=verify(json.loads(args.export.read_bytes()))
        print(json.dumps(result));return 0
    except (KeyError,TypeError,ValueError,OSError) as exc:
        print(json.dumps({'consistent':False,'error':type(exc).__name__}));return 1

if __name__=='__main__': raise SystemExit(main())
