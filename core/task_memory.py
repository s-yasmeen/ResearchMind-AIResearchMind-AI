from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =========================================================
# PATHS
# =========================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

MEMORY_DIR = ROOT_DIR / "researchmind_memory"

MEMORY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# CONSTANTS
# =========================================================

MEMORY_VERSION = "ResearchMind-Memory-V8.7"


# =========================================================
# TIME
# =========================================================

def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# SAFE FILE NAME
# =========================================================

def safe_name(
    value: str,
) -> str:

    value = str(value).strip().lower()

    value = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        value,
    )

    value = value.strip("_")

    return value[:120] or "research_project"


# =========================================================
# JSON SAFE
# =========================================================

def json_safe(
    value: Any,
) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        Path,
    ):
        return str(value)

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            json_safe(item)
            for item in value
        ]

    if hasattr(
        value,
        "__dict__",
    ):
        try:
            return json_safe(
                vars(value)
            )
        except Exception:
            pass

    return str(value)


# =========================================================
# TASK MEMORY
# =========================================================

class TaskMemory:

    VERSION = MEMORY_VERSION

    def __init__(
        self,
        root: Path | None = None,
    ):

        self.root = (
            Path(root)
            if root is not None
            else MEMORY_DIR
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.query: str | None = None

        self.project: dict[str, Any] = {}

        self.results: list[
            dict[str, Any]
        ] = []

        # -------------------------------------------------
        # INTERRUPTION STATE
        # -------------------------------------------------

        self.interrupted = False

        self.interruption_reason = None

        self.interruption_task_id = None

        self.interruption_at = None

        # -------------------------------------------------
        # QUOTA STATE
        # -------------------------------------------------

        self.quota_blocked = False

        self.quota_error = None

        self.quota_reset_time = None

    # =====================================================
    # PATHS
    # =====================================================

    def project_dir(
        self,
        query: str,
    ) -> Path:

        directory = (
            self.root
            / safe_name(query)
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    def checkpoint_path(
        self,
        query: str,
    ) -> Path:

        return (
            self.project_dir(query)
            / "checkpoint.json"
        )

    # =====================================================
    # INITIALIZE
    # =====================================================

    def initialize(
        self,
        query: str,
        project: dict[str, Any] | None = None,
    ) -> None:

        self.query = str(
            query
        ).strip()

        self.project = (
            dict(project)
            if isinstance(
                project,
                dict,
            )
            else {}
        )

        self.results = []

        self.clear_state(
            save=False
        )

    # =====================================================
    # LOAD CHECKPOINT
    # =====================================================

    def load(
        self,
        query: str,
    ) -> dict[str, Any] | None:

        query = str(
            query
        ).strip()

        path = self.checkpoint_path(
            query
        )

        if not path.exists():

            return None

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception as exc:

            print(
                f"Checkpoint load failed: {exc}"
            )

            return None

        checkpoint_query = str(
            data.get(
                "query",
                "",
            )
        ).strip()

        # -------------------------------------------------
        # NEVER MIX PROJECTS
        # -------------------------------------------------

        if checkpoint_query != query:

            print(
                "\nCheckpoint belongs to "
                "another research topic."
            )

            return None

        self.query = query

        project = data.get(
            "project",
            {},
        )

        self.project = (
            dict(project)
            if isinstance(
                project,
                dict,
            )
            else {}
        )

        results = data.get(
            "executed_tasks",
            [],
        )

        if isinstance(
            results,
            list,
        ):

            self.results = [
                dict(item)
                for item in results
                if isinstance(
                    item,
                    dict,
                )
            ]

        else:

            self.results = []

        # -------------------------------------------------
        # INTERRUPTION STATE
        # -------------------------------------------------

        self.interrupted = bool(
            data.get(
                "interrupted",
                False,
            )
        )

        self.interruption_reason = (
            data.get(
                "interruption_reason"
            )
        )

        self.interruption_task_id = (
            data.get(
                "interruption_task_id"
            )
        )

        self.interruption_at = (
            data.get(
                "interruption_at"
            )
        )

        # -------------------------------------------------
        # QUOTA STATE
        # -------------------------------------------------

        self.quota_blocked = bool(
            data.get(
                "quota_blocked",
                False,
            )
        )

        quota = data.get(
            "quota",
            {},
        )

        if not isinstance(
            quota,
            dict,
        ):
            quota = {}

        self.quota_error = (
            quota.get(
                "error"
            )
            or data.get(
                "quota_error"
            )
        )

        self.quota_reset_time = (
            quota.get(
                "reset_time"
            )
            or data.get(
                "quota_reset_time"
            )
        )

        # -------------------------------------------------
        # NORMALIZE DUPLICATES
        # -------------------------------------------------

        self._deduplicate_results()

        completed = len(
            self.get_completed_ids()
        )

        print(
            f"\nCheckpoint found: "
            f"{completed} tasks completed"
        )

        if self.quota_blocked:

            print(
                "Previous run stopped because "
                "the LLM quota/rate limit was exhausted."
            )

            if self.quota_reset_time:

                print(
                    "Provider reset: "
                    f"{self.quota_reset_time}"
                )

        elif self.interrupted:

            print(
                "Previous run was interrupted."
            )

            if self.interruption_reason:

                print(
                    "Reason: "
                    f"{self.interruption_reason}"
                )

            if self.interruption_task_id:

                print(
                    "Resume task: "
                    f"{self.interruption_task_id}"
                )

        return data

    # =====================================================
    # DEDUPLICATE TASK RESULTS
    # =====================================================

    def _deduplicate_results(
        self,
    ) -> None:

        latest: dict[
            str,
            dict[str, Any],
        ] = {}

        order: list[str] = []

        for item in self.results:

            task_id = item.get(
                "task_id"
            )

            if not task_id:

                continue

            task_id = str(
                task_id
            )

            if task_id not in latest:

                order.append(
                    task_id
                )

            latest[
                task_id
            ] = dict(item)

        self.results = [
            latest[task_id]
            for task_id in order
            if task_id in latest
        ]

    # =====================================================
    # SAVE CHECKPOINT
    # =====================================================

    def save(
        self,
        result: dict[str, Any] | None = None,
        *,
        query: str | None = None,
        project: dict[str, Any] | None = None,
        results: list[dict[str, Any]] | None = None,
    ) -> Path:

        if query is not None:

            self.query = str(
                query
            ).strip()

        if project is not None:

            self.project = dict(
                project
            )

        if results is not None:

            self.results = [
                dict(item)
                for item in results
                if isinstance(
                    item,
                    dict,
                )
            ]

        # -------------------------------------------------
        # ADD / REPLACE SINGLE TASK
        # -------------------------------------------------

        if result is not None:

            result = dict(
                result
            )

            task_id = result.get(
                "task_id"
            )

            if task_id:

                task_id = str(
                    task_id
                )

                self.results = [
                    item
                    for item in self.results
                    if str(
                        item.get(
                            "task_id",
                            "",
                        )
                    )
                    != task_id
                ]

            self.results.append(
                result
            )

        # -------------------------------------------------
        # VALIDATE QUERY
        # -------------------------------------------------

        if not self.query:

            raise RuntimeError(
                "TaskMemory.save() requires a query."
            )

        self._deduplicate_results()

        payload = {
            "version": self.VERSION,

            "query": self.query,

            "updated_at": utc_now(),

            "project": json_safe(
                self.project
            ),

            "executed_tasks": json_safe(
                self.results
            ),

            # -------------------------------------------------
            # INTERRUPTION
            # -------------------------------------------------

            "interrupted":
                self.interrupted,

            "interruption_reason":
                self.interruption_reason,

            "interruption_task_id":
                self.interruption_task_id,

            "interruption_at":
                self.interruption_at,

            # -------------------------------------------------
            # QUOTA
            # -------------------------------------------------

            "quota_blocked":
                self.quota_blocked,

            "quota_error":
                self.quota_error,

            "quota_reset_time":
                self.quota_reset_time,

            "quota": {
                "blocked":
                    self.quota_blocked,

                "error":
                    self.quota_error,

                "reset_time":
                    self.quota_reset_time,
            },
        }

        path = self.checkpoint_path(
            self.query
        )

        temporary = path.with_suffix(
            ".tmp"
        )

        # -------------------------------------------------
        # ATOMIC WRITE
        # -------------------------------------------------

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temporary.replace(
            path
        )

        return path

    # =====================================================
    # SAVE COMPLETED RESULT
    # =====================================================

    def save_result(
        self,
        result: dict[str, Any],
    ) -> Path:

        task_id = result.get(
            "task_id"
        )

        if task_id:

            # Remove stale version first.
            self.results = [
                item
                for item in self.results
                if item.get(
                    "task_id"
                )
                != task_id
            ]

        self.results.append(
            dict(result)
        )

        # A successful result clears interruption
        # and quota state.

        self.clear_state(
            save=False
        )

        return self.save()

    # =====================================================
    # MARK TASK PENDING
    # =====================================================

    def mark_pending(
        self,
        task_id: str,
        reason: str | None = None,
    ) -> Path:

        task_id = str(
            task_id
        )

        existing = self.get_result(
            task_id
        )

        # Never overwrite a completed task.
        if (
            existing
            and existing.get(
                "status"
            )
            == "completed"
        ):

            return self.save()

        self.results = [
            item
            for item in self.results
            if item.get(
                "task_id"
            )
            != task_id
        ]

        self.results.append(
            {
                "task_id": task_id,
                "status": "pending",
                "reason": (
                    reason
                    or "Task pending"
                ),
                "updated_at": utc_now(),
            }
        )

        return self.save()

    # =====================================================
    # MARK QUOTA EXHAUSTED
    # =====================================================

    def mark_quota_exhausted(
        self,
        task_id: str | None = None,
        reason: str | None = None,
        reset_time: str | None = None,
    ) -> Path:

        self.interrupted = True

        self.interruption_reason = (
            reason
            or (
                "OpenRouter daily free-model "
                "quota exhausted."
            )
        )

        self.interruption_task_id = (
            str(task_id)
            if task_id
            else None
        )

        self.interruption_at = utc_now()

        self.quota_blocked = True

        self.quota_error = (
            reason
            or (
                "OpenRouter daily free-model "
                "quota exhausted."
            )
        )

        self.quota_reset_time = (
            reset_time
        )

        # -------------------------------------------------
        # IMPORTANT:
        #
        # The quota-blocked task must NEVER be recorded
        # as permanently failed.
        # -------------------------------------------------

        if task_id:

            task_id = str(
                task_id
            )

            existing = self.get_result(
                task_id
            )

            if not (
                existing
                and existing.get(
                    "status"
                )
                == "completed"
            ):

                self.results = [
                    item
                    for item in self.results
                    if item.get(
                        "task_id"
                    )
                    != task_id
                ]

                self.results.append(
                    {
                        "task_id": task_id,
                        "status": "pending",
                        "quota_blocked": True,
                        "reason": (
                            "Waiting for "
                            "LLM quota reset"
                        ),
                        "updated_at":
                            utc_now(),
                    }
                )

        return self.save()

    # =====================================================
    # MARK TEMPORARY INTERRUPTION
    # =====================================================

    def mark_interrupted(
        self,
        task_id: str | None = None,
        reason: str | None = None,
    ) -> Path:

        self.interrupted = True

        self.interruption_reason = (
            reason
            or "Research execution interrupted."
        )

        self.interruption_task_id = (
            str(task_id)
            if task_id
            else None
        )

        self.interruption_at = utc_now()

        if task_id:

            task_id = str(
                task_id
            )

            existing = self.get_result(
                task_id
            )

            if not (
                existing
                and existing.get(
                    "status"
                )
                == "completed"
            ):

                self.results = [
                    item
                    for item in self.results
                    if item.get(
                        "task_id"
                    )
                    != task_id
                ]

                self.results.append(
                    {
                        "task_id": task_id,
                        "status": "pending",
                        "reason": (
                            "Interrupted; "
                            "safe to resume"
                        ),
                        "updated_at":
                            utc_now(),
                    }
                )

        return self.save()

    # =====================================================
    # CLEAR STATE
    # =====================================================

    def clear_state(
        self,
        *,
        save: bool = True,
    ) -> Path | None:

        self.interrupted = False

        self.interruption_reason = None

        self.interruption_task_id = None

        self.interruption_at = None

        self.quota_blocked = False

        self.quota_error = None

        self.quota_reset_time = None

        if save:

            return self.save()

        return None

    # =====================================================
    # CLEAR INTERRUPTION
    # =====================================================

    def clear_interruption(
        self,
    ) -> Path:

        return self.clear_state(
            save=True
        )

    # =====================================================
    # COMPLETED IDS
    # =====================================================

    def get_completed_ids(
        self,
    ) -> set[str]:

        return {
            str(
                item.get(
                    "task_id"
                )
            )
            for item in self.results
            if (
                item.get(
                    "status"
                )
                == "completed"
            )
            and item.get(
                "task_id"
            )
        }

    # =====================================================
    # GET RESULT
    # =====================================================

    def get_result(
        self,
        task_id: str,
    ) -> dict[str, Any] | None:

        task_id = str(
            task_id
        )

        for item in reversed(
            self.results
        ):

            if str(
                item.get(
                    "task_id",
                    "",
                )
            ) == task_id:

                return item

        return None

    # =====================================================
    # ALL RESULTS
    # =====================================================

    def get_results(
        self,
    ) -> list[dict[str, Any]]:

        return [
            dict(item)
            for item in self.results
        ]

    # =====================================================
    # NEXT PENDING TASK
    # =====================================================

    def next_pending_task(
        self,
        task_ids: list[str],
    ) -> str | None:

        completed = (
            self.get_completed_ids()
        )

        for task_id in task_ids:

            if str(
                task_id
            ) not in completed:

                return str(
                    task_id
                )

        return None

    # =====================================================
    # NORMALIZE FOR RESUME
    # =====================================================

    def normalize_for_resume(
        self,
    ) -> None:

        self._deduplicate_results()

        completed = (
            self.get_completed_ids()
        )

        normalized = []

        temporary_statuses = {
            "running",
            "interrupted",
            "rate_limited",
            "quota_blocked",
            "quota_exhausted",
        }

        for item in self.results:

            task_id = item.get(
                "task_id"
            )

            if not task_id:

                continue

            task_id = str(
                task_id
            )

            status = str(
                item.get(
                    "status",
                    "",
                )
            ).lower().strip()

            # -------------------------------------------------
            # COMPLETED = IMMUTABLE
            # -------------------------------------------------

            if (
                task_id in completed
                and status
                == "completed"
            ):

                normalized.append(
                    item
                )

                continue

            # -------------------------------------------------
            # TEMPORARY FAILURE = PENDING
            # -------------------------------------------------

            if status in temporary_statuses:

                normalized.append(
                    {
                        **item,
                        "task_id": task_id,
                        "status": "pending",
                        "reason": (
                            "Normalized "
                            "for safe resume"
                        ),
                        "updated_at":
                            utc_now(),
                    }
                )

                continue

            # -------------------------------------------------
            # PERMANENT FAILURE
            #
            # Keep it as-is. The runner decides whether
            # it should remain failed or be retried.
            # -------------------------------------------------

            normalized.append(
                item
            )

        self.results = normalized

    # =====================================================
    # RESET PROJECT
    # =====================================================

    def reset(
        self,
        query: str,
    ) -> bool:

        path = self.checkpoint_path(
            query
        )

        if not path.exists():

            return False

        path.unlink()

        return True

    # =====================================================
    # SUMMARY
    # =====================================================

    def summary(
        self,
    ) -> dict[str, Any]:

        completed = sum(
            1
            for item in self.results
            if item.get(
                "status"
            )
            == "completed"
        )

        failed = sum(
            1
            for item in self.results
            if item.get(
                "status"
            )
            == "failed"
        )

        pending = sum(
            1
            for item in self.results
            if item.get(
                "status"
            )
            == "pending"
        )

        return {
            "version":
                self.VERSION,

            "query":
                self.query,

            "total_recorded":
                len(self.results),

            "completed":
                completed,

            "failed":
                failed,

            "pending":
                pending,

            "quota_blocked":
                self.quota_blocked,

            "quota_error":
                self.quota_error,

            "quota_reset_time":
                self.quota_reset_time,

            "interrupted":
                self.interrupted,

            "interruption_reason":
                self.interruption_reason,

            "interruption_task_id":
                self.interruption_task_id,

            "interruption_at":
                self.interruption_at,
        }