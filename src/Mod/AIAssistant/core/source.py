# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Source Manager - Maintain generating Python script alongside FreeCAD document.

Accumulates all successfully executed AI-generated code into a single Python
file that can regenerate the document. Stored in project subfolder:
  {doc_stem}/source.py

This provides:
1. Full context for the LLM when making modifications
2. Version-controllable source of truth
3. Ability to regenerate document from scratch
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

import FreeCAD


# Buffer for code when document isn't saved yet
# List of (code, description, timestamp) tuples
_pending_code: List[Tuple[str, str, str]] = []

# Document observer instance (set on module load)
_observer = None

# Backup of source.py content before Claude edits it
# Used for restore on cancel and diff preview
_source_backup: Optional[str] = None


class _SourceManagerObserver:
    """
    Document observer that flushes pending code when document is saved.

    This ensures code isn't lost if user saves document but doesn't
    execute any more AI code afterward.
    """

    def slotStartSaveDocument(self, doc, filename):
        """Called when document save begins - initialize source file and flush pending code."""
        global _pending_code

        # Build source path in project subfolder: parent/doc_stem/source.py
        file_path = Path(filename)
        project_dir = file_path.parent / file_path.stem
        project_dir.mkdir(parents=True, exist_ok=True)
        source_path = project_dir / "source.py"

        try:
            # Always ensure source file exists (proactive creation)
            if not source_path.exists():
                init_source_file(source_path, doc.Name)

            # Flush any pending code
            if _pending_code:
                FreeCAD.Console.PrintMessage(
                    f"SourceManager: Flushing {len(_pending_code)} pending code blocks\n"
                )
                _flush_pending_to_file(source_path)

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"SourceManager: Failed on save: {e}\n")


def _register_observer():
    """Register the document observer if not already registered."""
    global _observer

    if _observer is not None:
        return

    _observer = _SourceManagerObserver()
    FreeCAD.addDocumentObserver(_observer)
    FreeCAD.Console.PrintMessage("SourceManager: Document observer registered\n")


def _unregister_observer():
    """Unregister the document observer."""
    global _observer

    if _observer is None:
        return

    try:
        FreeCAD.removeDocumentObserver(_observer)
    except Exception:
        pass
    _observer = None


# Auto-register observer on module load
_register_observer()


def get_source_path() -> Optional[Path]:
    """
    Get path to source file for active document.

    The source file is stored in project subfolder: parent/doc_stem/source.py

    Returns:
        Path to source file, or None if document not saved
    """
    doc = FreeCAD.ActiveDocument
    if not doc or not doc.FileName:
        return None

    doc_path = Path(doc.FileName)
    return doc_path.parent / doc_path.stem / "source.py"


# Lines to strip from code blocks (already in header)
# FreeCAD uses both FreeCAD.* and App.* (App is an alias)
_BOILERPLATE_PATTERNS = [
    "import FreeCAD",
    "import Part",
    "from FreeCAD import",
    "from Part import",
    "doc = FreeCAD.ActiveDocument or FreeCAD.newDocument",
    "doc = FreeCAD.ActiveDocument",
    "doc = App.ActiveDocument or App.newDocument",
    "doc = App.ActiveDocument",
    "doc = App.activeDocument()",
    "doc = FreeCAD.activeDocument()",
    "if doc is None:",
    "doc = FreeCAD.newDocument(",
    "doc = App.newDocument(",
]


def _clean_boilerplate(code: str) -> str:
    """
    Remove redundant boilerplate from code block.

    Since the source file header already has imports and doc setup,
    we strip these from individual code blocks to keep the file clean.
    """
    lines = code.strip().split("\n")
    cleaned = []
    skip_next_indent = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines at the start
        if not cleaned and not stripped:
            continue

        # Check if line matches boilerplate pattern
        is_boilerplate = False
        for pattern in _BOILERPLATE_PATTERNS:
            if stripped.startswith(pattern):
                is_boilerplate = True
                # If it's an "if doc is None:" we need to skip the next indented line too
                if stripped == "if doc is None:":
                    skip_next_indent = True
                break

        if is_boilerplate:
            continue

        # Skip indented line after "if doc is None:"
        if skip_next_indent and line.startswith((" ", "\t")):
            skip_next_indent = False
            continue
        skip_next_indent = False

        cleaned.append(line)

    # Remove leading/trailing empty lines
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    return "\n".join(cleaned)


