# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Context Builder - Gathers FreeCAD document state for AI context.
Provides detailed information about all objects to help AI understand existing designs.
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

    # Get all objects
    objects = doc.Objects
    if not objects:
        lines.append("\nDocument is empty - ready for new design.")
        return "\n".join(lines)

    # Categorize objects by type
    bodies = []
    part_primitives = []
    part_features = []
    sketches = []
    partdesign_features = []
    arch_structures = []
    arch_walls = []
    datums = []
    other_objects = []

    for obj in objects:
        category = _categorize_object_v2(obj)
        if category == "body":
            bodies.append(obj)
        elif category == "part_primitive":
            part_primitives.append(obj)
        elif category == "part_feature":
            part_features.append(obj)
        elif category == "sketch":
            sketches.append(obj)
        elif category == "partdesign_feature":
            partdesign_features.append(obj)
        elif category == "arch_structure":
            arch_structures.append(obj)
        elif category == "arch_wall":
            arch_walls.append(obj)
        elif category == "datum":
            datums.append(obj)
        else:
            other_objects.append(obj)

    # Summary
    lines.append(f"\n### Summary: {len(objects)} objects")
    summary_parts = []
    if bodies:
        summary_parts.append(f"{len(bodies)} bodies")
    if part_primitives:
        summary_parts.append(f"{len(part_primitives)} primitives")
    if sketches:
        summary_parts.append(f"{len(sketches)} sketches")
    if partdesign_features:
        summary_parts.append(f"{len(partdesign_features)} PartDesign features")
    if arch_structures:
        summary_parts.append(f"{len(arch_structures)} structures")
    if arch_walls:
        summary_parts.append(f"{len(arch_walls)} walls")
    if other_objects:
        summary_parts.append(f"{len(other_objects)} other")
    if summary_parts:
        lines.append(f"  {', '.join(summary_parts)}")

    # Bodies with their feature trees
    if bodies:
        lines.append("\n### Bodies:")
        for body in bodies[:5]:
            lines.append(_describe_body(body))
        if len(bodies) > 5:
            lines.append(f"  ... and {len(bodies) - 5} more bodies")

    # Part primitives (Box, Cylinder, Sphere, etc.)
    if part_primitives:
        lines.append("\n### Part Primitives:")
        for obj in part_primitives[:10]:
            lines.append(_describe_part_primitive(obj))
        if len(part_primitives) > 10:
            lines.append(f"  ... and {len(part_primitives) - 10} more primitives")

    # Part features (Boolean operations, etc.)
    if part_features:
        lines.append("\n### Part Features:")
        for obj in part_features[:5]:
            lines.append(_describe_part_feature(obj))
        if len(part_features) > 5:
            lines.append(f"  ... and {len(part_features) - 5} more features")

    # Sketches
    if sketches:
        lines.append("\n### Sketches:")
        for obj in sketches[:5]:
            lines.append(_describe_sketch(obj))
        if len(sketches) > 5:
            lines.append(f"  ... and {len(sketches) - 5} more sketches")

    # PartDesign features (standalone, not in bodies)
    standalone_pd = [f for f in partdesign_features if not _is_in_body(f)]
    if standalone_pd:
        lines.append("\n### PartDesign Features:")
        for obj in standalone_pd[:5]:
            lines.append(_describe_partdesign_feature(obj))

    # Arch structures
    if arch_structures:
        lines.append("\n### Architectural Structures:")
        for obj in arch_structures[:10]:
            lines.append(_describe_arch_structure(obj))
        if len(arch_structures) > 10:
            lines.append(f"  ... and {len(arch_structures) - 10} more structures")

    # Arch walls
    if arch_walls:
        lines.append("\n### Walls:")
        for obj in arch_walls[:10]:
            lines.append(_describe_arch_wall(obj))
        if len(arch_walls) > 10:
            lines.append(f"  ... and {len(arch_walls) - 10} more walls")

    # Other objects
    if other_objects:
        # Filter out origins and internal objects
        visible_other = [o for o in other_objects if not _is_internal_object(o)]
        if visible_other:
            lines.append("\n### Other Objects:")
            for obj in visible_other[:5]:
                lines.append(_describe_generic_object(obj))
            if len(visible_other) > 5:
                lines.append(f"  ... and {len(visible_other) - 5} more objects")

    # Selection info (important for context)
    try:
        selection = FreeCADGui.Selection.getSelection()
        if selection:
            lines.append(f"\n### Currently Selected:")
            for obj in selection[:3]:
                lines.append(f"  - {obj.Label} ({obj.TypeId})")
            if len(selection) > 3:
                lines.append(f"  ... and {len(selection) - 3} more selected")
    except Exception:
        pass

    return "\n".join(lines)


