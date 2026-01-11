# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Context Builder - Gathers FreeCAD document state for AI context.
Provides detailed structural information to help AI understand existing designs.
"""

import FreeCAD
import FreeCADGui


def build_context() -> str:
    """
    Build a detailed context string describing the current FreeCAD state.
    This helps the AI understand what already exists in the document.

    Returns:
        A formatted string describing document objects, organized by type.
    """
    lines = []

    # Document info
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return "No active document. A new document will be created."

    lines.append(f"## Document: {doc.Name}")

    # Categorize objects by structural type
    objects = doc.Objects
    if not objects:
        lines.append("\nDocument is empty - ready for new design.")
        return "\n".join(lines)

    # Sort objects into categories
    columns = []
    beams = []
    slabs = []
    walls = []
    other_structures = []
    other_objects = []

    for obj in objects:
        category = _categorize_object(obj)
        if category == "column":
            columns.append(obj)
        elif category == "beam":
            beams.append(obj)
        elif category == "slab":
            slabs.append(obj)
        elif category == "wall":
            walls.append(obj)
        elif category == "structure":
            other_structures.append(obj)
        else:
            other_objects.append(obj)

    # Summary
    lines.append(f"\n### Summary: {len(objects)} objects")
    summary_parts = []
    if columns:
        summary_parts.append(f"{len(columns)} columns")
    if beams:
        summary_parts.append(f"{len(beams)} beams")
    if slabs:
        summary_parts.append(f"{len(slabs)} slabs")
    if walls:
        summary_parts.append(f"{len(walls)} walls")
    if other_structures:
        summary_parts.append(f"{len(other_structures)} other structures")
    if other_objects:
        summary_parts.append(f"{len(other_objects)} other")
    if summary_parts:
        lines.append(f"  {', '.join(summary_parts)}")

    # Detail each category
    if columns:
        lines.append("\n### Columns:")
        for obj in columns[:10]:
            lines.append(_describe_structure(obj))
        if len(columns) > 10:
            lines.append(f"  ... and {len(columns) - 10} more columns")

    if beams:
        lines.append("\n### Beams:")
        for obj in beams[:10]:
            lines.append(_describe_structure(obj))
        if len(beams) > 10:
            lines.append(f"  ... and {len(beams) - 10} more beams")

    if slabs:
        lines.append("\n### Slabs:")
        for obj in slabs[:10]:
            lines.append(_describe_structure(obj))
        if len(slabs) > 10:
            lines.append(f"  ... and {len(slabs) - 10} more slabs")

    if walls:
        lines.append("\n### Walls:")
        for obj in walls[:10]:
            lines.append(_describe_wall(obj))
        if len(walls) > 10:
            lines.append(f"  ... and {len(walls) - 10} more walls")

    if other_structures:
        lines.append("\n### Other Structures:")
        for obj in other_structures[:5]:
            lines.append(_describe_structure(obj))

    if other_objects:
        lines.append("\n### Other Objects:")
        for obj in other_objects[:5]:
            lines.append(_describe_object(obj))
        if len(other_objects) > 5:
            lines.append(f"  ... and {len(other_objects) - 5} more objects")

    # Grid analysis
    grid_info = _analyze_grid(columns)
    if grid_info:
        lines.append(f"\n### Grid Layout:")
        lines.append(f"  {grid_info}")

    # Selection info
    try:
        selection = FreeCADGui.Selection.getSelection()
        if selection:
            lines.append(f"\n### Selected: {', '.join(o.Label for o in selection)}")
    except Exception:
        pass

    return "\n".join(lines)


def _categorize_object(obj) -> str:
    """Determine the structural category of an object."""
    # Check IfcType first (most reliable for Arch objects)
    if hasattr(obj, "IfcType"):
        ifc = obj.IfcType.lower() if obj.IfcType else ""
        if "column" in ifc:
            return "column"
        elif "beam" in ifc:
            return "beam"
        elif "slab" in ifc or "floor" in ifc or "roof" in ifc:
            return "slab"
        elif "wall" in ifc:
            return "wall"

    # Check TypeId
    type_id = obj.TypeId.lower()
    if "wall" in type_id:
        return "wall"
    if "structure" in type_id:
        # Infer from dimensions: height > length = column, else beam
        try:
            if hasattr(obj, "Height") and hasattr(obj, "Length"):
                h = obj.Height.Value
                l = obj.Length.Value
                if h > l:
                    return "column"
                else:
                    return "beam"
        except Exception:
            pass
        return "structure"

    # Check label for hints
    label = obj.Label.lower()
    if "column" in label or "col_" in label:
        return "column"
    elif "beam" in label:
        return "beam"
    elif "slab" in label:
        return "slab"
    elif "wall" in label:
        return "wall"

    return "other"


def _describe_structure(obj) -> str:
    """Describe an Arch Structure object with dimensions."""
    parts = [f"  - {obj.Label}"]

    # Get dimensions
    dims = []
    try:
        if hasattr(obj, "Width") and obj.Width.Value > 0:
            dims.append(f"{obj.Width.Value:.0f}")
        if hasattr(obj, "Length") and obj.Length.Value > 0:
            # For columns, Length is often the "depth"
            dims.append(f"{obj.Length.Value:.0f}")
        if hasattr(obj, "Height") and obj.Height.Value > 0:
            dims.append(f"H={obj.Height.Value:.0f}")
    except Exception:
        pass

    if dims:
        parts.append(f"[{' x '.join(dims)} mm]")

    # Position
    try:
        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            parts.append(f"at ({pos.x:.0f}, {pos.y:.0f}, {pos.z:.0f})")
    except Exception:
        pass

    return " ".join(parts)


def _describe_wall(obj) -> str:
    """Describe an Arch Wall object."""
    parts = [f"  - {obj.Label}"]

    try:
        dims = []
        if hasattr(obj, "Length") and obj.Length.Value > 0:
            dims.append(f"L={obj.Length.Value:.0f}")
        if hasattr(obj, "Width") and obj.Width.Value > 0:
            dims.append(f"W={obj.Width.Value:.0f}")
        if hasattr(obj, "Height") and obj.Height.Value > 0:
            dims.append(f"H={obj.Height.Value:.0f}")
        if dims:
            parts.append(f"[{', '.join(dims)} mm]")
    except Exception:
        pass

    try:
        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            parts.append(f"at ({pos.x:.0f}, {pos.y:.0f}, {pos.z:.0f})")
    except Exception:
        pass

    return " ".join(parts)


def _describe_object(obj) -> str:
    """Create a brief description of any FreeCAD object."""
    info = f"  - {obj.Label} ({obj.TypeId})"

    # Add bounding box info for shapes
    try:
        if hasattr(obj, "Shape") and hasattr(obj.Shape, "BoundBox"):
            bb = obj.Shape.BoundBox
            if bb.isValid():
                info += f" [{bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm]"
    except Exception:
        pass

    return info


def _analyze_grid(columns: list) -> str:
    """Analyze column positions to detect grid pattern."""
    if len(columns) < 2:
        return ""

    try:
        # Collect X and Y positions
        x_positions = set()
        y_positions = set()

        for col in columns:
            if hasattr(col, "Placement"):
                pos = col.Placement.Base
                # Round to nearest 100mm to group similar positions
                x_positions.add(round(pos.x / 100) * 100)
                y_positions.add(round(pos.y / 100) * 100)

        x_sorted = sorted(x_positions)
        y_sorted = sorted(y_positions)

        if len(x_sorted) >= 2 and len(y_sorted) >= 2:
            # Calculate typical spacing
            x_spacing = x_sorted[1] - x_sorted[0] if len(x_sorted) > 1 else 0
            y_spacing = y_sorted[1] - y_sorted[0] if len(y_sorted) > 1 else 0

            return (
                f"{len(x_sorted)}x{len(y_sorted)} grid, "
                f"spacing ~{x_spacing:.0f} x {y_spacing:.0f} mm"
            )
    except Exception:
        pass

    return ""


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