def append_code(code: str, description: str = "") -> bool:
    """
    Append executed code to the source file.

    If the document isn't saved yet, buffers the code in memory.
    When the document is saved (has a FileName), flushes the buffer
    and writes to the source file.

    Args:
        code: Python code that was successfully executed
        description: Optional description (e.g., from LLM response)

    Returns:
        True if saved/buffered successfully, False otherwise
    """
    global _pending_code

    # Clean boilerplate before saving
    code = _clean_boilerplate(code)

    # Skip if code is empty after cleaning
    if not code.strip():
        return True

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_path = get_source_path()

    # If document not saved yet, buffer the code
    if not source_path:
        _pending_code.append((code, description, timestamp))
        FreeCAD.Console.PrintMessage(
            f"SourceManager: Buffered code ({len(_pending_code)} blocks pending, save document to persist)\n"
        )
        return True

    try:
        # Flush any pending code first (document was just saved)
        if _pending_code:
            _flush_pending_to_file(source_path)

        # Write the new code block
        _write_code_block(source_path, code, description, timestamp)
        return True

    except Exception as e:
        FreeCAD.Console.PrintWarning(f"SourceManager: Failed to save: {e}\n")
        return False


def _flush_pending_to_file(source_path: Path) -> None:
    """Flush all pending code blocks to the source file."""
    global _pending_code

    if not _pending_code:
        return

    FreeCAD.Console.PrintMessage(
        f"SourceManager: Flushing {len(_pending_code)} pending code blocks to {source_path.name}\n"
    )

    for code, description, timestamp in _pending_code:
        _write_code_block(source_path, code, description, timestamp)

    _pending_code = []


def _write_code_block(source_path: Path, code: str, description: str, timestamp: str) -> None:
    """Write a single code block to the source file."""
    # Create file with header if new
    if not source_path.exists():
        doc_name = FreeCAD.ActiveDocument.Name if FreeCAD.ActiveDocument else "Design"
        with open(source_path, "w") as f:
            f.write(f"# FreeCAD AI Source - {doc_name}\n")
            f.write(f"# Created: {timestamp}\n")
            f.write("#\n")
            f.write("# This script can regenerate the document.\n")
            f.write("# Run in FreeCAD's Python console or as a macro.\n")
            f.write("#\n\n")
            f.write("import FreeCAD\n")
            f.write("import Part\n\n")
            f.write('doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")\n\n')

    # Append code block
    with open(source_path, "a") as f:
        f.write(f"\n# === {timestamp} ===\n")
        if description:
            # Add description as comments (limit to 3 lines)
            for line in description.strip().split("\n")[:3]:
                f.write(f"# {line}\n")
        f.write(code.strip())
        f.write("\n")


def read_source() -> str:
    """
    Read current source file content, including any pending (unsaved) code.

    Returns:
        Source file content plus pending code, or empty string if none
    """
    parts = []

    # Read from file if it exists
    source_path = get_source_path()
    if source_path and source_path.exists():
        try:
            with open(source_path, "r") as f:
                parts.append(f.read())
        except Exception:
            pass

    # Add pending code (not yet written to file)
    if _pending_code:
        if not parts:
            # No file yet, add a header
            parts.append("# FreeCAD AI Source (unsaved document)\n")
            parts.append("# Save the document to persist this code.\n\n")
            parts.append("import FreeCAD\n")
            parts.append("import Part\n\n")
            parts.append('doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")\n')

        for code, description, timestamp in _pending_code:
            block = f"\n# === {timestamp} (pending) ===\n"
            if description:
                for line in description.strip().split("\n")[:3]:
                    block += f"# {line}\n"
            block += code.strip() + "\n"
            parts.append(block)

    return "".join(parts)