def _categorize_object_v2(obj) -> str:
    """Categorize object by its TypeId for comprehensive context."""
    type_id = obj.TypeId

    # Bodies
    if type_id == "PartDesign::Body":
        return "body"

    # Part primitives
    if type_id in ("Part::Box", "Part::Cylinder", "Part::Sphere", "Part::Cone",
                   "Part::Torus", "Part::Ellipsoid", "Part::Prism", "Part::Wedge",
                   "Part::Helix", "Part::Spiral"):
        return "part_primitive"

    # Part features (Boolean, etc.)
    if type_id.startswith("Part::") and type_id not in ("Part::Feature", "Part::Part2DObject"):
        if "Cut" in type_id or "Fuse" in type_id or "Common" in type_id:
            return "part_feature"
        if "Extrusion" in type_id or "Revolution" in type_id:
            return "part_feature"

    # Generic Part::Feature (could be anything with a shape)
    if type_id == "Part::Feature":
        return "part_primitive"

    # Sketches
    if type_id == "Sketcher::SketchObject":
        return "sketch"

    # PartDesign features
    if type_id.startswith("PartDesign::"):
        if type_id == "PartDesign::Body":
            return "body"
        return "partdesign_feature"

    # Arch structures
    if type_id == "Arch::Structure":
        return "arch_structure"

    # Arch walls
    if type_id == "Arch::Wall":
        return "arch_wall"

    # Datums
    if "Datum" in type_id or type_id in ("App::Plane", "App::Line", "App::Origin"):
        return "datum"

    return "other"


def _is_in_body(obj) -> bool:
    """Check if object is part of a Body."""
    try:
        parents = obj.InList
        for parent in parents:
            if parent.TypeId == "PartDesign::Body":
                return True
    except Exception:
        pass
    return False


def _is_internal_object(obj) -> bool:
    """Check if object is internal (Origin, planes, etc.)."""
    type_id = obj.TypeId
    if type_id in ("App::Origin", "App::Plane", "App::Line", "App::Point"):
        return True
    if "Origin" in obj.Label:
        return True
    return False


def _describe_body(body) -> str:
    """Describe a PartDesign Body with its feature tree."""
    lines = [f"  - {body.Label}"]

    try:
        # Get tip (active feature)
        if hasattr(body, "Tip") and body.Tip:
            lines[0] += f" (tip: {body.Tip.Label})"

        # List features in order
        if hasattr(body, "Group"):
            features = [f for f in body.Group if not _is_internal_object(f)]
            if features:
                for feat in features[:5]:
                    feat_desc = _describe_partdesign_feature(feat, indent=4)
                    lines.append(feat_desc)
                if len(features) > 5:
                    lines.append(f"      ... and {len(features) - 5} more features")

        # Shape info
        if hasattr(body, "Shape") and body.Shape.isValid():
            vol = body.Shape.Volume
            if vol > 0:
                lines.append(f"    Volume: {vol:.0f} mm³")
    except Exception:
        pass

    return "\n".join(lines)


