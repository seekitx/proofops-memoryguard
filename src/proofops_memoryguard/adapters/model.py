from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import httpx

from ..agent_models import ModelPlan
from ..canonical import domain_hash


class RemoteModelResponseError(RuntimeError):
    """Sanitized remote-provider failure without persisting upstream response text."""


class DeterministicModelAdapter:
    """Development/test planner. Production wiring must reject this Adapter."""

    production_kind = "deterministic_test_planner"

    def health(self) -> dict[str, Any]:
        return {
            "available": True,
            "backend": self.production_kind,
            "production_eligible": False,
        }

    def plan(self, *, context: dict[str, Any], allowed_tools: tuple[str, ...]) -> ModelPlan:
        verdict = str(context["verdict"])
        explanations = {
            "ready": (
                "The recalled baseline matches, so the Agent prepared human review "
                "without gaining payment authority."
            ),
            "deny": (
                "A persisted dispute or revocation changed the Agent path, so "
                "preparation was blocked and escalated."
            ),
            "needs_human": (
                "The recalled evidence is not strong enough for an automated path, "
                "so a human review is required."
            ),
        }
        return ModelPlan(
            explanation=explanations.get(
                verdict,
                "The Agent stopped because an authoritative decision was unavailable.",
            ),
            operator_steps=(
                "Review the causal memory IDs and proof root before taking any external action.",
            ),
            requested_tools=tuple(allowed_tools),
        )


