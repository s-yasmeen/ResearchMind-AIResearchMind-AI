"""Canonical 26-task workflow registry and dependency validation.

Task names are intentionally explicit about expected research deliverables.
A task is executable only when its dependencies are completed and an agent
implementation is registered by the project engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    phase: int
    title: str
    dependencies: tuple[str, ...] = ()


_TITLES = {
    "P1-T1": "Evidence-grounded literature review",
    "P1-T2": "Initial methodology proposal",
    "P1-T3": "Research writing draft",
    "P1-T4": "Research question and hypothesis specification",
    "P1-T5": "Research plan and acceptance criteria",
    "P2-T1": "Research gap and novelty assessment",
    "P2-T2": "Method and algorithm design",
    "P2-T3": "Dataset discovery and suitability assessment",
    "P2-T4": "Experimental protocol and baseline design",
    "P2-T5": "Risk, ethics, and reproducibility review",
    "P3-T1": "Dataset acquisition and provenance capture",
    "P3-T2": "Dataset validation and preprocessing",
    "P3-T3": "Leakage-safe split and benchmark setup",
    "P3-T4": "Experiment execution and run tracking",
    "P3-T5": "Baseline comparison and robustness evaluation",
    "P4-T1": "Quantitative and statistical analysis",
    "P4-T2": "Ablation and sensitivity analysis",
    "P4-T3": "Error analysis and limitations",
    "P4-T4": "Independent result and evidence review",
    "P4-T5": "Reproducibility and claim verification",
    "P5-T1": "Manuscript structure and outline",
    "P5-T2": "Methods and results drafting",
    "P5-T3": "Related work and discussion drafting",
    "P5-T4": "Citation and reference validation",
    "P5-T5": "Independent manuscript review and revision",
    "P5-T6": "Final research package and audit report",
}


def _build_registry() -> tuple[TaskDefinition, ...]:
    definitions = []
    previous = None
    for phase in range(1, 6):
        count = 6 if phase == 5 else 5
        for number in range(1, count + 1):
            task_id = f"P{phase}-T{number}"
            dependencies = (previous,) if previous else ()
            definitions.append(TaskDefinition(
                task_id=task_id,
                phase=phase,
                title=_TITLES[task_id],
                dependencies=dependencies,
            ))
            previous = task_id
    return tuple(definitions)


TASK_REGISTRY = _build_registry()
TASKS_BY_ID = {task.task_id: task for task in TASK_REGISTRY}
TASK_IDS = tuple(task.task_id for task in TASK_REGISTRY)


def validate_registry(tasks: Iterable[TaskDefinition] = TASK_REGISTRY) -> None:
    items = tuple(tasks)
    by_id = {task.task_id: task for task in items}
    if len(by_id) != len(items):
        raise ValueError("Task registry contains duplicate task IDs.")
    for task in items:
        for dependency in task.dependencies:
            if dependency not in by_id:
                raise ValueError(f"{task.task_id} has unknown dependency {dependency}.")
            if dependency == task.task_id:
                raise ValueError(f"{task.task_id} cannot depend on itself.")
            if by_id[dependency].task_id >= task.task_id:
                raise ValueError("Dependencies must precede their dependent task.")
    # The strict predecessor rule above also makes cycles impossible.


def dependencies_satisfied(task_id: str, completed_ids: Iterable[str]) -> bool:
    task = TASKS_BY_ID[task_id]
    completed = set(completed_ids)
    return all(dependency in completed for dependency in task.dependencies)


validate_registry()