def _describe_part_primitive(obj) -> str:
    """Describe a Part primitive with its specific parameters."""
    type_id = obj.TypeId
    parts = [f"  - {obj.Label}"]

    try:
        if type_id == "Part::Box":
            l = getattr(obj, "Length", None)
            w = getattr(obj, "Width", None)
            h = getattr(obj, "Height", None)
            if l and w and h:
                parts.append(f"Box [{l.Value:.0f} x {w.Value:.0f} x {h.Value:.0f} mm]")

        elif type_id == "Part::Cylinder":
            r = getattr(obj, "Radius", None)
            h = getattr(obj, "Height", None)
            if r and h:
                parts.append(f"Cylinder [r={r.Value:.0f}, h={h.Value:.0f} mm]")

        elif type_id == "Part::Sphere":
            r = getattr(obj, "Radius", None)
            if r:
                parts.append(f"Sphere [r={r.Value:.0f} mm]")

        elif type_id == "Part::Cone":
            r1 = getattr(obj, "Radius1", None)
            r2 = getattr(obj, "Radius2", None)
            h = getattr(obj, "Height", None)
            if r1 and r2 and h:
                parts.append(f"Cone [r1={r1.Value:.0f}, r2={r2.Value:.0f}, h={h.Value:.0f} mm]")

        elif type_id == "Part::Torus":
            r1 = getattr(obj, "Radius1", None)
            r2 = getattr(obj, "Radius2", None)
            if r1 and r2:
                parts.append(f"Torus [R={r1.Value:.0f}, r={r2.Value:.0f} mm]")

        elif type_id == "Part::Feature":
            # Generic feature - describe by shape
            if hasattr(obj, "Shape") and obj.Shape.isValid():
                bb = obj.Shape.BoundBox
                parts.append(f"Shape [{bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm]")

        else:
            parts.append(f"({type_id.split('::')[1]})")

        # Position
        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            if pos.x != 0 or pos.y != 0 or pos.z != 0:
                parts.append(f"at ({pos.x:.0f}, {pos.y:.0f}, {pos.z:.0f})")

    except Exception as e:
        parts.append(f"(error: {e})")

    return " ".join(parts)


def _describe_part_feature(obj) -> str:
    """Describe a Part feature (Boolean, extrusion, etc.)."""
    type_id = obj.TypeId
    parts = [f"  - {obj.Label}"]

    try:
        op_name = type_id.split("::")[-1]
        parts.append(f"({op_name})")

        # For Boolean operations, show operands
        if hasattr(obj, "Base") and obj.Base:
            parts.append(f"on {obj.Base.Label}")
        if hasattr(obj, "Tool") and obj.Tool:
            parts.append(f"with {obj.Tool.Label}")

    except Exception:
        pass

    return " ".join(parts)


def _describe_sketch(obj) -> str:
    """Describe a Sketch with geometry and constraint info."""
    parts = [f"  - {obj.Label}"]

    try:
        # Geometry count
        if hasattr(obj, "GeometryCount"):
            geom_count = obj.GeometryCount
        elif hasattr(obj, "Geometry"):
            geom_count = len(obj.Geometry)
        else:
            geom_count = 0

        # Constraint count
        if hasattr(obj, "ConstraintCount"):
            const_count = obj.ConstraintCount
        elif hasattr(obj, "Constraints"):
            const_count = len(obj.Constraints)
        else:
            const_count = 0

        parts.append(f"[{geom_count} geometry, {const_count} constraints]")

        # Fully constrained status
        if hasattr(obj, "FullyConstrained"):
            if obj.FullyConstrained:
                parts.append("(fully constrained)")
            else:
                # Get DoF if available
                try:
                    dof = obj.solve()
                    if dof > 0:
                        parts.append(f"({dof} DoF)")
                except Exception:
                    parts.append("(under-constrained)")

        # Support/attachment
        if hasattr(obj, "AttachmentSupport") and obj.AttachmentSupport:
            support = obj.AttachmentSupport
            if isinstance(support, tuple) and len(support) > 0:
                parts.append(f"on {support[0].Label}")

    except Exception:
        pass

    return " ".join(parts)


