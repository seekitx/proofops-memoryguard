from apps.api.main import readiness_snapshot


def backend(*, available: bool = True, production_eligible: bool = True) -> dict[str, bool]:
    return {"available": available, "production_eligible": production_eligible}


def test_production_readiness_survives_optional_model_outage() -> None:
    ready, content = readiness_snapshot(
        app_env="production",
        memory=backend(),
        agent={
            "run_ledger": backend(),
            "safe_actions": backend(),
            "model": backend(available=False, production_eligible=True),
        },
    )
    assert ready is True
    assert content["status"] == "ready"
    assert content["model_live"] is False
    assert content["model_degraded"] is True
    assert content["safety_core_ready"] is True
    assert content["model_is_authority_dependency"] is False


def test_production_readiness_rejects_unconfigured_remote_model() -> None:
    ready, content = readiness_snapshot(
        app_env="production",
        memory=backend(),
        agent={
            "run_ledger": backend(),
            "safe_actions": backend(),
            "model": backend(available=False, production_eligible=False),
        },
    )
    assert ready is False
    assert content["status"] == "degraded"


def test_production_readiness_still_fails_closed_without_sibyl() -> None:
    ready, content = readiness_snapshot(
        app_env="production",
        memory=backend(available=False, production_eligible=False),
        agent={
            "run_ledger": backend(),
            "safe_actions": backend(),
            "model": backend(available=True, production_eligible=True),
        },
    )
    assert ready is False
    assert content["status"] == "degraded"
