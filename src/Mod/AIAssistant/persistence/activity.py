# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Activity Logger - Logs all user interactions and system events in NDJSON format.

Logs are stored in the project folder: {doc_stem}/activity.ndjson

NDJSON (Newline Delimited JSON) - one JSON object per line, machine-parseable.
Use `jq` to query: cat activity.ndjson | jq 'select(.event == "MESSAGE_SENT")'
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import FreeCAD


class _LogEncoder(json.JSONEncoder):
    """JSON encoder that handles Path objects and other non-serializable types."""

    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def get_log_path() -> Optional[Path]:
    """Get the activity log path for the active document.

    Returns:
        Path to {doc_stem}/activity.ndjson, or None if document not saved.
    """
    try:
        doc = FreeCAD.ActiveDocument
        if doc and doc.FileName:
            doc_path = Path(doc.FileName)
            project_dir = doc_path.parent / doc_path.stem
            project_dir.mkdir(parents=True, exist_ok=True)
            return project_dir / "activity.ndjson"
    except Exception:
        pass
    return None


def log(event: str, level: str = "INFO", **kwargs: Any) -> None:
    """Log an event to the activity log in NDJSON format.

    Args:
        event: Event name (e.g., "PREVIEW_APPROVED", "MESSAGE_SENT")
        level: Log level (INFO, WARN, ERROR, DEBUG)
        **kwargs: Additional structured data for this event
    """
    log_path = get_log_path()
    if not log_path:
        return

    # Build log entry
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "level": level,
        **kwargs,
    }

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, cls=_LogEncoder) + "\n")
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"AIAssistant: Failed to write activity log: {e}\n")


# Convenience functions for common events


def log_message_sent(message: str, session_id: str = None) -> None:
    """Log user message submission."""
    log("MESSAGE_SENT", message=message, session_id=session_id)


def log_response_received(
    duration_ms: float,
    cost_usd: float,
    tool_count: int,
    model: str = None,
    session_id: str = None,
) -> None:
    """Log LLM response received."""
    log(
        "RESPONSE_RECEIVED",
        duration_ms=round(duration_ms, 1),
        cost_usd=round(cost_usd, 6),
        tool_count=tool_count,
        model=model,
        session_id=session_id,
    )


def log_tool_calls(tool_calls: list, session_id: str = None) -> None:
    """Log tool calls made by Claude."""
    log("TOOL_CALLS", tools=tool_calls, count=len(tool_calls), session_id=session_id)


def log_llm_response(response: str, session_id: str = None) -> None:
    """Log full LLM response text."""
    log("LLM_RESPONSE", response=response, session_id=session_id)


def log_preview_created(object_count: int, is_deletion: bool = False) -> None:
    """Log preview creation."""
    log("PREVIEW_CREATED", object_count=object_count, is_deletion=is_deletion)


def log_preview_approved() -> None:
    """Log preview approval."""
    log("PREVIEW_APPROVED")


def log_preview_cancelled() -> None:
    """Log preview cancellation."""
    log("PREVIEW_CANCELLED")


def log_plan_approved(plan: str = "") -> None:
    """Log plan approval."""
    log("PLAN_APPROVED", plan=plan)


def log_plan_edited(original: str = "", edited: str = "") -> None:
    """Log plan edit."""
    log("PLAN_EDITED", original=original, edited=edited)


def log_plan_cancelled() -> None:
    """Log plan cancellation."""
    log("PLAN_CANCELLED")


def log_code_executed(success: bool, message: str = "", code: str = None) -> None:
    """Log code execution result."""
    log("CODE_EXECUTED", success=success, message=message, code=code)


def log_session_created(session_id: str) -> None:
    """Log new session creation."""
    log("SESSION_CREATED", session_id=session_id)


def log_session_loaded(session_id: str) -> None:
    """Log session load."""
    log("SESSION_LOADED", session_id=session_id)


def log_session_cleared() -> None:
    """Log session clear."""
    log("SESSION_CLEARED")


def log_snapshot_saved(snapshot_id: str, object_count: int = None) -> None:
    """Log snapshot save."""
    log("SNAPSHOT_SAVED", snapshot_id=snapshot_id, object_count=object_count)


def log_setting_changed(setting: str, value: Any) -> None:
    """Log setting change."""
    log("SETTING_CHANGED", setting=setting, value=value)


def log_source_edited(tool_calls: int, file_path: str = None) -> None:
    """Log source.py edit by Claude."""
    log("SOURCE_EDITED", tool_calls=tool_calls, file_path=file_path)


def log_source_restored(reason: str = "cancelled") -> None:
    """Log source.py restoration from backup."""
    log("SOURCE_RESTORED", reason=reason)


def log_error(error: str, context: str = None) -> None:
    """Log an error."""
    log("ERROR", level="ERROR", error=error, context=context)


def log_panel_opened() -> None:
    """Log panel opened."""
    log("PANEL_OPENED")


def log_panel_closed() -> None:
    """Log panel closed."""
