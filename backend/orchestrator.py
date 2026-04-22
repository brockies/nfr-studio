"""Lightweight workflow orchestration primitives for backend agent pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from agents.nfr_agent import AgentRunResult

from .models import RunPayload, UsageStat


ProgressCallback = Callable[[RunPayload], None]
RecordUsageCallback = Callable[[dict[str, UsageStat], str, str, AgentRunResult], None]


@dataclass(frozen=True)
class PipelineExecutionContext:
    """Shared state passed to each workflow step during execution."""

    run: RunPayload
    combined_system_description: str
    analysis_system_description: str
    rag_context: str = ""


StepRunner = Callable[[PipelineExecutionContext], AgentRunResult]


@dataclass(frozen=True)
class WorkflowStep:
    """One deterministic workflow step backed by an agent function."""

    key: str
    label: str
    runner: StepRunner


def build_agent_states(steps: Sequence[WorkflowStep]) -> dict[str, str]:
    """Return the initial waiting-state map for a workflow definition."""

    return {step.key: "waiting" for step in steps}


def run_workflow(
    context: PipelineExecutionContext,
    steps: Sequence[WorkflowStep],
    *,
    emit_progress: ProgressCallback | None,
    record_usage: RecordUsageCallback,
) -> RunPayload:
    """Execute a deterministic workflow and update the shared run state."""

    run = context.run
    run.agent_states = build_agent_states(steps)
    if emit_progress is not None:
        emit_progress(run.model_copy(deep=True))

    for step in steps:
        run.agent_states[step.key] = "running"
        if emit_progress is not None:
            emit_progress(run.model_copy(deep=True))

        result = step.runner(context)
        run.results[step.key] = result.content
        record_usage(run.usage_stats, step.key, step.label, result)

        run.agent_states[step.key] = "done"
        if emit_progress is not None:
            emit_progress(run.model_copy(deep=True))

    return run
