
from __future__ import annotations

import argparse
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# ENVIRONMENT
# ============================================================

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")

except Exception:
    pass


# ============================================================
# ENGINE IMPORT
# ============================================================

try:
    from engine.autonomous_project_engine import (
        AutonomousProjectEngine,
    )

except ImportError:
    try:
        from core.autonomous_project_engine import (
            AutonomousProjectEngine,
        )

    except ImportError as exc:
        raise ImportError(
            "\nResearchMind engine could not be imported.\n\n"
            "Expected one of:\n"
            "  engine/autonomous_project_engine.py\n"
            "  core/autonomous_project_engine.py\n"
        ) from exc


# ============================================================
# TASK MEMORY
# ============================================================

try:
    from core.task_memory import TaskMemory

except ImportError as exc:
    raise ImportError(
        "\nTaskMemory could not be imported.\n\n"
        "Expected:\n"
        "  core/task_memory.py\n\n"
        f"Original error: {exc}\n"
    ) from exc


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = ROOT_DIR / "outputs"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SUMMARY_FILE = (
    OUTPUT_DIR / "researchmind_summary.json"
)

REPORT_FILE = (
    OUTPUT_DIR / "researchmind_report.md"
)


# ============================================================
# EXPECTED TASKS
# ============================================================

EXPECTED_TASK_IDS = (
    [f"P1-T{i}" for i in range(1, 6)]
    + [f"P2-T{i}" for i in range(1, 6)]
    + [f"P3-T{i}" for i in range(1, 6)]
    + [f"P4-T{i}" for i in range(1, 6)]
    + [f"P5-T{i}" for i in range(1, 7)]
)

TOTAL_TASKS = len(
    EXPECTED_TASK_IDS
)


# ============================================================
# GLOBAL STOP STATE
# ============================================================

_STOP_REQUESTED = False


def _signal_handler(
    signum,
    frame,
):
    global _STOP_REQUESTED

    _STOP_REQUESTED = True

    print()
    print()
    print(
        "ResearchMind stop requested."
    )
    print(
        "Current task will remain resumable."
    )


try:
    signal.signal(
        signal.SIGINT,
        _signal_handler,
    )
except Exception:
    pass


# ============================================================
# TIME
# ============================================================

def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# JSON SAFE
# ============================================================

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


# ============================================================
# ERROR TEXT
# ============================================================

def error_text(
    exc: Any,
) -> str:

    try:
        return str(exc).lower()
    except Exception:
        return repr(exc).lower()


# ============================================================
# QUOTA DETECTION
# ============================================================

def is_daily_quota_error(
    value: Any,
) -> bool:

    text = error_text(value)

    markers = (
        "free-models-per-day",
        "openrouter_free_tier_daily",
        "daily free-model",
        "daily free model",
        "daily quota",
        "daily limit",
        "free model requests per day",
        "free-model requests per day",
    )

    return any(
        marker in text
        for marker in markers
    )


def is_rate_limit_error(
    value: Any,
) -> bool:

    text = error_text(value)

    if is_daily_quota_error(value):
        return True

    markers = (
        "429",
        "rate limit",
        "rate_limit",
        "ratelimit",
        "too many requests",
        "quota exceeded",
        "quota_exceeded",
        "x-ratelimit-remaining",
    )

    return any(
        marker in text
        for marker in markers
    )


# ============================================================
# RESET TIME
# ============================================================

