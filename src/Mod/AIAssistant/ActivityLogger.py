# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Activity Logger - Logs all user interactions and system events to a .log file.

Logs are stored in the project folder: {doc_stem}/activity.log
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import FreeCAD


def get_log_path() -> Optional[Path]:
    """Get the activity log path for the active document.

    Returns:
        Path to {doc_stem}/activity.log, or None if document not saved.
    """
    try:
        doc = FreeCAD.ActiveDocument
        if doc and doc.FileName:
            doc_path = Path(doc.FileName)
            project_dir = doc_path.parent / doc_path.stem
            project_dir.mkdir(parents=True, exist_ok=True)
            return project_dir / "activity.log"
    except Exception:
        pass
    return None


def log(event: str, details: str = "", level: str = "INFO") -> None:
    """Log an event to the activity log.

    Args:
        event: Short event name (e.g., "PREVIEW_APPROVED", "MESSAGE_SENT")
        details: Additional details about the event
        level: Log level (INFO, WARN, ERROR, DEBUG)
    """
    log_path = get_log_path()
    if not log_path:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # Format: [timestamp] LEVEL EVENT: details
    if details:
        line = f"[{timestamp}] {level:5} {event}: {details}\n"
    else:
        line = f"[{timestamp}] {level:5} {event}\n"

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"AIAssistant: Failed to write activity log: {e}\n")


# Convenience functions for common events

def log_message_sent(message: str) -> None:
    """Log user message submission."""
    preview = message[:100] + "..." if len(message) > 100 else message
    log("MESSAGE_SENT", preview)


def log_response_received(duration_ms: float, cost_usd: float, tool_count: int) -> None:
    """Log LLM response received."""
    log("RESPONSE_RECEIVED", f"duration={duration_ms:.0f}ms, cost=${cost_usd:.4f}, tools={tool_count}")


def log_preview_created(object_count: int, is_deletion: bool = False) -> None:
    """Log preview creation."""
    action = "deletion" if is_deletion else "creation"
    log("PREVIEW_CREATED", f"{action} preview with {object_count} objects")


def log_preview_approved() -> None:
    """Log preview approval."""
    log("PREVIEW_APPROVED")


def log_preview_cancelled() -> None:
    """Log preview cancellation."""
    log("PREVIEW_CANCELLED")


def log_plan_approved(plan_preview: str = "") -> None:
    """Log plan approval."""
    log("PLAN_APPROVED", plan_preview[:50] if plan_preview else "")


def log_plan_edited() -> None:
    """Log plan edit."""
    log("PLAN_EDITED")


def log_plan_cancelled() -> None:
    """Log plan cancellation."""
    log("PLAN_CANCELLED")


def log_code_executed(success: bool, message: str = "") -> None:
    """Log code execution result."""
    status = "success" if success else "failed"
    log("CODE_EXECUTED", f"{status}: {message[:100]}" if message else status)


def log_session_created(session_id: str) -> None:
    """Log new session creation."""
    log("SESSION_CREATED", session_id)


def log_session_loaded(session_id: str) -> None:
    """Log session load."""
    log("SESSION_LOADED", session_id)


def log_session_cleared() -> None:
    """Log session clear."""
    log("SESSION_CLEARED")


def log_snapshot_saved(snapshot_id: str) -> None:
    """Log snapshot save."""
    log("SNAPSHOT_SAVED", snapshot_id)


def log_setting_changed(setting: str, value: str) -> None:
    """Log setting change."""
    log("SETTING_CHANGED", f"{setting}={value}")


def log_source_edited(tool_calls: int) -> None:
    """Log source.py edit by Claude."""
    log("SOURCE_EDITED", f"via {tool_calls} tool calls")


def log_source_restored() -> None:
    """Log source.py restoration from backup."""
    log("SOURCE_RESTORED", "from backup")


def log_error(error: str) -> None:
    """Log an error."""
    log("ERROR", error, level="ERROR")


def log_panel_opened() -> None:
    """Log panel opened."""
    log("PANEL_OPENED")


def log_panel_closed() -> None:
    """Log panel closed."""
    log("PANEL_CLOSED")
