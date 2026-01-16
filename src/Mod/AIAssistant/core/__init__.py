# SPDX-License-Identifier: LGPL-2.1-or-later
"""Core business logic for AI Assistant."""

from .context import (
    build_context,
    start_console_observer,
    stop_console_observer,
    get_console_buffer,
    clear_console_buffer,
    get_selected_objects,
    get_selection_summary,
)
from .source import (
    get_source_path,
    init_source_file,
    read_source,
    append_code,
    clear_source,
    exists as source_exists,
    get_context as get_source_context,
    backup_source,
    restore_source,
    has_backup,
    get_backup_content,
    clear_backup,
)
from .snapshot import (
    get_snapshots_dir,
    capture_current_state,
    capture_object_data,
    save_snapshot,
)
from .changes import (
    PropertyChange,
    ObjectChange,
    ChangeSet,
    detect_changes,
    format_change_summary,
)
from .executor import (
    execute,
    validate_code,
)
from .preview import PreviewManager

__all__ = [
    # context
    "build_context",
    "start_console_observer",
    "stop_console_observer",
    "get_console_buffer",
    "clear_console_buffer",
    "get_selected_objects",
    "get_selection_summary",
    # source
    "get_source_path",
    "init_source_file",
    "read_source",
    "append_code",
    "clear_source",
    "source_exists",
    "get_source_context",
    "backup_source",
    "restore_source",
    "has_backup",
    "get_backup_content",
    "clear_backup",
    # snapshot
    "get_snapshots_dir",
    "capture_current_state",
    "capture_object_data",
    "save_snapshot",
    # changes
    "PropertyChange",
    "ObjectChange",
    "ChangeSet",
    "detect_changes",
    "format_change_summary",
    # executor
    "execute",
    "validate_code",
    # preview
    "PreviewManager",
]
