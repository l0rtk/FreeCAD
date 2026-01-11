# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Context Builder - Gathers FreeCAD document state for AI context.
"""

import FreeCAD
import FreeCADGui


def build_context() -> str:
    """
    Build a context string describing the current FreeCAD state.
    This helps the AI understand what already exists in the document.

    Returns:
        A formatted string describing document objects and selection.
    """
    lines = []

    # Document info
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return "No active document. A new document will be created."

    lines.append(f"Document: {doc.Name}")

    # List objects
    objects = doc.Objects
    if not objects:
        lines.append("Document is empty.")
    else:
        lines.append(f"\nObjects ({len(objects)}):")
        for obj in objects[:15]:  # Limit to avoid huge context
            lines.append(_describe_object(obj))

        if len(objects) > 15:
            lines.append(f"  ... and {len(objects) - 15} more objects")

    # Selection info
    try:
        selection = FreeCADGui.Selection.getSelection()
        if selection:
            lines.append(f"\nSelected: {', '.join(o.Label for o in selection)}")
    except Exception:
        pass

    # Active workbench
    try:
        wb = FreeCADGui.activeWorkbench()
        if wb:
            lines.append(f"\nActive workbench: {wb.name()}")
    except Exception:
        pass

    return "\n".join(lines)


def _describe_object(obj) -> str:
    """Create a brief description of a FreeCAD object."""
    info = f"  - {obj.Label} ({obj.TypeId})"

    # Add bounding box info for shapes
    try:
        if hasattr(obj, "Shape") and hasattr(obj.Shape, "BoundBox"):
            bb = obj.Shape.BoundBox
            if bb.isValid():
                info += f" [{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm]"
    except Exception:
        pass

    # Add placement info
    try:
        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            if pos.Length > 0.1:  # Only show if not at origin
                info += f" at ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
    except Exception:
        pass

    return info


def get_selected_objects() -> list:
    """Get currently selected objects."""
    try:
        return FreeCADGui.Selection.getSelection()
    except Exception:
        return []


def get_selection_summary() -> str:
    """Get a summary of the current selection."""
    selected = get_selected_objects()
    if not selected:
        return "Nothing selected"

    return f"Selected: {', '.join(o.Label for o in selected)}"
