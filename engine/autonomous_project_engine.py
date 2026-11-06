"""Resumable orchestration for the ResearchMind CLI.

This implementation deliberately exposes only capabilities backed by existing
agents. The remaining legacy task IDs are retained as not_implemented rather
than being reported as successful work.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.task_memory import TaskMemory


EXPECTED_TASK_IDS = (
    [f"P1-T{i}" for i in range(1, 6)]
    + [f"P2-T{i}" for i in range(1, 6)]
    + [f"P3-T{i}" for i in range(1, 6)]
    + [f"P4-T{i}" for i in range(1, 6)]
    + [f"P5-T{i}" for i in range(1, 7)]
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutonomousProjectEngine:
    """Execute available research agents and preserve honest task states."""

    IMPLEMENTED_TASKS = {
        "P1-T1": ("Evidence-grounded literature review", "literature"),
        "P1-T2": ("Initial methodology proposal", "methodology"),
        "P1-T3": ("Research writing draft", "writing"),
    }

    def __init__(self, memory: TaskMemory | None = None) -> None:
        self.memory = memory or TaskMemory()

    def _agent_output(self, agent_name: str, query: str) -> str:
        # Lazy imports keep engine construction independent of optional LLM
        # provider initialization and make orchestration tests straightforward.
        if agent_name == "literature":
            from agents.literature_agent import LiteratureAgent
            return LiteratureAgent().run(query)
        if agent_name == "methodology":
            from agents.methodology_agent import MethodologyAgent
            return MethodologyAgent().run(query)
        if agent_name == "writing":
            from agents.writing_agent import WritingAgent
            return WritingAgent().run(query)
        raise ValueError(f"Unsupported agent: {agent_name}")

    def run(
        self,
        query: str,
        max_tasks: int | None = None,
        resume: bool = True,
    ) -> dict[str, Any]:
        query = str(query).strip()
        if not query:
            raise ValueError("Research query cannot be empty.")
        if max_tasks is not None and max_tasks <= 0:
            raise ValueError("max_tasks must be greater than zero.")

        checkpoint = self.memory.load(query) if resume else None
        if checkpoint is None:
            self.memory.initialize(query)
        existing = {
            str(item.get("task_id")): dict(item)
            for item in self.memory.get_results()
            if item.get("task_id")
        }

        records: list[dict[str, Any]] = []
        for task_id in EXPECTED_TASK_IDS:
            title, agent = self.IMPLEMENTED_TASKS.get(
                task_id, (f"Legacy workflow task {task_id}", None)
            )
            prior = existing.get(task_id)
            if prior and prior.get("status") == "completed":
                records.append(prior)
            else:
                records.append({
                    "task_id": task_id,
                    "title": title,
                    "status": "pending" if agent else "not_implemented",
                    "reason": (
                        "Awaiting execution."
                        if agent else
                        "No corresponding implementation or task specification exists in the repository."
                    ),
                    "updated_at": _now(),
                })

        attempted = 0
        executed: list[dict[str, Any]] = []
        for index, task_id in enumerate(EXPECTED_TASK_IDS):
            title, agent = self.IMPLEMENTED_TASKS.get(
                task_id, (f"Legacy workflow task {task_id}", None)
            )
            record = records[index]
            if record.get("status") == "completed" or agent is None:
                continue
            if max_tasks is not None and attempted >= max_tasks:
                break

            attempted += 1
            running = {
                "task_id": task_id,
                "title": title,
                "status": "running",
                "started_at": _now(),
            }
            records[index] = running
            self.memory.save(results=records, query=query)
            try:
                output = self._agent_output(agent, query)
                if not isinstance(output, str) or not output.strip():
                    raise RuntimeError("Agent returned empty output.")
                completed = {
                    "task_id": task_id,
                    "title": title,
                    "status": "completed",
                    "output": output,
                    "completed_at": _now(),
                    "agent": agent,
                }
                records[index] = completed
                executed.append(completed)
                self.memory.save(results=records, query=query)
            except Exception as exc:
                failed = {
                    "task_id": task_id,
                    "title": title,
                    "status": "pending" if getattr(exc, "retryable", False)
                               or "quota" in str(exc).lower()
                               or "429" in str(exc)
                               else "failed",
                    "error": str(exc),
                    "updated_at": _now(),
                }
                records[index] = failed
                self.memory.save(results=records, query=query)
                if failed["status"] == "pending":
                    break

        self.memory.save(results=records, query=query)
        completed_count = sum(r.get("status") == "completed" for r in records)
        failed_count = sum(r.get("status") == "failed" for r in records)
        pending_count = sum(r.get("status") in {"pending", "running"} for r in records)
        unimplemented_count = sum(r.get("status") == "not_implemented" for r in records)
        if pending_count:
            status, stopped_reason = "paused", "task_limit_or_retryable_error"
        elif failed_count:
            status, stopped_reason = "partial", "task_failure"
        elif unimplemented_count:
            status, stopped_reason = "partial", "unimplemented_legacy_tasks"
        else:
            status, stopped_reason = "completed", None

        return {
            "status": status,
            "stopped_reason": stopped_reason,
            "executed_tasks": records,
            "newly_executed_tasks": executed,
            "counts": {
                "total": len(records),
                "completed": completed_count,
                "failed": failed_count,
                "pending": pending_count,
                "not_implemented": unimplemented_count,
            },
        }
