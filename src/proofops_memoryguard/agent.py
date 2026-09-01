from __future__ import annotations

from dataclasses import replace
from typing import Any

from .agent_models import (
    AgentHumanSignal,
    AgentRun,
    AgentState,
    GuardedPaymentGoal,
    ModelPlan,
    ToolEvent,
    ToolPhase,
)
from .canonical import domain_hash, subject_ref
from .errors import (
    DecisionNotFoundError,
    FinalizationError,
    MemoryConflictError,
    MemoryIntegrityError,
)
from .models import AnchorState, DecisionDraft, Verdict, utc_now
from .module import MemoryGuard
from .ports import ModelPort, RunLedgerPort, SafetyActionPort
from .proof import validate_decision

_REVIEW_TOOL = "human_review.prepare"
_ESCALATION_TOOL = "operator_escalation.create"
_BRIEF_TOOL = "causal_evidence_brief.prepare"
_REGISTERED_TOOLS = (_REVIEW_TOOL, _ESCALATION_TOOL, _BRIEF_TOOL)


class _Trace:
    def __init__(self) -> None:
        self.events: list[ToolEvent] = []

    def add(
        self,
        tool: str,
        phase: ToolPhase,
        reason: str,
        input_value: Any,
        output_value: Any | None = None,
    ) -> None:
        self.events.append(
            ToolEvent(
                sequence=len(self.events) + 1,
                tool=tool,
                phase=phase,
                reason_code=reason,
                input_hash=domain_hash(f"agent-tool-input:{tool}", input_value),
                output_hash=(
                    domain_hash(f"agent-tool-output:{tool}", output_value)
                    if output_value is not None
                    else None
                ),
            )
        )