class HttpModelAdapter:
    """Real external planner using an OpenAI-compatible chat-completions endpoint."""

    production_kind = "remote_structured_model"

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 20,
    ) -> None:
        if not url.startswith("https://"):
            raise ValueError("AGENT_MODEL_URL must use HTTPS")
        if not api_key.strip() or not model.strip():
            raise ValueError("remote Agent model requires API key and model name")
        self._url = url
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._openrouter = urlparse(url).hostname in {"openrouter.ai", "www.openrouter.ai"}
        self._available = False
        self._live_call_verified = False
        self._last_success_at: str | None = None
        self._last_error_type: str | None = None
        self._resolved_model: str | None = None
        self._last_generation_id: str | None = None
        self._last_completion_sha256: str | None = None
        self._structured_output_validated = False
        self._health_lock = Lock()
        self._service_tier = (
            "free_experimental"
            if self._openrouter and (model == "openrouter/free" or model.endswith(":free"))
            else "configured_remote"
        )

    def health(self) -> dict[str, Any]:
        with self._health_lock:
            return {
                "available": self._available,
                "backend": self.production_kind,
                "production_eligible": True,
                "production_protocol_eligible": True,
                "production_eligibility_scope": "configured_https_protocol_only",
                "model": self._model,
                "resolved_model": self._resolved_model,
                "generation_id": self._last_generation_id,
                "completion_sha256": self._last_completion_sha256,
                "configured": True,
                "live_call_verified": self._live_call_verified,
                "structured_output_validated": self._structured_output_validated,
                "structured_output_required": True,
                "openrouter_require_parameters": self._openrouter,
                "service_tier": self._service_tier,
                "production_reliability_claimed": False,
                "last_success_at": self._last_success_at,
                "last_error_type": self._last_error_type,
            }

    @staticmethod
    def _parse_plan(content: str, allowed_tools: tuple[str, ...]) -> ModelPlan:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise TypeError("model plan must be a JSON object")
        explanation = str(data.get("explanation", "")).strip()
        raw_steps = data.get("operator_steps", [])
        raw_tools = data.get("requested_tools", [])
        if not explanation or len(explanation) > 1_000:
            raise ValueError("model explanation is missing or too long")
        if not isinstance(raw_steps, list) or not isinstance(raw_tools, list):
            raise TypeError("model plan lists are invalid")
        steps = tuple(str(item).strip() for item in raw_steps[:5] if str(item).strip())
        tools = tuple(str(item).strip() for item in raw_tools[:10] if str(item).strip())
        if any(len(step) > 300 for step in steps) or any(len(tool) > 100 for tool in tools):
            raise ValueError("model plan item exceeds its size limit")
        # Do not discard unknown names here. The Agent executor must visibly suppress them.
        del allowed_tools
        return ModelPlan(explanation, steps, tools)

    def plan(self, *, context: dict[str, Any], allowed_tools: tuple[str, ...]) -> ModelPlan:
        model_context_hash = domain_hash(
            "agent-model-context",
            {"context": context, "allowed_tools": list(allowed_tools)},
        )
        system = (
            "You plan operator-facing steps for a safety Agent. The supplied verdict is final. "
            "You cannot change target, amount, verdict, or authorize payment. Return only "
            "JSON with explanation, operator_steps, and requested_tools. Keep the explanation "
            "under three short sentences and each operator step under one sentence. Request "
            "tools only from the supplied list."
        )
        user = json.dumps(
            {"decision_context": context, "allowed_tools": list(allowed_tools)},
            sort_keys=True,
            separators=(",", ":"),
        )
        response_schema = {
            "type": "object",
            "properties": {
                "explanation": {"type": "string", "maxLength": 1_000},
                "operator_steps": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 300},
                    "maxItems": 5,
                },
                "requested_tools": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 100},
                    "maxItems": 10,
                },
            },
            "required": ["explanation", "operator_steps", "requested_tools"],
            "additionalProperties": False,
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0,
            "max_tokens": 1_000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "memoryguard_operator_plan",
                    "strict": True,
                    "schema": response_schema,
                },
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self._openrouter:
            payload["provider"] = {"require_parameters": True}
        with self._health_lock:
            self._available = False
            self._live_call_verified = False
            self._resolved_model = None
            self._last_generation_id = None
            self._last_completion_sha256 = None
            self._structured_output_validated = False
        try:
            response = httpx.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise RemoteModelResponseError("remote model response must be an object")
            error = body.get("error")
            if error:
                code = error.get("code") if isinstance(error, dict) else "unknown"
                raise RemoteModelResponseError(f"remote model provider error code {code}")
            choices = body.get("choices")
            if not isinstance(choices, list) or not choices:
                raise RemoteModelResponseError("remote model response has no choices")
            first = choices[0]
            if not isinstance(first, dict) or not isinstance(first.get("message"), dict):
                raise RemoteModelResponseError("remote model response has no message")
            content = first["message"].get("content")
            if not isinstance(content, str) or not content:
                raise RemoteModelResponseError("remote model response has no content")
            plan = self._parse_plan(str(content), allowed_tools)
            resolved_model = str(body.get("model", "")).strip() or None
            generation_id = str(body.get("id", "")).strip() or None
            completion_sha256 = sha256(str(content).encode()).hexdigest()
            completed_at = datetime.now(UTC).isoformat()
            receipt = {
                "schema_version": "1.0",
                "backend": self.production_kind,
                "configured_model": self._model,
                "resolved_model": resolved_model,
                "generation_id": generation_id,
                "completion_sha256": completion_sha256,
                "model_context_hash": model_context_hash,
                "live_call_verified": True,
                "structured_output_validated": True,
                "service_tier": self._service_tier,
                "production_reliability_claimed": False,
                "completed_at": completed_at,
            }
            with self._health_lock:
                self._resolved_model = resolved_model
                self._last_generation_id = generation_id
                self._last_completion_sha256 = completion_sha256
                self._structured_output_validated = True
                self._available = True
                self._live_call_verified = True
                self._last_success_at = completed_at
                self._last_error_type = None
            return replace(plan, model_receipt=receipt)
        except Exception as exc:
            with self._health_lock:
                self._available = False
                self._live_call_verified = False
                self._last_error_type = type(exc).__name__
            raise

    def probe(self) -> None:
        self.plan(
            context={
                "probe": True,
                "state": "await_human_review",
                "verdict": "needs_human",
                "reason_codes": ["startup_model_probe"],
                "causal_memory_ids": [],
            },
            allowed_tools=(),
        )
