# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Parts Library - Scan and insert reusable parts for AI Assistant.

Provides access to the FreeCAD Parts Library addon, allowing the LLM
to discover and insert standard components by name.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional

import FreeCAD

# Supported file extensions for parts
SUPPORTED_EXTENSIONS = ('.fcstd', '.step', '.stp', '.brep', '.brp')

# Cache for library contents
_library_cache: Optional[List[Dict]] = None
_library_path_cache: Optional[str] = None


def get_library_path() -> Optional[str]:
    """
    Get the parts library path from FreeCAD preferences.

    Checks user preference first, then falls back to default addon location.

    Returns:
        Path to parts library directory, or None if not found
    """
    # Check user preference (set by parts_library addon)
    try:
        pr = FreeCAD.ParamGet("User parameter:Plugins/parts_library")
        path = pr.GetString("destination", "")
        if path and os.path.exists(path):
            return path
    except Exception:
        pass

    # Check default addon location
    default = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "parts_library")
    if os.path.exists(default):
        return default

    return None


def scan_library(force_refresh: bool = False) -> List[Dict]:
    """
    Scan the parts library and return list of available parts.

    Args:
        force_refresh: If True, rescan even if cached

    Returns:
        List of dicts with 'name', 'path', 'category', 'extension' for each part
    """
    global _library_cache, _library_path_cache

    lib_path = get_library_path()
    if not lib_path:
        return []

    # Use cache if valid
    if not force_refresh and _library_cache and _library_path_cache == lib_path:
        return _library_cache

    parts = []
    lib_root = Path(lib_path)

    try:
        for ext in SUPPORTED_EXTENSIONS:
            for file_path in lib_root.rglob(f"*{ext}"):
                # Get relative path for category
                rel_path = file_path.relative_to(lib_root)
                category = str(rel_path.parent) if rel_path.parent != Path(".") else ""

                parts.append({
                    "name": file_path.stem,
                    "path": str(file_path),
                    "extension": file_path.suffix.lower(),
                    "category": category,
                })
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"Parts library scan error: {e}\n")

    # Sort by category then name
    parts.sort(key=lambda p: (p["category"], p["name"]))

    _library_cache = parts
    _library_path_cache = lib_path

    return parts


def get_context() -> str:
    """
    Get parts library info formatted for LLM context.

    Returns:
        Formatted string describing available parts, or empty string if no library
    """
    parts = scan_library()
    if not parts:
        return ""

    lines = [f"\n### Parts Library ({len(parts)} parts available):"]

    # Group by category
    categories: Dict[str, List[str]] = {}
    for part in parts:
        cat = part["category"] or "Root"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(part["name"])

    # Show up to 30 parts total
    shown = 0
    for cat in sorted(categories.keys()):
        if shown >= 30:
            break

        names = categories[cat]
        if cat != "Root":
            lines.append(f"  {cat}/")

        for name in names[:5]:  # Max 5 per category
            prefix = "    " if cat != "Root" else "  "
            lines.append(f"{prefix}- {name}")
            shown += 1
            if shown >= 30:
                break

        if len(names) > 5:
            lines.append(f"    ... and {len(names) - 5} more")

    remaining = len(parts) - shown
    if remaining > 0:
        lines.append(f"  ... and {remaining} more parts")

    lines.append("\nTo insert a part: PartsLibrary.insert('part_name')")

    return "\n".join(lines)


def search(query: str) -> List[Dict]:
    """
    Search for parts matching a query.

    Args:
        query: Case-insensitive search string

    Returns:
        List of matching parts
    """
    query_lower = query.lower()
    return [p for p in scan_library() if query_lower in p["name"].lower()]


def insert(name_or_path: str) -> bool:
    """
    Insert a part from the library into the active document.

    Args:
        name_or_path: Part name (will search library) or full path

    Returns:
        True if successfully inserted
    """
    import FreeCADGui

    doc = FreeCAD.ActiveDocument
    if not doc:
        FreeCAD.Console.PrintError("PartsLibrary: No active document\n")
        return False

    # Find the part
    path = None
    if os.path.exists(name_or_path):
        path = name_or_path
    else:
        # Search library by name (case-insensitive)
        for part in scan_library():
            if part["name"].lower() == name_or_path.lower():
                path = part["path"]
                break

    if not path:
        FreeCAD.Console.PrintError(f"PartsLibrary: Part not found: {name_or_path}\n")
        return False

    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".fcstd":
            # Merge FreeCAD document
            FreeCADGui.ActiveDocument.mergeProject(path)
        elif ext in (".step", ".stp", ".brep", ".brp"):
            # Import STEP/BREP file
            import Part

            shape = Part.read(path)
            obj = doc.addObject("Part::Feature", Path(path).stem)
            obj.Shape = shape
            obj.Label = Path(path).stem
        else:
            FreeCAD.Console.PrintError(f"PartsLibrary: Unsupported format: {ext}\n")
            return False

        doc.recompute()
        FreeCAD.Console.PrintMessage(f"PartsLibrary: Inserted {Path(path).name}\n")
        return True

    except Exception as e:
        FreeCAD.Console.PrintError(f"PartsLibrary: Failed to insert: {e}\n")
        return False


def is_available() -> bool:
    """Check if parts library is installed and accessible."""
    return get_library_path() is not None
