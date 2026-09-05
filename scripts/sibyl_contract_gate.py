#!/usr/bin/env python3
"""Explicit local Hardhat gate. No deployment, accounts or private keys supplied."""
from pathlib import Path
import os
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]

def main():
    directory = ROOT / 'contracts'
    if not (directory / 'package-lock.json').is_file():
        raise SystemExit('Reviewed package-lock.json is required; do not resolve floating dependencies in CI')
    env = {k:v for k,v in os.environ.items() if k in {'PATH','HOME','SYSTEMROOT','LANG','TEMP','TMP'}}
    for command in (['npm','ci','--ignore-scripts'], ['npm','test','--','--network','hardhat']):
        result = subprocess.run(command,cwd=directory,env=env,stdin=subprocess.DEVNULL,timeout=500)
        if result.returncode:
            return result.returncode
    return subprocess.run([sys.executable,str(ROOT/"scripts/sibyl_abi_crosscheck.py")],
        cwd=ROOT,env=env,stdin=subprocess.DEVNULL,timeout=40).returncode
if __name__ == '__main__': raise SystemExit(main())