def extract_reset_time(
    value: Any,
) -> str | None:

    text = error_text(value)

    # The OpenRouter error in your logs contains:
    #
    # "X-RateLimit-Reset": 1786492800000
    #
    # We deliberately avoid the broken quote-heavy regex from
    # the previous version.

    marker = (
        "x-ratelimit-reset"
    )

    position = text.find(
        marker
    )

    if position >= 0:

        remaining = text[
            position + len(marker):
        ]

        digits = []

        for char in remaining:

            if char.isdigit():
                digits.append(char)

            elif digits:
                break

        if digits:

            raw = "".join(
                digits
            )

            try:
                timestamp = float(
                    raw
                )

                # OpenRouter uses milliseconds.
                if timestamp > 10_000_000_000:
                    timestamp /= 1000.0

                return datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                ).isoformat()

            except Exception:
                pass

    # Also support an already-human-readable ISO time.

    for token in text.replace(
        ",",
        " ",
    ).split():

        if (
            "t" in token.lower()
            and (
                "+" in token
                or token.endswith("z")
            )
        ):
            cleaned = (
                token
                .strip(
                    "\"'{}[]"
                )
            )

            if (
                "-" in cleaned
                and ":" in cleaned
            ):
                return cleaned

    return None


# ============================================================
# EXTRACT TASKS FROM ENGINE RESULT
# ============================================================