def _describe_partdesign_feature(obj, indent=2) -> str:
    """Describe a PartDesign feature with parameters."""
    prefix = " " * indent + "- "
    type_id = obj.TypeId
    parts = [f"{prefix}{obj.Label}"]

    try:
        feat_type = type_id.split("::")[-1]

        if feat_type == "Pad":
            length = getattr(obj, "Length", None)
            if length:
                parts.append(f"Pad [{length.Value:.0f} mm]")
            profile = getattr(obj, "Profile", None)
            if profile and hasattr(profile, "__len__") and len(profile) > 0:
                parts.append(f"from {profile[0].Label}")

        elif feat_type == "Pocket":
            length = getattr(obj, "Length", None)
            if length:
                parts.append(f"Pocket [{length.Value:.0f} mm]")

        elif feat_type == "Fillet":
            radius = getattr(obj, "Radius", None)
            if radius:
                parts.append(f"Fillet [r={radius.Value:.0f} mm]")

        elif feat_type == "Chamfer":
            size = getattr(obj, "Size", None)
            if size:
                parts.append(f"Chamfer [{size.Value:.0f} mm]")

        elif feat_type == "Revolution":
            angle = getattr(obj, "Angle", None)
            if angle:
                parts.append(f"Revolution [{angle.Value:.0f}°]")

        elif feat_type == "Hole":
            diameter = getattr(obj, "Diameter", None)
            depth = getattr(obj, "Depth", None)
            if diameter:
                parts.append(f"Hole [d={diameter.Value:.0f} mm]")

        elif feat_type in ("LinearPattern", "PolarPattern", "Mirrored"):
            occurrences = getattr(obj, "Occurrences", None)
            if occurrences:
                parts.append(f"{feat_type} [{occurrences} copies]")
            else:
                parts.append(f"({feat_type})")

        else:
            parts.append(f"({feat_type})")

    except Exception:
        pass

    return " ".join(parts)


def _describe_arch_structure(obj) -> str:
    """Describe an Arch Structure object with dimensions."""
    parts = [f"  - {obj.Label}"]

    try:
        # Determine type (column, beam, slab)
        struct_type = "Structure"
        if hasattr(obj, "IfcType") and obj.IfcType:
            struct_type = obj.IfcType

        dims = []
        if hasattr(obj, "Width") and obj.Width.Value > 0:
            dims.append(f"{obj.Width.Value:.0f}")
        if hasattr(obj, "Length") and obj.Length.Value > 0:
            dims.append(f"{obj.Length.Value:.0f}")
        if hasattr(obj, "Height") and obj.Height.Value > 0:
            dims.append(f"H={obj.Height.Value:.0f}")

        if dims:
            parts.append(f"{struct_type} [{' x '.join(dims)} mm]")
        else:
            parts.append(f"({struct_type})")

        # Position
        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            parts.append(f"at ({pos.x:.0f}, {pos.y:.0f}, {pos.z:.0f})")

    except Exception:
        pass

    return " ".join(parts)


def _describe_arch_wall(obj) -> str:
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
            parts.append(f"Wall [{', '.join(dims)} mm]")

        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            parts.append(f"at ({pos.x:.0f}, {pos.y:.0f}, {pos.z:.0f})")

    except Exception:
        pass

    return " ".join(parts)


def _describe_generic_object(obj) -> str:
    """Describe any FreeCAD object with available info."""
    parts = [f"  - {obj.Label}"]

    try:
        # Type
        type_name = obj.TypeId.split("::")[-1]
        parts.append(f"({type_name})")

        # Shape info if available
        if hasattr(obj, "Shape") and obj.Shape.isValid():
            bb = obj.Shape.BoundBox
            if bb.isValid():
                parts.append(f"[{bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm]")

        # Position if not at origin
        if hasattr(obj, "Placement"):
            pos = obj.Placement.Base
            if pos.x != 0 or pos.y != 0 or pos.z != 0:
                parts.append(f"at ({pos.x:.0f}, {pos.y:.0f}, {pos.z:.0f})")

    except Exception:
        pass

    return " ".join(parts)


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