class MemoryGuardAgent:
    """Goal-driven Agent whose tool authority is reduced from MemoryGuard verdicts."""

    def __init__(
        self,
        *,
        guard: MemoryGuard,
        model: ModelPort,
        ledger: RunLedgerPort,
        actions: SafetyActionPort,
        runtime_instance_id: str,
        production: bool = False,
    ) -> None:
        if production and model.production_kind != "remote_structured_model":
            raise ValueError("production MemoryGuardAgent requires a real remote model Adapter")
        if production and ledger.production_kind != "sibyl_agent_ledger":
            raise ValueError("production MemoryGuardAgent requires the Sibyl Agent run ledger")
        if production and actions.production_kind != "sibyl_safe_actions":
            raise ValueError("production MemoryGuardAgent requires Sibyl-backed safety actions")
        self._guard = guard
        self._model = model
        self._ledger = ledger
        self._actions = actions
        self._runtime_instance_id = runtime_instance_id
        self._production = production

    @property
    def backend_status(self) -> dict[str, Any]:
        return {
            "model": self._model.health(),
            "run_ledger": self._ledger.health(),
            "safe_actions": self._actions.health(),
        }

    @staticmethod
    def _request_hash(goal: GuardedPaymentGoal) -> str:
        intent = goal.intent
        return domain_hash(
            "agent-request",
            {
                "subject_ref": subject_ref(intent.subject_id),
                "session_id": intent.session_id,
                "chain_id": intent.chain_id,
                "target": intent.target.lower(),
                "method": intent.method,
                "amount_usd": intent.amount_usd,
                "evidence_mode": intent.evidence_mode.value,
                "idempotency_key": intent.idempotency_key,
            },
        )

    @staticmethod
    def _action_fingerprint(decision_or_goal: DecisionDraft | GuardedPaymentGoal) -> str:
        intent = (
            decision_or_goal.intent
            if isinstance(decision_or_goal, (DecisionDraft, GuardedPaymentGoal))
            else decision_or_goal
        )
        subject = (
            intent.subject_id
            if isinstance(decision_or_goal, DecisionDraft)
            else subject_ref(intent.subject_id)
        )
        return domain_hash(
            "agent-action",
            {
                "subject_ref": subject,
                "chain_id": intent.chain_id,
                "target": intent.target.lower(),
                "method": intent.method,
                "amount_usd": intent.amount_usd,
                "evidence_mode": intent.evidence_mode.value,
            },
        )

    @staticmethod
    def _run_id(goal: GuardedPaymentGoal) -> str:
        intent = goal.intent
        digest = domain_hash(
            "agent-run",
            {"subject_ref": subject_ref(intent.subject_id), "key": intent.idempotency_key},
        )
        return f"run_{digest[:20]}"

    @staticmethod
    def _stored_run_id(decision: DecisionDraft) -> str:
        digest = domain_hash(
            "agent-run",
            {
                "subject_ref": decision.subject_ref,
                "key": decision.intent.idempotency_key,
            },
        )
        return f"run_{digest[:20]}"

    @staticmethod
    def _stored_request_hash(decision: DecisionDraft) -> str:
        intent = decision.intent
        return domain_hash(
            "agent-request",
            {
                "subject_ref": decision.subject_ref,
                "session_id": intent.session_id,
                "chain_id": intent.chain_id,
                "target": intent.target.lower(),
                "method": intent.method,
                "amount_usd": intent.amount_usd,
                "evidence_mode": intent.evidence_mode.value,
                "idempotency_key": intent.idempotency_key,
            },
        )

    @staticmethod
    def _authorization(decision: DecisionDraft) -> tuple[AgentState, tuple[str, ...], str]:
        if decision.verdict == Verdict.READY:
            return AgentState.AWAIT_FINALIZE, (_REVIEW_TOOL, _BRIEF_TOOL), _REVIEW_TOOL
        if decision.verdict == Verdict.DENY:
            return (
                AgentState.BLOCK_AND_ESCALATE,
                (_ESCALATION_TOOL, _BRIEF_TOOL),
                _ESCALATION_TOOL,
            )
        return (
            AgentState.AWAIT_HUMAN_REVIEW,
            (_ESCALATION_TOOL, _BRIEF_TOOL),
            _ESCALATION_TOOL,
        )

    @staticmethod
    def _model_context(decision: DecisionDraft, state: AgentState) -> dict[str, Any]:
        # Raw observations, external text, source IDs, nonces and policy contents
        # never cross this seam.
        return {
            "state": state.value,
            "verdict": decision.verdict.value,
            "reason_codes": list(decision.reason_codes),
            "causal_memory_ids": list(decision.causal_memory_ids),
            "cross_session": decision.cross_session,
            "chain_id": decision.intent.chain_id,
            "target_hash": domain_hash("agent-model-target", decision.intent.target),
            "method": decision.intent.method,
            "amount_usd": decision.intent.amount_usd,
            "evidence_mode": decision.intent.evidence_mode.value,
        }

    @staticmethod
    def _fallback_plan(decision: DecisionDraft) -> ModelPlan:
        return ModelPlan(
            explanation=(
                "The external planning model was unavailable. MemoryGuard's verdict "
                "remains authoritative, "
                "and only the deterministic non-payment safety step was retained."
            ),
            operator_steps=("Review the authoritative reason codes and causal memory IDs.",),
            requested_tools=(),
        )

    @staticmethod
    def _operator_copy(
        decision: DecisionDraft,
        state: AgentState,
        planning_degraded: bool,
    ) -> tuple[str, tuple[str, ...]]:
        if state == AgentState.HALT_ACTION_UNAVAILABLE:
            explanation = (
                "The safe-action Adapter was unavailable, so the Agent stopped without "
                "claiming that a review or escalation artifact was created."
            )
            steps = ("Restore the Sibyl safety-action Adapter and start a new Agent run.",)
        elif state == AgentState.AWAIT_FINALIZE:
            explanation = (
                "MemoryGuard recalled a matching trusted baseline. The Agent prepared "
                "a non-executable review card and did not gain payment authority."
            )
            steps = ("Review the causal memory and proof before any external action.",)
        elif state == AgentState.BLOCK_AND_ESCALATE:
            explanation = (
                "MemoryGuard recalled a dispute or revocation. The Agent suppressed "
                "review preparation and created a non-executable escalation case."
            )
            steps = ("Investigate the causal memory IDs; do not perform the requested action.",)
        else:
            explanation = (
                "MemoryGuard did not grant an automated path. The Agent created a "
                "non-executable operator review case."
            )
            steps = ("Obtain new trusted evidence and start a new Agent run.",)
        if planning_degraded:
            explanation += " The external planning model was unavailable."
        del decision
        return explanation, steps

    def _call_action(self, tool: str, decision: DecisionDraft) -> dict[str, Any]:
        if tool == _REVIEW_TOOL:
            return self._actions.prepare_review(decision)
        if tool == _ESCALATION_TOOL:
            return self._actions.create_escalation(decision)
        if tool == _BRIEF_TOOL:
            return self._actions.prepare_evidence_brief(decision)
        raise ValueError("tool is not registered")

    def _validate_run(self, run: AgentRun) -> None:
        validate_decision(run.decision)
        if run.run_id != self._stored_run_id(
            run.decision
        ) or run.request_hash != self._stored_request_hash(run.decision):
            raise MemoryIntegrityError("Agent run identity does not match its request")
        if run.executable or run.action_fingerprint != self._action_fingerprint(run.decision):
            raise MemoryIntegrityError("Agent run action boundary is invalid")
        if [event.sequence for event in run.tool_trace] != list(range(1, len(run.tool_trace) + 1)):
            raise MemoryIntegrityError("Agent run tool trace sequence is invalid")
        if self._production and run.model_kind != "remote_structured_model":
            raise MemoryIntegrityError("production Agent run did not use the remote model")

        base_state, allowed_tools, mandatory_tool = self._authorization(run.decision)
        valid_states = {
            base_state,
            AgentState.HALT_ACTION_UNAVAILABLE,
            AgentState.DEGRADED_SAFE_ONLY,
            AgentState.BLOCK_AND_REDECIDE,
        }
        if base_state != AgentState.BLOCK_AND_ESCALATE:
            valid_states.add(AgentState.CANCELLED)
        if run.state not in valid_states:
            raise MemoryIntegrityError("Agent run state does not match its decision")
        if any(tool not in allowed_tools for tool in run.model_requested_safe_tools):
            raise MemoryIntegrityError("Agent run contains an unauthorized model tool")

        known_tools = {
            "memoryguard.decide",
            "model.plan",
            "model.receipt",
            "agent.cancel",
            "proof_anchor.prepare",
            "proof_anchor.verify",
            *_REGISTERED_TOOLS,
        }
        for event in run.tool_trace:
            hashes = [event.input_hash]
            if event.output_hash is not None:
                hashes.append(event.output_hash)
            if any(
                len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
                for value in hashes
            ):
                raise MemoryIntegrityError("Agent run trace hash is invalid")
            if event.tool not in known_tools and (
                event.phase != ToolPhase.SUPPRESSED or event.reason_code != "tool_not_registered"
            ):
                raise MemoryIntegrityError("Agent run trace contains an executable unknown tool")
            if event.tool in _REGISTERED_TOOLS and event.phase in {
                ToolPhase.CALLED,
                ToolPhase.SUCCEEDED,
            }:
                if event.tool not in allowed_tools:
                    raise MemoryIntegrityError("Agent run called a verdict-forbidden tool")
                if event.tool == _BRIEF_TOOL and event.tool not in run.model_requested_safe_tools:
                    raise MemoryIntegrityError("Agent run called an unrequested optional tool")
            if (
                event.tool in {"proof_anchor.prepare", "proof_anchor.verify"}
                and event.phase in {ToolPhase.CALLED, ToolPhase.SUCCEEDED, ToolPhase.FAILED}
                and event.tool not in run.artifacts
            ):
                raise MemoryIntegrityError("Agent run anchor trace has no artifact")

        if run.schema_version not in {"1.0", "1.1"}:
            raise MemoryIntegrityError("Agent run schema version is unsupported")
        receipt_events = [event for event in run.tool_trace if event.tool == "model.receipt"]
        if run.schema_version == "1.0":
            if run.model_receipt is not None or receipt_events:
                raise MemoryIntegrityError("legacy Agent run contains a model receipt")
        else:
            if run.planning_degraded and run.model_receipt is not None:
                raise MemoryIntegrityError("degraded Agent run contains a model receipt")
            if run.model_receipt is not None:
                receipt = run.model_receipt
                required_strings = (
                    "backend",
                    "configured_model",
                    "resolved_model",
                    "generation_id",
                    "completion_sha256",
                    "model_context_hash",
                    "completed_at",
                )
                if any(
                    not isinstance(receipt.get(key), str) or not receipt[key]
                    for key in required_strings
                ):
                    raise MemoryIntegrityError("Agent run model receipt is incomplete")
                completion_hash = str(receipt["completion_sha256"])
                if len(completion_hash) != 64 or any(
                    char not in "0123456789abcdef" for char in completion_hash
                ):
                    raise MemoryIntegrityError("Agent run model receipt hash is invalid")
                if (
                    receipt.get("backend") != run.model_kind
                    or receipt.get("live_call_verified") is not True
                    or receipt.get("structured_output_validated") is not True
                    or receipt.get("production_reliability_claimed") is not False
                ):
                    raise MemoryIntegrityError("Agent run model receipt boundary is invalid")
                expected_context_hash = domain_hash(
                    "agent-model-context",
                    {
                        "context": self._model_context(run.decision, base_state),
                        "allowed_tools": list(allowed_tools),
                    },
                )
                if receipt.get("model_context_hash") != expected_context_hash:
                    raise MemoryIntegrityError("Agent run model receipt context is invalid")
                expected_receipt_hash = domain_hash(
                    "agent-tool-output:model.receipt",
                    receipt,
                )
                expected_receipt_input_hash = domain_hash(
                    "agent-tool-input:model.receipt",
                    {"run_id": run.run_id, "model_context_hash": expected_context_hash},
                )
                successful_plan_events = [
                    event
                    for event in run.tool_trace
                    if event.tool == "model.plan" and event.phase == ToolPhase.SUCCEEDED
                ]
                if (
                    len(receipt_events) != 1
                    or len(successful_plan_events) != 1
                    or receipt_events[0].phase != ToolPhase.SUCCEEDED
                    or receipt_events[0].reason_code != "non_secret_provider_receipt"
                    or receipt_events[0].input_hash != expected_receipt_input_hash
                    or receipt_events[0].output_hash != expected_receipt_hash
                    or receipt_events[0].sequence != successful_plan_events[0].sequence + 1
                ):
                    raise MemoryIntegrityError("Agent run model receipt is not trace-bound")
            else:
                if receipt_events:
                    raise MemoryIntegrityError("Agent run has a receipt trace without a receipt")
                if self._production and not run.planning_degraded:
                    raise MemoryIntegrityError("production Agent run is missing its model receipt")

        allowed_artifacts = {*_REGISTERED_TOOLS, "proof_anchor.prepare", "proof_anchor.verify"}
        if any(name not in allowed_artifacts for name in run.artifacts):
            raise MemoryIntegrityError("Agent run contains an unknown artifact")
        if run.state != AgentState.HALT_ACTION_UNAVAILABLE and mandatory_tool not in run.artifacts:
            raise MemoryIntegrityError("Agent run is missing its mandatory safety artifact")
        if _BRIEF_TOOL in run.artifacts and _BRIEF_TOOL not in run.model_requested_safe_tools:
            raise MemoryIntegrityError("Agent run brief was not requested by the model")
        expected_action_ids = {
            _REVIEW_TOOL: f"act_{domain_hash('review-action', run.decision.decision_id)[:20]}",
            _ESCALATION_TOOL: (
                f"act_{domain_hash('escalation-action', run.decision.decision_id)[:20]}"
            ),
            _BRIEF_TOOL: (
                f"act_{domain_hash('evidence-brief-action', run.decision.decision_id)[:20]}"
            ),
        }
        for name, artifact in run.artifacts.items():
            if not isinstance(artifact, dict):
                raise MemoryIntegrityError("Agent run artifact is invalid")
            artifact_decision = artifact.get("decision_id")
            if artifact_decision and artifact_decision != run.decision.decision_id:
                raise MemoryIntegrityError("Agent run artifact references another decision")
            if artifact.get("executable") is not False:
                raise MemoryIntegrityError("Agent run artifact gained execution authority")
            if (
                name in expected_action_ids
                and artifact.get("action_id") != expected_action_ids[name]
            ):
                raise MemoryIntegrityError("Agent run safety action receipt is invalid")
            if name in _REGISTERED_TOOLS:
                expected_output = domain_hash(f"agent-tool-output:{name}", artifact)
                if not any(
                    event.tool == name
                    and event.phase == ToolPhase.SUCCEEDED
                    and event.output_hash == expected_output
                    for event in run.tool_trace
                ):
                    raise MemoryIntegrityError("Agent run safety action trace is invalid")

        proof_artifact = run.artifacts.get("proof_anchor.verify") or run.artifacts.get(
            "proof_anchor.prepare"
        )
        if proof_artifact:
            if proof_artifact.get("state") != run.anchor_state.value:
                raise MemoryIntegrityError("Agent run anchor state does not match its artifact")
            if proof_artifact.get("proof_root") != run.decision.proof_root:
                raise MemoryIntegrityError("Agent run anchor proof root is invalid")
            proof_tool = (
                "proof_anchor.verify"
                if "proof_anchor.verify" in run.artifacts
                else "proof_anchor.prepare"
            )
            expected_output = domain_hash(
                f"agent-tool-output:{proof_tool}",
                proof_artifact,
            )
            if not any(
                event.tool == proof_tool
                and event.phase in {ToolPhase.SUCCEEDED, ToolPhase.FAILED}
                and event.output_hash == expected_output
                for event in run.tool_trace
            ):
                raise MemoryIntegrityError("Agent run anchor trace is invalid")
        elif run.anchor_state != AnchorState.NOT_CONFIGURED:
            raise MemoryIntegrityError("Agent run anchor state has no artifact")

        copy_state = (
            AgentState.HALT_ACTION_UNAVAILABLE
            if run.state == AgentState.HALT_ACTION_UNAVAILABLE
            else base_state
        )
        expected_explanation, expected_steps = self._operator_copy(
            run.decision,
            copy_state,
            run.planning_degraded,
        )
        if run.explanation != expected_explanation or run.operator_steps != expected_steps:
            raise MemoryIntegrityError("Agent operator copy was modified")

    def run(self, goal: GuardedPaymentGoal) -> AgentRun:
        request_hash = self._request_hash(goal)
        run_id = self._run_id(goal)
        with self._ledger.claim(run_id):
            return self._run_claimed(goal, request_hash, run_id)

    def _run_claimed(
        self,
        goal: GuardedPaymentGoal,
        request_hash: str,
        run_id: str,
    ) -> AgentRun:
        existing = self._ledger.load(run_id)
        if existing is not None:
            self._validate_run(existing)
            if existing.request_hash != request_hash:
                raise MemoryConflictError(
                    "Agent idempotency key was reused for a different request"
                )
            return existing

        trace = _Trace()
        intent_payload = {"action_fingerprint": self._action_fingerprint(goal)}
        trace.add("memoryguard.decide", ToolPhase.CONSIDERED, "mandatory_authority", intent_payload)
        trace.add("memoryguard.decide", ToolPhase.CALLED, "mandatory_authority", intent_payload)
        decision = self._guard.decide(goal.intent)
        trace.add(
            "memoryguard.decide",
            ToolPhase.SUCCEEDED,
            f"verdict_{decision.verdict.value}",
            intent_payload,
            {"decision_id": decision.decision_id, "proof_root": decision.proof_root},
        )

        state, allowed_tools, mandatory_tool = self._authorization(decision)
        context = self._model_context(decision, state)
        trace.add("model.plan", ToolPhase.CONSIDERED, "bounded_planning", context)
        trace.add("model.plan", ToolPhase.CALLED, "bounded_planning", context)
        planning_degraded = False
        try:
            plan = self._model.plan(context=context, allowed_tools=allowed_tools)
            trace.add(
                "model.plan",
                ToolPhase.SUCCEEDED,
                "structured_plan_received",
                context,
                {
                    "requested_tools": list(plan.requested_tools),
                    "explanation_hash": domain_hash("model-explanation", plan.explanation),
                },
            )
            if plan.model_receipt is not None:
                receipt_context_hash = str(plan.model_receipt.get("model_context_hash", ""))
                trace.add(
                    "model.receipt",
                    ToolPhase.SUCCEEDED,
                    "non_secret_provider_receipt",
                    {
                        "run_id": run_id,
                        "model_context_hash": receipt_context_hash,
                    },
                    plan.model_receipt,
                )
        except Exception as exc:  # noqa: BLE001
            planning_degraded = True
            plan = self._fallback_plan(decision)
            trace.add(
                "model.plan",
                ToolPhase.FAILED,
                f"planning_failed_{type(exc).__name__}",
                context,
            )

        artifacts: dict[str, Any] = {}
        action_failed = False
        requested = set(plan.requested_tools)
        for unknown in sorted(requested.difference(_REGISTERED_TOOLS)):
            trace.add(
                unknown,
                ToolPhase.SUPPRESSED,
                "tool_not_registered",
                {"decision_id": decision.decision_id},
            )

        for tool in _REGISTERED_TOOLS:
            tool_input = {"decision_id": decision.decision_id, "verdict": decision.verdict.value}
            trace.add(tool, ToolPhase.CONSIDERED, "closed_tool_registry", tool_input)
            if tool not in allowed_tools:
                trace.add(
                    tool,
                    ToolPhase.SUPPRESSED,
                    f"verdict_{decision.verdict.value}",
                    tool_input,
                )
                continue
            if tool != mandatory_tool and tool not in requested:
                trace.add(tool, ToolPhase.SUPPRESSED, "not_requested_by_model", tool_input)
                continue
            call_reason = (
                "mandatory_safety_action"
                if tool == mandatory_tool
                else "requested_by_model_and_authorized"
            )
            trace.add(tool, ToolPhase.CALLED, call_reason, tool_input)
            try:
                artifact = self._call_action(tool, decision)
                artifacts[tool] = artifact
                trace.add(
                    tool,
                    ToolPhase.SUCCEEDED,
                    "persisted_by_safe_action_adapter",
                    tool_input,
                    artifact,
                )
            except Exception as exc:  # noqa: BLE001
                action_failed = True
                trace.add(
                    tool,
                    ToolPhase.FAILED,
                    f"safe_action_failed_{type(exc).__name__}",
                    tool_input,
                )

        now = utc_now()
        final_state = (
            AgentState.HALT_ACTION_UNAVAILABLE
            if action_failed
            else AgentState.DEGRADED_SAFE_ONLY
            if planning_degraded
            else state
        )
        explanation, operator_steps = self._operator_copy(
            decision,
            AgentState.HALT_ACTION_UNAVAILABLE if action_failed else state,
            planning_degraded,
        )
        run = AgentRun(
            run_id=run_id,
            request_hash=request_hash,
            runtime_instance_id=self._runtime_instance_id,
            state=final_state,
            decision=decision,
            action_fingerprint=intent_payload["action_fingerprint"],
            explanation=explanation,
            operator_steps=operator_steps,
            planning_degraded=planning_degraded,
            model_kind=self._model.production_kind,
            model_receipt=plan.model_receipt,
            model_requested_safe_tools=tuple(
                tool for tool in plan.requested_tools if tool in allowed_tools
            ),
            tool_trace=tuple(trace.events),
            artifacts=artifacts,
            anchor_state=AnchorState.NOT_CONFIGURED,
            executable=False,
            created_at=now,
            updated_at=now,
        )
        self._validate_run(run)
        self._ledger.save(run)
        return run

    def inspect(self, run_id: str) -> AgentRun:
        run = self._ledger.load(run_id)
        if run is None:
            raise DecisionNotFoundError("Agent run was not found")
        self._validate_run(run)
        return run

    def resume(self, run_id: str, signal: AgentHumanSignal) -> AgentRun:
        with self._ledger.claim(run_id):
            return self._resume_claimed(run_id, signal)

    def _resume_claimed(self, run_id: str, signal: AgentHumanSignal) -> AgentRun:
        run = self.inspect(run_id)
        if signal.kind == "cancel":
            if run.state in {
                AgentState.BLOCK_AND_ESCALATE,
                AgentState.HALT_ACTION_UNAVAILABLE,
                AgentState.DEGRADED_SAFE_ONLY,
                AgentState.BLOCK_AND_REDECIDE,
                AgentState.CANCELLED,
            }:
                return run
            trace = _Trace()
            trace.events.extend(run.tool_trace)
            payload = {"run_id": run.run_id}
            trace.add("agent.cancel", ToolPhase.CONSIDERED, "human_cancel_signal", payload)
            trace.add("agent.cancel", ToolPhase.CALLED, "human_cancel_signal", payload)
            trace.add("agent.cancel", ToolPhase.SUCCEEDED, "run_cancelled", payload, payload)
            updated = replace(
                run,
                state=AgentState.CANCELLED,
                tool_trace=tuple(trace.events),
                updated_at=utc_now(),
            )
            self._ledger.save(updated)
            return updated

        if run.state in {
            AgentState.CANCELLED,
            AgentState.HALT_ACTION_UNAVAILABLE,
            AgentState.DEGRADED_SAFE_ONLY,
            AgentState.BLOCK_AND_REDECIDE,
        }:
            raise ValueError("this Agent run cannot continue")

        if signal.kind == "prepare_anchor":
            trace = _Trace()
            trace.events.extend(run.tool_trace)
            payload = {"decision_id": run.decision.decision_id}
            trace.add("proof_anchor.prepare", ToolPhase.CONSIDERED, "human_request", payload)
            trace.add("proof_anchor.prepare", ToolPhase.CALLED, "human_request", payload)
            result = self._guard.finalize(run.decision.decision_id)
            phase = ToolPhase.FAILED if result.state == AnchorState.FAILED else ToolPhase.SUCCEEDED
            trace.add(
                "proof_anchor.prepare",
                phase,
                f"anchor_{result.state.value}",
                payload,
                result.to_dict(),
            )
            updated = replace(
                run,
                tool_trace=tuple(trace.events),
                anchor_state=result.state,
                artifacts={**run.artifacts, "proof_anchor.prepare": result.to_dict()},
                updated_at=utc_now(),
                executable=False,
            )
            self._ledger.save(updated)
            return updated

        if signal.kind != "anchor_transaction_observed" or not signal.confirmation_tx_hash:
            raise ValueError(
                "resume accepts only cancel, prepare_anchor, or anchor_transaction_observed"
            )
        if run.anchor_state == AnchorState.VERIFIED:
            verified = run.artifacts.get("proof_anchor.verify", {})
            verification = verified.get("anchor_verification") or {}
            if verification.get("tx_hash") == signal.confirmation_tx_hash:
                return run
            raise ValueError("Agent run is already anchored by a different transaction")

        trace = _Trace()
        trace.events.extend(run.tool_trace)
        payload = {"decision_id": run.decision.decision_id, "tx_hash": signal.confirmation_tx_hash}
        trace.add("proof_anchor.verify", ToolPhase.CONSIDERED, "human_wallet_signal", payload)
        trace.add("proof_anchor.verify", ToolPhase.CALLED, "human_wallet_signal", payload)
        try:
            result = self._guard.finalize(
                run.decision.decision_id,
                signal.confirmation_tx_hash,
            )
        except FinalizationError as exc:
            failure = {
                "decision_id": run.decision.decision_id,
                "state": "failed",
                "proof_root": run.decision.proof_root,
                "reason_codes": ["decision_requires_fresh_recall"],
                "executable": False,
            }
            trace.add(
                "proof_anchor.verify",
                ToolPhase.FAILED,
                f"decision_requires_recall_{type(exc).__name__}",
                payload,
                failure,
            )
            updated = replace(
                run,
                state=AgentState.BLOCK_AND_REDECIDE,
                tool_trace=tuple(trace.events),
                anchor_state=AnchorState.FAILED,
                artifacts={
                    **run.artifacts,
                    "proof_anchor.verify": failure,
                },
                updated_at=utc_now(),
                executable=False,
            )
            self._ledger.save(updated)
            return updated
        phase = (
            ToolPhase.SUCCEEDED
            if result.state in {AnchorState.PENDING, AnchorState.VERIFIED}
            else ToolPhase.FAILED
        )
        trace.add(
            "proof_anchor.verify",
            phase,
            f"anchor_{result.state.value}",
            payload,
            result.to_dict(),
        )
        updated = replace(
            run,
            tool_trace=tuple(trace.events),
            anchor_state=result.state,
            artifacts={**run.artifacts, "proof_anchor.verify": result.to_dict()},
            updated_at=utc_now(),
            executable=False,
        )
        self._ledger.save(updated)
        return updated