def get_context(max_lines: int = 50) -> str:
    """
    Get source code formatted for LLM context.

    Shows the most recent code blocks to give the LLM understanding
    of how objects were created.

    Args:
        max_lines: Maximum lines to include (from end of file)

    Returns:
        Formatted context string, or empty if no source file
    """
    source = read_source()
    if not source:
        return ""

    lines = source.split("\n")

    # Count code blocks (by counting timestamp headers)
    block_count = sum(1 for line in lines if line.startswith("# === "))

    # Get last N lines for recent context
    if len(lines) > max_lines:
        recent_lines = lines[-max_lines:]
        truncated = True
    else:
        recent_lines = lines
        truncated = False

    recent = "\n".join(recent_lines)

    result = f"\n### Source Code History ({block_count} code blocks):\n"
    if truncated:
        result += f"(showing last {max_lines} lines)\n"
    result += f"```python\n{recent}\n```"

    return result


def clear_source() -> bool:
    """
    Delete the source file to start fresh.

    Returns:
        True if deleted or didn't exist, False on error
    """
    source_path = get_source_path()
    if not source_path:
        return False

    try:
        if source_path.exists():
            source_path.unlink()
        return True
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"SourceManager: Failed to clear: {e}\n")
        return False


def exists() -> bool:
    """Check if source file exists for current document."""
    source_path = get_source_path()
    return source_path is not None and source_path.exists()


def init_source_file(source_path: Path = None, doc_name: str = None) -> bool:
    """
    Initialize an empty source file with boilerplate headers.

    Creates the source file proactively even before any AI code runs.
    This ensures every saved document has a corresponding source file.

    Args:
        source_path: Path to create file at (defaults to get_source_path())
        doc_name: Document name for header (defaults to ActiveDocument.Name)

    Returns:
        True if created or already exists, False on error
    """
    if source_path is None:
        source_path = get_source_path()

    if not source_path:
        return False  # Document not saved yet

    if source_path.exists():
        return True  # Already exists

    if doc_name is None:
        doc_name = FreeCAD.ActiveDocument.Name if FreeCAD.ActiveDocument else "Design"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(source_path, "w") as f:
            f.write(f"# FreeCAD AI Source - {doc_name}\n")
            f.write(f"# Created: {timestamp}\n")
            f.write("#\n")
            f.write("# This script can regenerate the document.\n")
            f.write("# Run in FreeCAD's Python console or as a macro.\n")
            f.write("#\n\n")
            f.write("import FreeCAD\n")
            f.write("import Part\n\n")
            f.write('doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")\n\n')

        FreeCAD.Console.PrintMessage(f"SourceManager: Initialized {source_path.name}\n")
        return True

    except Exception as e:
        FreeCAD.Console.PrintWarning(f"SourceManager: Failed to initialize: {e}\n")
        return False


# =============================================================================
# Backup/Restore for Direct Source Editing
# =============================================================================


def backup_source() -> bool:
    """
    Backup source.py content before Claude edits it.

    Called before each Claude Code invocation to enable:
    1. Restore on cancel (undo Claude's edits)
    2. Diff preview (compare OLD vs NEW source.py execution)

    Returns:
        True if backed up successfully, False if no source file
    """
    global _source_backup

    source_path = get_source_path()
    if not source_path or not source_path.exists():
        _source_backup = None
        return False

    try:
        _source_backup = source_path.read_text()
        FreeCAD.Console.PrintMessage("SourceManager: Backed up source.py\n")
        return True
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"SourceManager: Backup failed: {e}\n")
        _source_backup = None
        return False


def restore_source() -> bool:
    """
    Restore source.py from backup (on cancel).

    Called when user cancels preview to undo Claude's edits.

    Returns:
        True if restored successfully, False if no backup
    """
    global _source_backup

    if _source_backup is None:
        return False

    source_path = get_source_path()
    if not source_path:
        _source_backup = None
        return False

    try:
        source_path.write_text(_source_backup)
        FreeCAD.Console.PrintMessage("SourceManager: Restored source.py from backup\n")
        _source_backup = None
        return True
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"SourceManager: Restore failed: {e}\n")
        return False


def get_backup_content() -> Optional[str]:
    """
    Get the backed up source.py content for diff preview.

    Returns:
        Backup content, or None if no backup exists
    """
    return _source_backup


def clear_backup():
    """
    Clear backup after successful approve.

    Called when user approves preview - source.py is now the canonical version.
    """
    global _source_backup
    _source_backup = None
    FreeCAD.Console.PrintMessage("SourceManager: Cleared backup\n")


def has_backup() -> bool:
    """Check if there's an active backup."""
    return _source_backup is not None
