from pathlib import Path

from scripts.judge_benchmark import run_benchmark


def test_judge_benchmark_passes_all_twelve_checks(tmp_path: Path) -> None:
    report = run_benchmark(work_dir=tmp_path)

    assert report["uses_official_sibyl_sdk"] is True
    assert report["checks_total"] == 12
    assert report["checks_passed"] == 12
    assert report["all_checks_passed"] is True
    assert report["run_scope"]["single_python_process"] is True
    assert report["run_scope"]["process_restart_proven"] is False
    assert report["run_scope"]["production_agent_run"] is False