def result_tasks(
    result: Any,
) -> list[dict[str, Any]]:

    if isinstance(
        result,
        dict,
    ):

        for key in (
            "executed_tasks",
            "tasks",
            "results",
        ):

            value = result.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                return [
                    item
                    for item in value
                    if isinstance(
                        item,
                        dict,
                    )
                ]

    for attribute in (
        "executed_tasks",
        "tasks",
        "results",
    ):

        try:
            value = getattr(
                result,
                attribute,
                None,
            )

            if isinstance(
                value,
                list,
            ):
                return [
                    item
                    for item in value
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        except Exception:
            pass

    return []


# ============================================================
# NORMALIZE TASKS
# ============================================================

def normalize_tasks(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    latest: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in tasks:

        if not isinstance(
            item,
            dict,
        ):
            continue

        task_id = item.get(
            "task_id"
        )

        if not task_id:
            continue

        latest[
            str(task_id)
        ] = dict(item)

    normalized = []

    for task_id in EXPECTED_TASK_IDS:

        item = latest.get(
            task_id
        )

        if item is None:
            continue

        status = str(
            item.get(
                "status",
                "",
            )
        ).lower().strip()

        # --------------------------------------------------------
        # A quota/rate-limit task is NOT a permanent failure.
        # --------------------------------------------------------

        if status in {
            "running",
            "pending",
            "interrupted",
            "rate_limited",
            "quota_blocked",
            "quota_exhausted",
        }:

            item["status"] = (
                "pending"
            )

        normalized.append(
            item
        )

    return normalized


# ============================================================
# TASK COUNTS
# ============================================================

def task_counts(
    tasks: list[dict[str, Any]],
) -> tuple[int, int, int]:

    completed = sum(
        1
        for item in tasks
        if item.get("status")
        == "completed"
    )

    failed = sum(
        1
        for item in tasks
        if item.get("status")
        == "failed"
    )

    pending = (
        TOTAL_TASKS
        - completed
        - failed
    )

    return (
        completed,
        failed,
        max(
            0,
            pending,
        ),
    )


# ============================================================
# DETECT QUOTA INSIDE ENGINE RESULT
# ============================================================

def find_quota_task(
    tasks: list[dict[str, Any]],
) -> dict[str, Any] | None:

    for task in reversed(tasks):

        status = str(
            task.get(
                "status",
                "",
            )
        ).lower()

        if status in {
            "rate_limited",
            "quota_blocked",
            "quota_exhausted",
        }:
            return task

        error = task.get(
            "error"
        )

        if error and is_daily_quota_error(
            error
        ):
            return task

        output = task.get(
            "output"
        )

        if output and is_daily_quota_error(
            output
        ):
            return task

    return None


# ============================================================
# CONVERT QUOTA FAILURE -> PENDING
# ============================================================

def convert_quota_failure_to_pending(
    tasks: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any] | None,
]:

    normalized = []

    quota_task = None

    for original in tasks:

        task = dict(
            original
        )

        status = str(
            task.get(
                "status",
                "",
            )
        ).lower()

        error = task.get(
            "error"
        )

        output = task.get(
            "output"
        )

        quota_error = (
            is_daily_quota_error(
                error
            )
            or is_daily_quota_error(
                output
            )
            or (
                status
                in {
                    "rate_limited",
                    "quota_blocked",
                    "quota_exhausted",
                }
            )
        )

        if quota_error:

            task["status"] = (
                "pending"
            )

            task.pop(
                "traceback",
                None,
            )

            task[
                "quota_blocked"
            ] = True

            quota_task = task

        normalized.append(
            task
        )

    return (
        normalized,
        quota_task,
    )


# ============================================================
# SAVE CHECKPOINT SAFELY
# ============================================================

def save_checkpoint(
    memory: TaskMemory,
    query: str,
    tasks: list[dict[str, Any]],
    *,
    quota_blocked: bool = False,
    quota_error: str | None = None,
    reset_time: str | None = None,
) -> None:

    # IMPORTANT:
    #
    # TaskMemory.save() requires a query.
    #
    # Therefore NEVER call:
    #
    #     memory.save(results=tasks)
    #
    # by itself.

    try:

        memory.save(
            results=tasks,
            query=query,
        )

    except Exception as exc:

        print()
        print(
            "WARNING: Could not save checkpoint:"
        )
        print(
            str(exc)
        )

        return

    # Some V8.6 TaskMemory implementations expose
    # quota-specific state.

    if quota_blocked:

        try:

            task_id = None

            if tasks:

                for task in reversed(
                    tasks
                ):

                    if task.get(
                        "quota_blocked"
                    ):

                        task_id = (
                            task.get(
                                "task_id"
                            )
                        )

                        break

            memory.mark_quota_exhausted(
                task_id=task_id,
                reason=(
                    quota_error
                    or "OpenRouter daily free-model quota exhausted."
                ),
                reset_time=reset_time,
            )

        except Exception as exc:

            print(
                "WARNING: Could not record "
                f"quota state: {exc}"
            )


# ============================================================
# WRITE SUMMARY
# ============================================================

def write_summary(
    query: str,
    tasks: list[dict[str, Any]],
    *,
    quota_blocked: bool = False,
    quota_error: str | None = None,
    reset_time: str | None = None,
) -> None:

    completed, failed, pending = (
        task_counts(tasks)
    )

    summary = {
        "engine": (
            "ResearchMind-V8.7"
        ),
        "query": query,
        "generated_at": utc_now(),
        "total": TOTAL_TASKS,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "quota_blocked": quota_blocked,
        "quota_error": quota_error,
        "quota_reset_time": reset_time,
        "tasks": json_safe(
            tasks
        ),
    }

    SUMMARY_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# WRITE MARKDOWN REPORT
# ============================================================

def write_report(
    query: str,
    tasks: list[dict[str, Any]],
    *,
    quota_blocked: bool = False,
    quota_error: str | None = None,
    reset_time: str | None = None,
) -> None:

    completed, failed, pending = (
        task_counts(tasks)
    )

    lines = [
        "# ResearchMind V8.7",
        "",
        f"**Research topic:** {query}",
        "",
        f"**Generated:** {utc_now()}",
        "",
        "## Status",
        "",
        (
            f"- Completed: "
            f"{completed}/{TOTAL_TASKS}"
        ),
        f"- Failed: {failed}",
        f"- Pending: {pending}",
        (
            f"- Quota blocked: "
            f"{quota_blocked}"
        ),
        "",
    ]

    if quota_blocked:

        lines.extend(
            [
                "## Execution Paused",
                "",
                (
                    "ResearchMind paused because "
                    "OpenRouter reported that the "
                    "daily free-model quota is exhausted."
                ),
                "",
                (
                    f"**Error:** "
                    f"{quota_error or 'Unknown quota error'}"
                ),
                "",
            ]
        )

        if reset_time:

            lines.extend(
                [
                    (
                        f"**Quota reset:** "
                        f"{reset_time}"
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                (
                    "The current task was returned "
                    "to `pending` and will be retried "
                    "on the next run."
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Tasks",
            "",
        ]
    )

    for task in tasks:

        task_id = task.get(
            "task_id",
            "UNKNOWN",
        )

        title = task.get(
            "title",
            "",
        )

        status = task.get(
            "status",
            "unknown",
        )

        lines.extend(
            [
                (
                    f"### {task_id} — {title}"
                ),
                "",
                (
                    f"**Status:** `{status}`"
                ),
                "",
            ]
        )

        output = task.get(
            "output"
        )

        if output:

            lines.extend(
                [
                    str(output),
                    "",
                ]
            )

        error = task.get(
            "error"
        )

        if error:

            lines.extend(
                [
                    (
                        f"**Error:** {error}"
                    ),
                    "",
                ]
            )

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ============================================================
# CHECKPOINT DISPLAY
# ============================================================

def display_checkpoint(
    query: str,
    memory: TaskMemory,
    existing: dict[str, Any],
) -> list[dict[str, Any]]:

    tasks = normalize_tasks(
        memory.get_results()
    )

    completed, failed, pending = (
        task_counts(tasks)
    )

    print()
    print(
        f"Checkpoint found for: {query}"
    )

    print(
        f"Completed: "
        f"{completed}/{TOTAL_TASKS}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Pending: {pending}"
    )

    interruption_task = (
        existing.get(
            "interruption_task_id"
        )
    )

    if interruption_task:

        print(
            f"Resume task: "
            f"{interruption_task}"
        )

    if existing.get(
        "interrupted"
    ):

        print(
            "Checkpoint contains an "
            "interrupted run."
        )

        reason = existing.get(
            "interruption_reason"
        )

        if reason:

            print(
                f"Reason: {reason}"
            )

    return tasks


# ============================================================
# MAIN RESEARCH FUNCTION
# ============================================================

def run_research(
    query: str,
    max_tasks: int | None = None,
    resume: bool = True,
) -> int:

    print()
    print("=" * 70)
    print(" ResearchMind V8.7")
    print(" Safe Autonomous Research Runner")
    print(" OpenRouter 429 / Daily Quota Protection")
    print("=" * 70)

    print(
        f"Topic      : {query}"
    )

    print(
        f"Max tasks  : "
        f"{max_tasks if max_tasks is not None else 'ALL'}"
    )

    print(
        f"Resume     : {resume}"
    )

    print("=" * 70)

    # ========================================================
    # LOAD MEMORY
    # ========================================================

    memory = TaskMemory()

    existing = None

    if resume:

        try:
            existing = memory.load(
                query
            )
        except Exception as exc:

            print()
            print(
                "WARNING: Could not load checkpoint:"
            )
            print(
                str(exc)
            )

    if existing:

        tasks = display_checkpoint(
            query,
            memory,
            existing,
        )

        # Normalize checkpoint and explicitly preserve query.
        save_checkpoint(
            memory,
            query,
            tasks,
        )

    else:

        print()
        print(
            f"Creating new checkpoint for: "
            f"{query}"
        )

        memory.initialize(
            query
        )

        memory.save(
            query=query
        )

        tasks = []

    # ========================================================
    # RUN ENGINE
    # ========================================================

    print()
    print(
        "Starting autonomous research..."
    )
    print()

    engine = None
    result = None

    try:

        engine = (
            AutonomousProjectEngine()
        )

        result = engine.run(
            query=query,
            max_tasks=max_tasks,
            resume=resume,
        )

    except KeyboardInterrupt:

        print()
        print(
            "ResearchMind interrupted by user."
        )

        existing_tasks = (
            memory.get_results()
        )

        tasks = normalize_tasks(
            existing_tasks
        )

        save_checkpoint(
            memory,
            query,
            tasks,
        )

        write_summary(
            query,
            tasks,
        )

        write_report(
            query,
            tasks,
        )

        return 130

    except Exception as exc:

        # ====================================================
        # DIRECT EXCEPTION QUOTA DETECTION
        # ====================================================

        if is_rate_limit_error(
            exc
        ):

            reset_time = (
                extract_reset_time(
                    exc
                )
            )

            quota_error = str(
                exc
            )

            print()
            print("=" * 70)
            print(
                " RESEARCH PAUSED — OPENROUTER QUOTA EXHAUSTED"
            )
            print("=" * 70)

            print(
                quota_error
            )

            if reset_time:

                print()
                print(
                    f"Quota reset: {reset_time}"
                )

            # Do NOT mark the current task failed.

            current_tasks = (
                memory.get_results()
            )

            current_tasks = (
                normalize_tasks(
                    current_tasks
                )
            )

            current_tasks, quota_task = (
                convert_quota_failure_to_pending(
                    current_tasks
                )
            )

            save_checkpoint(
                memory,
                query,
                current_tasks,
                quota_blocked=True,
                quota_error=quota_error,
                reset_time=reset_time,
            )

            write_summary(
                query,
                current_tasks,
                quota_blocked=True,
                quota_error=quota_error,
                reset_time=reset_time,
            )

            write_report(
                query,
                current_tasks,
                quota_blocked=True,
                quota_error=quota_error,
                reset_time=reset_time,
            )

            print()
            print(
                f"Status       : PAUSED — QUOTA EXHAUSTED"
            )

            completed, failed, pending = (
                task_counts(
                    current_tasks
                )
            )

            print(
                f"Completed    : "
                f"{completed}/{TOTAL_TASKS}"
            )

            print(
                f"Failed       : {failed}"
            )

            print(
                f"Pending      : {pending}"
            )

            print()
            print(
                "The current task is PENDING."
            )

            print(
                "It will be retried after the quota resets."
            )

            return 0

        # ====================================================
        # NORMAL ENGINE ERROR
        # ====================================================

        print()
        print("=" * 70)
        print(
            " RESEARCH ENGINE ERROR"
        )
        print("=" * 70)
        print(
            str(exc)
        )
        print("=" * 70)

        raise

    # ========================================================
    # PROCESS ENGINE RESULT
    # ========================================================

    engine_tasks = result_tasks(
        result
    )

    if engine_tasks:

        combined = (
            normalize_tasks(
                engine_tasks
            )
        )

    else:

        combined = normalize_tasks(
            memory.get_results()
        )

    # ========================================================
    # CRITICAL FIX:
    #
    # The current V8.2 engine may incorrectly return:
    #
    #     status = failed
    #
    # even when the actual error is:
    #
    #     free-models-per-day
    #
    # We detect that here and convert it to PENDING.
    # ========================================================

    quota_task = find_quota_task(
        engine_tasks
    )

    quota_blocked = (
        quota_task is not None
    )

    quota_error = None
    reset_time = None

    if quota_blocked:

        quota_error = (
            quota_task.get(
                "error"
            )
            or quota_task.get(
                "output"
            )
            or (
                "OpenRouter daily "
                "free-model quota exhausted."
            )
        )

        reset_time = (
            extract_reset_time(
                quota_error
            )
        )

        combined, _ = (
            convert_quota_failure_to_pending(
                combined
            )
        )

        # ----------------------------------------------------
        # Make sure the quota task is actually present.
        # If engine failed before TaskMemory saved it,
        # add it explicitly.
        # ----------------------------------------------------

        task_id = (
            quota_task.get(
                "task_id"
            )
        )

        if task_id:

            found = False

            for task in combined:

                if task.get(
                    "task_id"
                ) == task_id:

                    found = True
                    break

            if not found:

                pending_record = {
                    "task_id": task_id,
                    "title": quota_task.get(
                        "title",
                        "Pending task",
                    ),
                    "status": "pending",
                    "quota_blocked": True,
                    "error": quota_error,
                    "updated_at": utc_now(),
                }

                combined.append(
                    pending_record
                )

        # Sort back into P1-T1 ... P5-T6 order.

        order = {
            task_id: index
            for index, task_id
            in enumerate(
                EXPECTED_TASK_IDS
            )
        }

        combined.sort(
            key=lambda item:
            order.get(
                item.get(
                    "task_id"
                ),
                999,
            )
        )

        save_checkpoint(
            memory,
            query,
            combined,
            quota_blocked=True,
            quota_error=str(
                quota_error
            ),
            reset_time=reset_time,
        )

        write_summary(
            query,
            combined,
            quota_blocked=True,
            quota_error=str(
                quota_error
            ),
            reset_time=reset_time,
        )

        write_report(
            query,
            combined,
            quota_blocked=True,
            quota_error=str(
                quota_error
            ),
            reset_time=reset_time,
        )

        completed, failed, pending = (
            task_counts(
                combined
            )
        )

        print()
        print("=" * 70)
        print(
            " RESEARCH PAUSED — QUOTA EXHAUSTED"
        )
        print("=" * 70)

        print(
            f"Status       : PAUSED — QUOTA EXHAUSTED"
        )

        print(
            f"Completed    : "
            f"{completed}/{TOTAL_TASKS}"
        )

        print(
            f"Failed       : {failed}"
        )

        print(
            f"Pending      : {pending}"
        )

        if reset_time:

            print(
                f"Quota reset  : {reset_time}"
            )

        print()
        print(
            "The current task remains PENDING."
        )

        print(
            "No task was permanently failed because of the quota."
        )

        print()
        print(
            "Run the same command again after the quota resets."
        )

        print("=" * 70)

        return 0

    # ========================================================
    # NORMAL RESULT
    # ========================================================

    # If the engine completed tasks, save them.
    save_checkpoint(
        memory,
        query,
        combined,
    )

    write_summary(
        query,
        combined,
    )

    write_report(
        query,
        combined,
    )

    completed, failed, pending = (
        task_counts(
            combined
        )
    )

    result_status = (
        result.get(
            "status",
            "unknown",
        )
        if isinstance(
            result,
            dict,
        )
        else "unknown"
    )

    stopped_reason = (
        result.get(
            "stopped_reason",
            "unknown",
        )
        if isinstance(
            result,
            dict,
        )
        else "unknown"
    )

    print()
    print("=" * 70)
    print(
        " RESEARCH RUN FINISHED"
    )
    print("=" * 70)

    print(
        f"Status       : {result_status}"
    )

    print(
        f"Completed    : "
        f"{completed}/{TOTAL_TASKS}"
    )

    print(
        f"Failed       : {failed}"
    )

    print(
        f"Pending      : {pending}"
    )

    print(
        f"Stopped      : {stopped_reason}"
    )

    print()
    print(
        f"Summary      : {SUMMARY_FILE}"
    )

    print(
        f"Report       : {REPORT_FILE}"
    )

    print("=" * 70)

    return 0


# ============================================================
# ARGUMENT PARSER
# ============================================================

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "ResearchMind autonomous research runner"
        )
    )

    parser.add_argument(
        "topic",
        nargs="?",
        help="Research topic",
    )

    parser.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help=(
            "Maximum number of tasks to execute"
        ),
    )

    parser.add_argument(
        "--no-resume",
        action="store_true",
        help=(
            "Start without loading an existing checkpoint"
        ),
    )

    return parser


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    parser = build_parser()

    args = parser.parse_args()

    query = args.topic

    if not query:

        print()
        print(
            "Enter your research topic:"
        )
        print()

        try:

            query = input(
                "> "
            ).strip()

        except EOFError:

            print()
            print(
                "No research topic supplied."
            )

            return 1

    if not query:

        print()
        print(
            "Research topic cannot be empty."
        )

        return 1

    if (
        args.max_tasks is not None
        and args.max_tasks <= 0
    ):

        parser.error(
            "--max-tasks must be greater than zero"
        )

    return run_research(
        query=query,
        max_tasks=args.max_tasks,
        resume=not args.no_resume,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )
