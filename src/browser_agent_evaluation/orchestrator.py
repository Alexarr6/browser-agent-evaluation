from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from browser_agent_evaluation.assertions import PageState, evaluate_acceptance
from browser_agent_evaluation.connectors.base import (
    BrowserConnector,
    CleanupResult,
    ConnectorSession,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.models import AcceptanceSpec, UsageEvidence, now_utc
from browser_agent_evaluation.step_evidence import Provenance, RunReceipt, StepReceipt
from browser_agent_evaluation.workflow import WorkflowSpec


@dataclass(frozen=True)
class WorkflowRunResult:
    receipt: RunReceipt


class WorkflowOrchestrator:
    """Advance one workflow through a single connector-owned persistent session."""

    def __init__(self, *, configuration_sha256: str) -> None:
        self._configuration_sha256 = configuration_sha256

    async def run(
        self, *, run_id: str, workflow: WorkflowSpec, connector: BrowserConnector
    ) -> WorkflowRunResult:
        provenance = Provenance(
            connector_id=connector.id,
            model_id=connector.model_id,
            configuration_sha256=self._configuration_sha256,
        )
        capability = await connector.preflight()
        if not capability.supported:
            return WorkflowRunResult(
                receipt=RunReceipt(
                    run_id=run_id,
                    workflow_id=workflow.id,
                    provenance=provenance,
                    outcome="unsupported",
                    cleanup_verified=True,
                    cleanup_detail=capability.reason,
                )
            )

        session: ConnectorSession | None = None
        receipts: list[StepReceipt] = []
        final_acceptance: dict[str, bool] = {}
        outcome = "failed"
        cleanup = CleanupResult(verified=False, detail="session did not open")
        try:
            session = await connector.open_session(
                SessionRequest(
                    workflow_id=workflow.id,
                    start_url=workflow.start_url,
                    policy=workflow.policy,
                )
            )
            for step in workflow.steps:
                started = now_utc()
                try:
                    result = await session.execute_step(workflow.connector_step_request(step))
                    state = await session.observe()
                except Exception as error:
                    receipts.append(
                        self._failed_receipt(
                            run_id=run_id,
                            workflow_id=workflow.id,
                            step_id=step.id,
                            started=started,
                            ended=now_utc(),
                            provenance=provenance,
                            diagnostic=str(error),
                        )
                    )
                    break
                acceptance = self._evaluate(step.acceptance, state)
                step_outcome = "passed" if all(acceptance.values()) else "failed"
                receipts.append(
                    StepReceipt(
                        run_id=run_id,
                        workflow_id=workflow.id,
                        step_id=step.id,
                        started_at=started,
                        ended_at=now_utc(),
                        provenance=provenance,
                        action_summary=result.action_summary,
                        usage=result.usage,
                        acceptance=acceptance,
                        outcome=step_outcome,
                        diagnostic=result.diagnostic,
                    )
                )
                if step_outcome == "failed":
                    break
            else:
                final_state = await session.observe()
                final_acceptance = self._evaluate(workflow.final_acceptance, final_state)
                outcome = "passed" if all(final_acceptance.values()) else "failed"
        finally:
            if session is not None:
                cleanup = await session.close()

        if not cleanup.verified:
            outcome = "invalidated"
        return WorkflowRunResult(
            receipt=RunReceipt(
                run_id=run_id,
                workflow_id=workflow.id,
                provenance=provenance,
                step_receipts=receipts,
                final_acceptance=final_acceptance,
                outcome=outcome,
                cleanup_verified=cleanup.verified,
                cleanup_detail=cleanup.detail,
            )
        )

    @staticmethod
    def _evaluate(acceptance: AcceptanceSpec, state: ObservedPageState) -> dict[str, bool]:
        return evaluate_acceptance(
            acceptance,
            PageState(
                url=state.url,
                title=state.title,
                visible_text=state.visible_text,
                input_values=state.input_values,
            ),
        )

    @staticmethod
    def _failed_receipt(
        *,
        run_id: str,
        workflow_id: str,
        step_id: str,
        started: datetime,
        ended: datetime,
        provenance: Provenance,
        diagnostic: str,
    ) -> StepReceipt:
        return StepReceipt(
            run_id=run_id,
            workflow_id=workflow_id,
            step_id=step_id,
            started_at=started,
            ended_at=ended,
            provenance=provenance,
            usage=UsageEvidence(
                prompt_tokens=None,
                completion_tokens=None,
                request_count=0,
                cost_usd=None,
                unavailable_reason="connector step failed before provider usage was available",
            ),
            acceptance={},
            outcome="failed",
            diagnostic=diagnostic[:2_000],
        )
