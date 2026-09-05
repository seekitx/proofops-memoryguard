import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(importlib.util.find_spec("sibyl_memory_client") is None,
                    reason="Official Sibyl SDK absent; never substitute a fixture for this test")
def test_official_sdk_two_process_and_real_disposable_deletion(tmp_path):
    root=Path(__file__).resolve().parents[2]
    # tests/casework -> tests -> repository
    script=root/"scripts/casework_process_probe.py"
    output=tmp_path/"probe.json"
    result=subprocess.run([sys.executable,str(script),"--out",str(output)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(output.read_text())
    assert all(report["checks"].values())
