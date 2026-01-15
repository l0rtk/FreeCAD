# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Context Builder - Gathers FreeCAD document state for AI context.
Provides detailed information about all objects to help AI understand existing designs.
"""

import FreeCAD
import FreeCADGui
from collections import deque
from . import SnapshotManager
from . import SourceManager
from . import PartsLibrary


# Global buffer for console messages (errors and warnings)
_console_buffer = deque(maxlen=50)  # Keep last 50 messages
_console_observer = None


class ConsoleObserver:
    """Observer that captures FreeCAD console messages."""

    def __init__(self, buffer):
        self._buffer = buffer

    def Error(self, msg):
        """Capture error messages."""
        self._buffer.append(("error", msg.strip()))

    def Warning(self, msg):
        """Capture warning messages."""
        self._buffer.append(("warning", msg.strip()))

    def Message(self, msg):
        """Capture regular messages (optional, filtered)."""
        # Only capture messages that might be useful (skip noise)
        msg_stripped = msg.strip()
        if msg_stripped and any(kw in msg_stripped.lower() for kw in
                                 ["failed", "invalid", "cannot", "error", "exception"]):
            self._buffer.append(("message", msg_stripped))

    def Log(self, msg):
        """Capture log messages (skip most, too verbose)."""
        pass


def start_console_observer():
    """Start capturing console messages.

    Note: FreeCAD's Console observer API is not available in Python,
    so this is currently a no-op. The buffer remains empty.
    """
    # FreeCAD.Console.AddObserver doesn't exist in Python API
    # This feature would require C++ implementation
    pass


def stop_console_observer():
    """Stop capturing console messages."""
    # No-op since observer couldn't be started
    pass


def get_console_buffer():
    """Get the current console buffer contents."""
    return list(_console_buffer)


def clear_console_buffer():
    """Clear the console buffer."""
    _console_buffer.clear()


# =============================================================================
# ENVIRONMENT CONTEXT - Application state beyond document objects
# =============================================================================

def _get_environment_context() -> str:
    """Get FreeCAD environment information.

    This provides context about the application state - what version,
    what workbench, what units - so AI can tailor suggestions appropriately.
    """
    lines = []

    try:
        # Version info
        version = FreeCAD.Version()
        if version and len(version) >= 2:
            ver_str = f"{version[0]}.{version[1]}"
            if len(version) > 2 and version[2]:
                ver_str += f".{version[2]}"
            lines.append(f"FreeCAD {ver_str}")
    except Exception:
        lines.append("FreeCAD (version unknown)")

    # Active workbench
    try:
        wb = FreeCADGui.activeWorkbench()
        if wb:
            wb_name = wb.name() if hasattr(wb, 'name') else str(type(wb).__name__)
            # Clean up workbench name
            wb_name = wb_name.replace("Workbench", "").strip()
            lines.append(f"Workbench: {wb_name}")
    except Exception:
        pass

    # Units system
    try:
        from FreeCAD import Units
        schema = Units.getSchema()
        decimals = Units.getDecimals()
        lines.append(f"Units: {schema} ({decimals} decimals)")
    except Exception:
        pass

    return " | ".join(lines) if lines else ""


def _get_open_documents() -> str:
    """Get list of open documents (beyond active one).

    Useful for AI to know what other documents are available for reference.
    """
    try:
        docs = FreeCAD.listDocuments()
        if len(docs) <= 1:
            return ""

        active_name = FreeCAD.ActiveDocument.Name if FreeCAD.ActiveDocument else None
        other_docs = [name for name in docs.keys() if name != active_name]

        if other_docs:
            return f"Other open documents: {', '.join(other_docs[:5])}"
    except Exception:
        pass
    return ""


def _get_workbench_tools() -> str:
    """Get available tools/features for the active workbench.

    This helps AI suggest operations that are actually available.
    """
    try:
        wb = FreeCADGui.activeWorkbench()
        if not wb:
            return ""

        wb_name = wb.name() if hasattr(wb, 'name') else ""

        # Map workbench to key capabilities
        capabilities = {
            "PartDesignWorkbench": "Pad, Pocket, Fillet, Chamfer, Revolution, Hole, Pattern",
            "PartWorkbench": "Box, Cylinder, Sphere, Cone, Boolean (Cut/Fuse/Common), Extrude",
            "SketcherWorkbench": "Line, Circle, Arc, Rectangle, Constraints, Dimensions",
            "DraftWorkbench": "Line, Wire, Circle, Rectangle, Polygon, BSpline, Text",
            "ArchWorkbench": "Wall, Structure, Window, Roof, Floor, Building",
            "TechDrawWorkbench": "Page, View, Dimension, Annotation",
            "SpreadsheetWorkbench": "Cell editing, Aliases, Formulas",
        }

        if wb_name in capabilities:
            return f"Available tools: {capabilities[wb_name]}"
    except Exception:
        pass
    return ""


def _get_selection_details() -> str:
    """Get detailed selection information including sub-elements.

    Goes beyond just object names - shows what faces, edges, vertices
    are selected, which is crucial for operations like Fillet, Chamfer.
    """
    try:
        sel_ex = FreeCADGui.Selection.getSelectionEx()
        if not sel_ex:
            return ""

        details = []
        for sel in sel_ex[:3]:  # Limit to first 3 selected objects
            obj_name = sel.Object.Label
            sub_elements = sel.SubElementNames

            if sub_elements:
                # Group by type (Face, Edge, Vertex)
                faces = [s for s in sub_elements if s.startswith("Face")]
                edges = [s for s in sub_elements if s.startswith("Edge")]
                vertices = [s for s in sub_elements if s.startswith("Vertex")]

                parts = [obj_name]
                if faces:
                    parts.append(f"{len(faces)} faces")
                if edges:
                    parts.append(f"{len(edges)} edges")
                if vertices:
                    parts.append(f"{len(vertices)} vertices")

                details.append(" → ".join(parts))
            else:
                details.append(f"{obj_name} (whole object)")

        if details:
            return "Selection: " + "; ".join(details)
    except Exception:
        pass
    return ""


def _get_import_export_formats() -> str:
    """Get supported import/export formats.

    Useful when user asks about file format compatibility.
    """
    try:
        # Common formats - don't need to enumerate all
        common_import = ["STEP", "IGES", "STL", "OBJ", "DXF", "SVG", "FCStd"]
        common_export = ["STEP", "IGES", "STL", "OBJ", "DXF", "SVG"]

        return f"Formats: Import ({', '.join(common_import)}), Export ({', '.join(common_export)})"
    except Exception:
        pass
    return ""


def build_context() -> str:
    """
    Build a detailed context string describing the current FreeCAD state.
    This helps the AI understand what already exists in the document.

    Returns:
        A formatted string describing document objects, organized by type.
    """
    lines = []

    # === ENVIRONMENT CONTEXT (always show) ===
    env_context = _get_environment_context()
    if env_context:
        lines.append(f"## Environment: {env_context}")

    # Available tools for current workbench
    tools = _get_workbench_tools()
    if tools:
        lines.append(tools)

    # Other open documents
    other_docs = _get_open_documents()
    if other_docs:
        lines.append(other_docs)

    lines.append("")  # Blank line before document section

    # Document info
    doc = FreeCAD.ActiveDocument
    if doc is None:
        lines.append("No active document. A new document will be created.")
        return "\n".join(lines)

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

    # Summary (brief counts - detailed info provided by comprehensive context below)
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

    # Selection info (important for context) - detailed with sub-elements
    selection_details = _get_selection_details()
    if selection_details:
        lines.append(f"\n### {selection_details}")
    else:
        # Fallback to basic selection
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

    # === NEW CONTEXT SOURCES ===

    # Expressions (parametric relationships - the "code" of CAD)
    expressions = _extract_expressions(objects)
    if expressions:
        lines.append(_describe_expressions(expressions))

    # Dependency graph (object relationships)
    dep_graph = _build_dependency_graph(objects)
    dep_desc = _describe_dependency_graph(dep_graph)
    if dep_desc:
        lines.append(dep_desc)

    # Spreadsheet parameters (named variables)
    spreadsheet_params = _extract_spreadsheet_params(objects)
    if spreadsheet_params:
        lines.append(_describe_spreadsheet_params(spreadsheet_params))

    # Detailed sketch constraints (only for selected or recent sketches)
    if sketches:
        constraint_details = []
        sketches_to_detail = sketches[:3]  # Only detail first 3 sketches
        for sketch in sketches_to_detail:
            constraint_str = _format_sketch_constraints(sketch)
            if constraint_str:
                constraint_details.append(f"  {sketch.Label}:\n{constraint_str}")

        if constraint_details:
            lines.append("\n### Sketch Constraint Details:")
            lines.extend(constraint_details)

    # Console errors (recent issues)
    console_errors = _get_console_errors()
    if console_errors:
        lines.append(_describe_console_errors(console_errors))

    # Comprehensive object data (geometry, volumes, topology from SnapshotManager)
    comprehensive_context = _get_comprehensive_object_context()
    if comprehensive_context:
        lines.append(comprehensive_context)

    # Source code history (how objects were created)
    source_context = SourceManager.get_context()
    if source_context:
        lines.append(source_context)

    # Parts library (available standard parts)
    parts_context = PartsLibrary.get_context()
    if parts_context:
        lines.append(parts_context)

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


def _extract_expressions(objects) -> list:
    """Extract expressions (parametric relationships) from all objects.

    Expressions are like "code" in CAD - they define how parameters depend on each other.
    Example: Box.Height = Spreadsheet.A1 * 2
    """
    expressions = []

    for obj in objects:
        try:
            # ExpressionEngine contains all expressions for an object
            if hasattr(obj, "ExpressionEngine") and obj.ExpressionEngine:
                for prop, expr in obj.ExpressionEngine:
                    expressions.append({
                        "object": obj.Label,
                        "property": prop,
                        "expression": expr
                    })
        except Exception:
            pass

    return expressions


def _describe_expressions(expressions) -> str:
    """Format expressions for context output."""
    if not expressions:
        return ""

    lines = ["\n### Expressions (Parametric Relationships):"]
    for expr in expressions[:15]:  # Limit to 15 expressions
        lines.append(f"  - {expr['object']}.{expr['property']} = {expr['expression']}")

    if len(expressions) > 15:
        lines.append(f"  ... and {len(expressions) - 15} more expressions")

    return "\n".join(lines)


def _describe_sketch_constraints_detailed(sketch) -> list:
    """Extract detailed constraint information from a sketch.

    Returns list of constraint descriptions showing design intent.
    """
    constraints = []

    try:
        if not hasattr(sketch, "Constraints"):
            return constraints

        for i, c in enumerate(sketch.Constraints):
            constraint_info = {
                "type": c.Type,
                "name": c.Name if c.Name else f"Constraint{i}",
            }

            # Add value for dimensional constraints
            if c.Type in ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"):
                constraint_info["value"] = c.Value

            # Add references
            if c.First >= 0:
                constraint_info["first"] = c.First
            if hasattr(c, "Second") and c.Second >= 0:
                constraint_info["second"] = c.Second

            constraints.append(constraint_info)

    except Exception:
        pass

    return constraints


def _format_sketch_constraints(sketch) -> str:
    """Format sketch constraints for context."""
    constraints = _describe_sketch_constraints_detailed(sketch)
    if not constraints:
        return ""

    lines = []

    # Group by type
    constraint_types = {}
    for c in constraints:
        ctype = c["type"]
        if ctype not in constraint_types:
            constraint_types[ctype] = []
        constraint_types[ctype].append(c)

    # Format
    for ctype, clist in constraint_types.items():
        if ctype in ("Distance", "DistanceX", "DistanceY"):
            values = [f"{c.get('value', 0):.1f}mm" for c in clist]
            lines.append(f"    {ctype}: {', '.join(values[:5])}")
        elif ctype in ("Radius", "Diameter"):
            values = [f"{c.get('value', 0):.1f}mm" for c in clist]
            lines.append(f"    {ctype}: {', '.join(values[:5])}")
        elif ctype == "Angle":
            values = [f"{c.get('value', 0):.1f}°" for c in clist]
            lines.append(f"    Angle: {', '.join(values[:5])}")
        else:
            # Geometric constraints (Horizontal, Vertical, Coincident, etc.)
            lines.append(f"    {ctype}: {len(clist)}")

    return "\n".join(lines)


def _build_dependency_graph(objects) -> dict:
    """Build dependency graph showing object relationships.

    InList = objects that depend on this object (downstream)
    OutList = objects this object depends on (upstream)
    """
    graph = {
        "dependencies": [],  # object -> depends on
        "dependents": []     # object -> used by
    }

    for obj in objects:
        try:
            # Skip internal objects
            if _is_internal_object(obj):
                continue

            # OutList: what does this object depend on?
            if hasattr(obj, "OutList") and obj.OutList:
                deps = [o.Label for o in obj.OutList if not _is_internal_object(o)]
                if deps:
                    graph["dependencies"].append({
                        "object": obj.Label,
                        "depends_on": deps
                    })

            # InList: what depends on this object?
            if hasattr(obj, "InList") and obj.InList:
                dependents = [o.Label for o in obj.InList if not _is_internal_object(o)]
                if dependents:
                    graph["dependents"].append({
                        "object": obj.Label,
                        "used_by": dependents
                    })

        except Exception:
            pass

    return graph


def _describe_dependency_graph(graph) -> str:
    """Format dependency graph for context."""
    if not graph["dependencies"] and not graph["dependents"]:
        return ""

    lines = ["\n### Dependencies:"]

    # Show key dependencies
    shown = set()
    for dep in graph["dependencies"][:10]:
        obj = dep["object"]
        deps = dep["depends_on"]
        if obj not in shown:
            lines.append(f"  - {obj} ← depends on: {', '.join(deps[:3])}")
            shown.add(obj)

    if len(graph["dependencies"]) > 10:
        lines.append(f"  ... and {len(graph['dependencies']) - 10} more dependency chains")

    return "\n".join(lines)


def _extract_spreadsheet_params(objects) -> list:
    """Extract named parameters from Spreadsheet objects.

    Spreadsheets are often used as parameter tables in parametric designs.
    """
    params = []

    for obj in objects:
        try:
            if obj.TypeId == "Spreadsheet::Sheet":
                # Get cells with aliases (named parameters)
                if hasattr(obj, "getCellFromAlias"):
                    # Try to get all aliases by checking common ranges
                    for row in range(1, 100):  # Check first 100 rows
                        for col_idx, col in enumerate("ABCDEFGH"):  # Check columns A-H
                            cell = f"{col}{row}"
                            try:
                                alias = obj.getAlias(cell)
                                if alias:
                                    value = obj.get(cell)
                                    params.append({
                                        "spreadsheet": obj.Label,
                                        "cell": cell,
                                        "alias": alias,
                                        "value": str(value) if value is not None else ""
                                    })
                            except Exception:
                                pass

                        # Stop if we've found enough or row is empty
                        if len(params) > 50:
                            break

        except Exception:
            pass

    return params


def _describe_spreadsheet_params(params) -> str:
    """Format spreadsheet parameters for context."""
    if not params:
        return ""

    lines = ["\n### Spreadsheet Parameters:"]

    # Group by spreadsheet
    by_sheet = {}
    for p in params:
        sheet = p["spreadsheet"]
        if sheet not in by_sheet:
            by_sheet[sheet] = []
        by_sheet[sheet].append(p)

    for sheet, sheet_params in by_sheet.items():
        lines.append(f"  {sheet}:")
        for p in sheet_params[:10]:
            lines.append(f"    - {p['alias']} = {p['value']} ({p['cell']})")
        if len(sheet_params) > 10:
            lines.append(f"    ... and {len(sheet_params) - 10} more parameters")

    return "\n".join(lines)


def _get_console_errors() -> list:
    """Get recent console errors and warnings.

    Useful for AI to understand what issues the user might be facing.
    Returns list of (type, message) tuples.
    """
    # Get messages from buffer, filter to errors and warnings
    buffer = get_console_buffer()

    # Only return errors and warnings, prioritize recent ones
    errors = [(t, m) for t, m in buffer if t in ("error", "warning")]

    # Return last 10 errors/warnings
    return errors[-10:] if len(errors) > 10 else errors


def _describe_console_errors(errors) -> str:
    """Format console errors for context."""
    if not errors:
        return ""

    lines = ["\n### Recent Console Issues:"]
    for err_type, msg in errors:
        prefix = "ERROR" if err_type == "error" else "WARN"
        # Truncate long messages
        display_msg = msg[:100] + "..." if len(msg) > 100 else msg
        lines.append(f"  [{prefix}] {display_msg}")

    return "\n".join(lines)


def _generate_reconstruction_code(obj, data: dict) -> str:
    """Generate concise Python code to recreate an object.

    Returns a one-liner that shows how the object could be created/modified.
    """
    type_id = obj.TypeId
    label = data.get('label', obj.Label)
    props = data.get('properties', {})

    # Arch Structure (columns, beams, slabs)
    if type_id == "Arch::Structure":
        length = props.get('Length', {}).get('value', 0)
        width = props.get('Width', {}).get('value', 0)
        height = props.get('Height', {}).get('value', 0)
        if length and width and height:
            pos = data.get('placement', {}).get('position', {})
            pos_str = ""
            if pos.get('x', 0) != 0 or pos.get('y', 0) != 0 or pos.get('z', 0) != 0:
                pos_str = f"; .Placement.Base=Vector({pos['x']:.0f},{pos['y']:.0f},{pos['z']:.0f})"
            return f"Arch.makeStructure(length={length:.0f}, width={width:.0f}, height={height:.0f}){pos_str}"

    # Part Box
    if type_id == "Part::Box":
        length = props.get('Length', {}).get('value', 0)
        width = props.get('Width', {}).get('value', 0)
        height = props.get('Height', {}).get('value', 0)
        if length and width and height:
            return f"Part.makeBox({length:.0f}, {width:.0f}, {height:.0f})"

    # Part Cylinder
    if type_id == "Part::Cylinder":
        radius = props.get('Radius', {}).get('value', 0)
        height = props.get('Height', {}).get('value', 0)
        if radius and height:
            return f"Part.makeCylinder({radius:.0f}, {height:.0f})"

    # Part Sphere
    if type_id == "Part::Sphere":
        radius = props.get('Radius', {}).get('value', 0)
        if radius:
            return f"Part.makeSphere({radius:.0f})"

    # Part Cone
    if type_id == "Part::Cone":
        radius1 = props.get('Radius1', {}).get('value', 0)
        radius2 = props.get('Radius2', {}).get('value', 0)
        height = props.get('Height', {}).get('value', 0)
        if height:
            return f"Part.makeCone({radius1:.0f}, {radius2:.0f}, {height:.0f})"

    # Part::Feature with simple vertices (custom shapes like pyramids)
    if type_id == "Part::Feature":
        shape = data.get('shape', {})
        verts = shape.get('vertices', [])
        topo = shape.get('topology', {})

        # Simple pyramid/tetrahedron detection (5 vertices, 5 faces)
        if len(verts) == 5 and topo.get('faces') == 5:
            # Find apex (highest Z) and base vertices
            sorted_verts = sorted(verts, key=lambda v: v['z'], reverse=True)
            apex = sorted_verts[0]
            base_verts = sorted_verts[1:]
            # Sort base vertices counterclockwise for proper polygon
            import math
            cx = sum(v['x'] for v in base_verts) / 4
            cy = sum(v['y'] for v in base_verts) / 4
            base_verts.sort(key=lambda v: math.atan2(v['y'] - cy, v['x'] - cx))
            # Generate executable Python code pattern
            base_pts = ", ".join([f"V({v['x']:.0f},{v['y']:.0f},{v['z']:.0f})" for v in base_verts])
            apex_pt = f"V({apex['x']:.0f},{apex['y']:.0f},{apex['z']:.0f})"
            return f"Pyramid(base=[{base_pts}], apex={apex_pt})"

        # Generic Part::Feature - show vertices for reconstruction
        if len(verts) <= 12:
            vert_str = ", ".join([f"V({v['x']:.0f},{v['y']:.0f},{v['z']:.0f})" for v in verts])
            return f"Part.Shape([{vert_str}])"

    # Arch Wall
    if type_id == "Arch::Wall":
        length = props.get('Length', {}).get('value', 0)
        width = props.get('Width', {}).get('value', 0)
        height = props.get('Height', {}).get('value', 0)
        if length and height:
            return f"Arch.makeWall(None, length={length:.0f}, width={width:.0f}, height={height:.0f})"

    return ""


def _get_comprehensive_object_context() -> str:
    """Get comprehensive object data from SnapshotManager for rich AI context.

    This provides detailed geometry data (positions, dimensions, volumes, topology)
    that helps the AI understand the exact state of all objects in the document.
    """
    doc = FreeCAD.ActiveDocument
    if not doc:
        return ""

    lines = ["\n### Comprehensive Object Data:"]

    for obj in doc.Objects:
        # Skip internal objects
        if obj.TypeId in ("App::Origin", "App::Plane", "App::Line", "App::Point"):
            continue
        if "Origin" in obj.Label:
            continue

        try:
            # Capture object data (without BREP to keep it concise)
            data = SnapshotManager.capture_object_data(obj, include_brep=False)

            # Format object header
            obj_line = f"  **{data['label']}** ({data['type'].split('::')[-1]})"

            # Position
            if 'placement' in data:
                pos = data['placement']['position']
                if pos['x'] != 0 or pos['y'] != 0 or pos['z'] != 0:
                    obj_line += f" at ({pos['x']:.0f}, {pos['y']:.0f}, {pos['z']:.0f})"

            lines.append(obj_line)

            # Shape data
            if 'shape' in data:
                shape = data['shape']
                shape_parts = []

                # Bounding box dimensions
                if 'bounding_box' in shape:
                    size = shape['bounding_box']['size']
                    shape_parts.append(f"Size: {size[0]:.0f}×{size[1]:.0f}×{size[2]:.0f}mm")

                # Volume
                if 'volume_mm3' in shape and shape['volume_mm3'] > 0:
                    vol = shape['volume_mm3']
                    if vol >= 1e9:
                        shape_parts.append(f"Vol: {vol/1e9:.1f}m³")
                    elif vol >= 1e6:
                        shape_parts.append(f"Vol: {vol/1e6:.1f}L")
                    else:
                        shape_parts.append(f"Vol: {vol:.0f}mm³")

                # Surface area
                if 'surface_area_mm2' in shape and shape['surface_area_mm2'] > 0:
                    area = shape['surface_area_mm2']
                    if area >= 1e6:
                        shape_parts.append(f"Area: {area/1e6:.2f}m²")
                    else:
                        shape_parts.append(f"Area: {area:.0f}mm²")

                # Center of mass
                if 'center_of_mass' in shape:
                    com = shape['center_of_mass']
                    shape_parts.append(f"CoM: ({com['x']:.0f}, {com['y']:.0f}, {com['z']:.0f})")

                # Topology
                if 'topology' in shape:
                    topo = shape['topology']
                    shape_parts.append(f"Topo: {topo['faces']}F/{topo['edges']}E/{topo['vertices']}V")

                if shape_parts:
                    lines.append(f"    {' | '.join(shape_parts)}")

                # Vertex coordinates (for simple objects - enables AI to understand exact geometry)
                if 'vertices' in shape and len(shape['vertices']) <= 50:
                    verts = shape['vertices']
                    # Format compactly: [(x,y,z), ...]
                    vert_strs = [f"({v['x']:.0f},{v['y']:.0f},{v['z']:.0f})" for v in verts]
                    lines.append(f"    Vertices: [{', '.join(vert_strs)}]")

            # Key dimensional properties
            if 'properties' in data:
                props = data['properties']
                dim_props = []
                for name in ['Length', 'Width', 'Height', 'Radius', 'Diameter']:
                    if name in props and 'value' in props[name]:
                        val = props[name]['value']
                        if val > 0:
                            dim_props.append(f"{name}={val:.0f}mm")

                if dim_props:
                    lines.append(f"    Props: {', '.join(dim_props)}")

            # Sketch geometry (for Sketcher objects - enables AI to understand 2D profiles)
            if 'sketch_data' in data:
                sketch = data['sketch_data']
                sketch_info = f"Geometry: {sketch.get('geometry_count', 0)}, Constraints: {sketch.get('constraint_count', 0)}"
                if sketch.get('fully_constrained'):
                    sketch_info += " (fully constrained)"
                lines.append(f"    {sketch_info}")

                # Include geometry details for simple sketches
                if 'geometry' in sketch and len(sketch['geometry']) <= 20:
                    geom_strs = []
                    for g in sketch['geometry']:
                        g_type = g.get('type', 'Unknown')
                        if 'start' in g and 'end' in g:
                            geom_strs.append(f"{g_type}({g['start'][0]:.0f},{g['start'][1]:.0f})->({g['end'][0]:.0f},{g['end'][1]:.0f})")
                        elif 'center' in g and 'radius' in g:
                            geom_strs.append(f"{g_type}@({g['center'][0]:.0f},{g['center'][1]:.0f}) r={g['radius']:.0f}")
                        else:
                            geom_strs.append(g_type)
                    if geom_strs:
                        lines.append(f"    Sketch: [{', '.join(geom_strs)}]")

            # Dependencies
            if 'dependencies' in data:
                deps = data['dependencies']
                if deps['depends_on']:
                    lines.append(f"    Depends on: {', '.join(deps['depends_on'][:3])}")
                if deps['used_by']:
                    lines.append(f"    Used by: {', '.join(deps['used_by'][:3])}")

            # Python reconstruction code (helps AI understand how to modify/recreate)
            py_code = _generate_reconstruction_code(obj, data)
            if py_code:
                lines.append(f"    Code: `{py_code}`")

        except Exception as e:
            # Skip objects that fail to capture
            continue

    if len(lines) == 1:
        return ""  # No objects captured

    return "\n".join(lines)


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
