from __future__ import annotations

import json
from typing import Any

import pytest

from proofops_memoryguard.adapters.model import HttpModelAdapter
from proofops_memoryguard.canonical import domain_hash


class FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


def test_openrouter_requests_strict_structured_output(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, Any] = {}

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs["json"])
        return FakeResponse(
            {
                "id": "gen_test_123",
                "model": "nvidia/example:free",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "explanation": "Stop for human review.",
                                    "operator_steps": ["Inspect the proof root."],
                                    "requested_tools": [],
                                }
                            )
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr("proofops_memoryguard.adapters.model.httpx.post", fake_post)
    adapter = HttpModelAdapter(
        url="https://openrouter.ai/api/v1/chat/completions",
        api_key="test-key",
        model="openrouter/free",
    )

    plan = adapter.plan(
        context={"verdict": "ready"},
        allowed_tools=("human_review.prepare",),
    )

    assert captured["provider"] == {"require_parameters": True}
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert captured["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert adapter.health()["resolved_model"] == "nvidia/example:free"
    assert adapter.health()["generation_id"] == "gen_test_123"
    assert len(adapter.health()["completion_sha256"]) == 64
    assert adapter.health()["structured_output_validated"] is True
    assert adapter.health()["service_tier"] == "free_experimental"
    assert adapter.health()["production_reliability_claimed"] is False
    assert adapter.health()["live_call_verified"] is True
    assert adapter.health()["production_protocol_eligible"] is True
    assert adapter.health()["production_eligibility_scope"] == ("configured_https_protocol_only")
    assert plan.model_receipt == {
        "schema_version": "1.0",
        "backend": "remote_structured_model",
        "configured_model": "openrouter/free",
        "resolved_model": "nvidia/example:free",
        "generation_id": "gen_test_123",
        "completion_sha256": adapter.health()["completion_sha256"],
        "model_context_hash": domain_hash(
            "agent-model-context",
            {
                "context": {"verdict": "ready"},
                "allowed_tools": ["human_review.prepare"],
            },
        ),
        "live_call_verified": True,
        "structured_output_validated": True,
        "service_tier": "free_experimental",
        "production_reliability_claimed": False,
        "completed_at": adapter.health()["last_success_at"],
    }


def test_generic_compatible_endpoint_does_not_send_openrouter_provider(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, Any] = {}

    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs["json"])
        return FakeResponse(
            {
                "id": "gen_generic_123",
                "model": "provider/model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "explanation": "Escalate safely.",
                                    "operator_steps": [],
                                    "requested_tools": ["operator_escalation.create"],
                                }
                            )
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr("proofops_memoryguard.adapters.model.httpx.post", fake_post)
    adapter = HttpModelAdapter(
        url="https://models.example.test/v1/chat/completions",
        api_key="test-key",
        model="provider/model",
    )

    adapter.probe()

    assert "provider" not in captured
    assert captured["response_format"]["type"] == "json_schema"
    assert adapter.health()["production_reliability_claimed"] is False


def test_provider_error_is_sanitized_and_fails_closed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        return FakeResponse(
            {
                "id": "gen_failed_123",
                "error": {
                    "code": 502,
                    "message": "private provider detail must not be persisted",
                },
            }
        )

    monkeypatch.setattr("proofops_memoryguard.adapters.model.httpx.post", fake_post)
    adapter = HttpModelAdapter(
        url="https://openrouter.ai/api/v1/chat/completions",
        api_key="test-key",
        model="openrouter/free",
    )

    with pytest.raises(RuntimeError, match="provider error code 502") as error:
        adapter.probe()

    assert "private provider detail" not in str(error.value)
    assert adapter.health()["available"] is False
    assert adapter.health()["live_call_verified"] is False
    assert adapter.health()["last_error_type"] == "RemoteModelResponseError"
