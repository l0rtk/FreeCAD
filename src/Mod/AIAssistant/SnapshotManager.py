# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Snapshot Manager - Captures comprehensive object state to JSON files and Python scripts.

Saves full object data to project folder on each AI request for future context enrichment.
Storage: .freecad_ai/snapshots/ next to the FreeCAD document.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import FreeCAD
import FreeCADGui


def get_snapshots_dir() -> Optional[Path]:
    """Get snapshots directory next to the active document."""
    try:
        doc = FreeCAD.ActiveDocument
        if doc and doc.FileName:
            doc_path = Path(doc.FileName)
            snapshots_dir = doc_path.parent / ".freecad_ai" / "snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            return snapshots_dir
    except Exception:
        pass
    # Fallback to global
    config_dir = Path(FreeCAD.getUserAppDataDir())
    snapshots_dir = config_dir / "AIAssistant" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return snapshots_dir


def _get_environment() -> Dict[str, Any]:
    """Capture FreeCAD environment info."""
    env = {}
    try:
        version = FreeCAD.Version()
        env["freecad_version"] = f"{version[0]}.{version[1]}.{version[2]}" if len(version) > 2 else f"{version[0]}.{version[1]}"
    except Exception:
        env["freecad_version"] = "unknown"

    try:
        wb = FreeCADGui.activeWorkbench()
        env["workbench"] = wb.name() if hasattr(wb, 'name') else str(type(wb).__name__).replace("Workbench", "")
    except Exception:
        env["workbench"] = "unknown"

    try:
        from FreeCAD import Units
        env["units"] = Units.getSchema()
    except Exception:
        env["units"] = "mm"

    return env


def _capture_placement(obj) -> Optional[Dict]:
    """Extract full placement data including 4x4 matrix."""
    if not hasattr(obj, "Placement"):
        return None

    pos = obj.Placement.Base
    rot = obj.Placement.Rotation
    matrix = obj.Placement.toMatrix()

    return {
        "position": {"x": pos.x, "y": pos.y, "z": pos.z},
        "rotation": {
            "axis": [rot.Axis.x, rot.Axis.y, rot.Axis.z],
            "angle": rot.Angle
        },
        "matrix": [
            [matrix.A11, matrix.A12, matrix.A13, matrix.A14],
            [matrix.A21, matrix.A22, matrix.A23, matrix.A24],
            [matrix.A31, matrix.A32, matrix.A33, matrix.A34],
            [matrix.A41, matrix.A42, matrix.A43, matrix.A44]
        ]
    }


def _capture_properties(obj) -> Dict[str, Any]:
    """Extract all typed properties with values and units."""
    props = {}

    for prop_name in obj.PropertiesList:
        try:
            prop_type = obj.getTypeIdOfProperty(prop_name)
            # Skip complex types that can't be easily serialized
            if not any(pt in prop_type for pt in ["Length", "Distance", "Angle", "Float", "Integer", "Bool", "String", "Vector", "Percent"]):
                continue

            val = getattr(obj, prop_name)

            # Handle different value types
            if hasattr(val, "Value"):  # PropertyLength, etc.
                props[prop_name] = {
                    "value": val.Value,
                    "unit": str(val.Unit) if hasattr(val, "Unit") else "mm",
                    "type": prop_type
                }
            elif isinstance(val, (int, float, bool, str)):
                props[prop_name] = {"value": val, "type": prop_type}
            elif hasattr(val, "x"):  # Vector
                props[prop_name] = {
                    "value": {"x": val.x, "y": val.y, "z": val.z},
                    "type": prop_type
                }
        except Exception:
            continue

    return props


def _capture_shape(obj, include_vertices: bool = True, include_brep: bool = False) -> Optional[Dict]:
    """Extract comprehensive shape data."""
    if not hasattr(obj, "Shape"):
        return None

    shape = obj.Shape
    if not shape or not hasattr(shape, "isValid") or not shape.isValid():
        return {"valid": False}

    bb = shape.BoundBox

    data = {
        "valid": True,
        "shape_type": shape.ShapeType,
        "bounding_box": {
            "min": [bb.XMin, bb.YMin, bb.ZMin],
            "max": [bb.XMax, bb.YMax, bb.ZMax],
            "size": [bb.XLength, bb.YLength, bb.ZLength]
        }
    }

    # Physical properties
    try:
        if shape.Volume > 0:
            data["volume_mm3"] = shape.Volume
    except Exception:
        pass

    try:
        if shape.Area > 0:
            data["surface_area_mm2"] = shape.Area
    except Exception:
        pass

    try:
        if hasattr(shape, "CenterOfMass"):
            com = shape.CenterOfMass
            data["center_of_mass"] = {"x": com.x, "y": com.y, "z": com.z}
    except Exception:
        pass

    # Topology counts
    try:
        data["topology"] = {
            "solids": len(shape.Solids) if hasattr(shape, "Solids") else 0,
            "shells": len(shape.Shells) if hasattr(shape, "Shells") else 0,
            "faces": len(shape.Faces) if hasattr(shape, "Faces") else 0,
            "edges": len(shape.Edges) if hasattr(shape, "Edges") else 0,
            "vertices": len(shape.Vertexes) if hasattr(shape, "Vertexes") else 0
        }
    except Exception:
        pass

    # Vertex coordinates (for reconstruction)
    if include_vertices:
        try:
            vertexes = shape.Vertexes if hasattr(shape, "Vertexes") else []
            if len(vertexes) <= 1000:  # Limit for large shapes
                data["vertices"] = [
                    {"x": v.Point.x, "y": v.Point.y, "z": v.Point.z}
                    for v in vertexes
                ]
        except Exception:
            pass

    # BREP export (optional - can be large)
    if include_brep:
        try:
            data["brep"] = shape.exportBrepToString()
        except Exception:
            pass

    return data


def _capture_sketch_data(obj) -> Optional[Dict]:
    """Extract sketch geometry and constraints."""
    if obj.TypeId != "Sketcher::SketchObject":
        return None

    data = {
        "geometry_count": obj.GeometryCount if hasattr(obj, "GeometryCount") else len(obj.Geometry) if hasattr(obj, "Geometry") else 0,
        "constraint_count": obj.ConstraintCount if hasattr(obj, "ConstraintCount") else len(obj.Constraints) if hasattr(obj, "Constraints") else 0,
        "fully_constrained": obj.FullyConstrained if hasattr(obj, "FullyConstrained") else False
    }

    # Extract geometry
    geometry = []
    try:
        for i, geom in enumerate(obj.Geometry):
            g = {"index": i, "type": type(geom).__name__}

            if hasattr(geom, "StartPoint") and hasattr(geom, "EndPoint"):
                g["start"] = [geom.StartPoint.x, geom.StartPoint.y]
                g["end"] = [geom.EndPoint.x, geom.EndPoint.y]
            if hasattr(geom, "Center"):
                g["center"] = [geom.Center.x, geom.Center.y]
            if hasattr(geom, "Radius"):
                g["radius"] = geom.Radius

            geometry.append(g)
    except Exception:
        pass
    data["geometry"] = geometry

    # Extract constraints
    constraints = []
    try:
        for c in obj.Constraints:
            constraint = {
                "type": c.Type,
                "name": c.Name if c.Name else None,
                "first": c.First
            }
            if hasattr(c, "Second") and c.Second >= 0:
                constraint["second"] = c.Second
            if c.Type in ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"):
                constraint["value"] = c.Value
            constraints.append(constraint)
    except Exception:
        pass
    data["constraints"] = constraints

    return data


def _capture_dependencies(obj) -> Dict:
    """Extract object dependencies."""
    deps = {"depends_on": [], "used_by": []}

    try:
        if hasattr(obj, "OutList") and obj.OutList:
            deps["depends_on"] = [o.Label for o in obj.OutList
                                   if o.TypeId not in ("App::Origin", "App::Plane", "App::Line")]
        if hasattr(obj, "InList") and obj.InList:
            deps["used_by"] = [o.Label for o in obj.InList
                               if o.TypeId not in ("App::Origin", "App::Plane", "App::Line")]
    except Exception:
        pass

    return deps


def capture_object_data(obj, include_brep: bool = False) -> Dict[str, Any]:
    """Extract comprehensive data from a single FreeCAD object."""
    data = {
        "name": obj.Name,
        "label": obj.Label,
        "type": obj.TypeId,
    }

    # Placement
    placement = _capture_placement(obj)
    if placement:
        data["placement"] = placement

    # Properties
    data["properties"] = _capture_properties(obj)

    # Shape
    shape = _capture_shape(obj, include_brep=include_brep)
    if shape:
        data["shape"] = shape

    # Sketch data (if applicable)
    sketch = _capture_sketch_data(obj)
    if sketch:
        data["sketch_data"] = sketch

    # Expressions
    if hasattr(obj, "ExpressionEngine") and obj.ExpressionEngine:
        data["expressions"] = [
            {"property": prop, "expression": expr}
            for prop, expr in obj.ExpressionEngine
        ]

    # Dependencies
    data["dependencies"] = _capture_dependencies(obj)

    return data


def _build_dependency_graph(objects) -> Dict:
    """Build a dependency tree from all objects."""
    graph = {"roots": [], "tree": {}}

    for obj in objects:
        if obj.TypeId in ("App::Origin", "App::Plane", "App::Line", "App::Point"):
            continue

        children = []
        try:
            if hasattr(obj, "OutList"):
                children = [o.Label for o in obj.OutList
                           if o.TypeId not in ("App::Origin", "App::Plane", "App::Line")]
        except Exception:
            pass

        if children:
            graph["tree"][obj.Label] = children

        # Find roots (objects with no parents)
        try:
            parents = [o for o in obj.InList
                      if o.TypeId not in ("App::Origin", "App::Plane", "App::Line")]
            if not parents:
                graph["roots"].append(obj.Label)
        except Exception:
            pass

    return graph


def _generate_python_script(snapshot: Dict) -> str:
    """Generate a Python script that can recreate the objects from the snapshot."""
    lines = [
        "# Auto-generated FreeCAD reconstruction script",
        f"# Generated: {snapshot['timestamp']}",
        f"# Document: {snapshot['document']['name']}",
        "#",
        "# Run this script in FreeCAD to recreate the objects.",
        "",
        "import FreeCAD",
        "import Part",
        "",
        "# Get or create document",
        f"doc_name = \"{snapshot['document']['name']}\"",
        "if FreeCAD.ActiveDocument is None:",
        "    doc = FreeCAD.newDocument(doc_name)",
        "else:",
        "    doc = FreeCAD.ActiveDocument",
        "",
    ]

    for obj_data in snapshot.get("objects", []):
        obj_name = obj_data["name"]
        obj_label = obj_data["label"]
        obj_type = obj_data["type"]

        lines.append(f"# --- {obj_label} ({obj_type}) ---")

        # Generate reconstruction based on object type
        if obj_type == "Part::Box":
            props = obj_data.get("properties", {})
            length = props.get("Length", {}).get("value", 10)
            width = props.get("Width", {}).get("value", 10)
            height = props.get("Height", {}).get("value", 10)
            lines.append(f"{obj_name} = doc.addObject('Part::Box', '{obj_name}')")
            lines.append(f"{obj_name}.Label = '{obj_label}'")
            lines.append(f"{obj_name}.Length = {length}")
            lines.append(f"{obj_name}.Width = {width}")
            lines.append(f"{obj_name}.Height = {height}")

        elif obj_type == "Part::Cylinder":
            props = obj_data.get("properties", {})
            radius = props.get("Radius", {}).get("value", 5)
            height = props.get("Height", {}).get("value", 10)
            lines.append(f"{obj_name} = doc.addObject('Part::Cylinder', '{obj_name}')")
            lines.append(f"{obj_name}.Label = '{obj_label}'")
            lines.append(f"{obj_name}.Radius = {radius}")
            lines.append(f"{obj_name}.Height = {height}")

        elif obj_type == "Part::Sphere":
            props = obj_data.get("properties", {})
            radius = props.get("Radius", {}).get("value", 5)
            lines.append(f"{obj_name} = doc.addObject('Part::Sphere', '{obj_name}')")
            lines.append(f"{obj_name}.Label = '{obj_label}'")
            lines.append(f"{obj_name}.Radius = {radius}")

        elif obj_type == "Part::Cone":
            props = obj_data.get("properties", {})
            radius1 = props.get("Radius1", {}).get("value", 5)
            radius2 = props.get("Radius2", {}).get("value", 0)
            height = props.get("Height", {}).get("value", 10)
            lines.append(f"{obj_name} = doc.addObject('Part::Cone', '{obj_name}')")
            lines.append(f"{obj_name}.Label = '{obj_label}'")
            lines.append(f"{obj_name}.Radius1 = {radius1}")
            lines.append(f"{obj_name}.Radius2 = {radius2}")
            lines.append(f"{obj_name}.Height = {height}")

        elif obj_type == "Part::Feature":
            # Generic Part::Feature - try to recreate from vertices or BREP
            shape_data = obj_data.get("shape", {})
            if shape_data.get("brep"):
                lines.append(f"# Recreate {obj_label} from BREP")
                lines.append(f"{obj_name}_shape = Part.Shape()")
                lines.append(f"{obj_name}_shape.importBrepFromString('''{shape_data['brep']}''')")
                lines.append(f"{obj_name} = doc.addObject('Part::Feature', '{obj_name}')")
                lines.append(f"{obj_name}.Label = '{obj_label}'")
                lines.append(f"{obj_name}.Shape = {obj_name}_shape")
            elif shape_data.get("vertices"):
                lines.append(f"# {obj_label} has {len(shape_data['vertices'])} vertices")
                lines.append(f"# Vertices stored but complex shape reconstruction not implemented")
                lines.append(f"# Use BREP data for exact reconstruction")
            else:
                lines.append(f"# {obj_label}: Complex Part::Feature - manual reconstruction needed")

        elif "Sketcher" in obj_type:
            sketch_data = obj_data.get("sketch_data", {})
            lines.append(f"# Sketch {obj_label}: {sketch_data.get('geometry_count', 0)} geometries, {sketch_data.get('constraint_count', 0)} constraints")
            lines.append(f"# Sketch reconstruction requires Sketcher module integration")

        else:
            lines.append(f"# {obj_label}: {obj_type} - type-specific reconstruction not implemented")

        # Add placement if present
        placement = obj_data.get("placement")
        if placement:
            pos = placement["position"]
            rot = placement["rotation"]
            lines.append(f"if hasattr({obj_name}, 'Placement'):")
            lines.append(f"    {obj_name}.Placement.Base = FreeCAD.Vector({pos['x']}, {pos['y']}, {pos['z']})")
            lines.append(f"    {obj_name}.Placement.Rotation = FreeCAD.Rotation(FreeCAD.Vector({rot['axis'][0]}, {rot['axis'][1]}, {rot['axis'][2]}), {rot['angle']})")

        lines.append("")

    lines.extend([
        "# Recompute document",
        "doc.recompute()",
        "",
        "print(f'Reconstructed {len(doc.Objects)} objects in {doc.Name}')",
    ])

    return "\n".join(lines)


def capture_current_state(include_brep: bool = False) -> Optional[Dict]:
    """Capture current document state as dict for change detection.

    This is an in-memory operation that does not save to disk.
    Use this for before/after comparison when executing code.

    Args:
        include_brep: Whether to include BREP data (usually False for change detection).

    Returns:
        Snapshot dictionary suitable for change detection, or None if no document.
    """
    doc = FreeCAD.ActiveDocument
    if not doc:
        return None

    # Collect all object data
    objects_data = []
    for obj in doc.Objects:
        if obj.TypeId in ("App::Origin", "App::Plane", "App::Line", "App::Point"):
            continue
        if "Origin" in obj.Label:
            continue

        try:
            objects_data.append(capture_object_data(obj, include_brep=include_brep))
        except Exception:
            continue

    return {
        "timestamp": datetime.now().isoformat(),
        "document": {
            "name": doc.Name,
            "filename": doc.FileName or "",
            "modified": doc.Modified if hasattr(doc, "Modified") else False
        },
        "environment": _get_environment(),
        "object_count": len(objects_data),
        "objects": objects_data,
        "dependency_graph": _build_dependency_graph(doc.Objects)
    }


def save_snapshot(timestamp: str = None, include_brep: bool = True) -> Optional[str]:
    """Save a comprehensive snapshot of all document objects.

    Args:
        timestamp: Optional timestamp string for the filename (matches session ID).
        include_brep: Whether to include BREP data for exact geometry reconstruction.

    Returns:
        Path to the saved JSON file, or None if failed.
    """
    snapshot = capture_current_state(include_brep=include_brep)
    if not snapshot:
        FreeCAD.Console.PrintWarning("AIAssistant: No active document for snapshot\n")
        return None

    snapshots_dir = get_snapshots_dir()
    if not snapshots_dir:
        FreeCAD.Console.PrintWarning("AIAssistant: Could not determine snapshots directory\n")
        return None

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Save JSON snapshot
    json_path = snapshots_dir / f"{timestamp}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        FreeCAD.Console.PrintMessage(f"AIAssistant: Snapshot saved to {json_path}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"AIAssistant: Failed to save snapshot JSON: {e}\n")
        return None

    # Generate and save Python reconstruction script
    py_path = snapshots_dir / f"{timestamp}_reconstruct.py"
    try:
        script = _generate_python_script(snapshot)
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(script)
        FreeCAD.Console.PrintMessage(f"AIAssistant: Reconstruction script saved to {py_path}\n")
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"AIAssistant: Failed to save reconstruction script: {e}\n")

    return str(json_path)


def load_snapshot(snapshot_path: str) -> Optional[Dict]:
    """Load a snapshot from a JSON file.

    Args:
        snapshot_path: Path to the snapshot JSON file.

    Returns:
        Snapshot dictionary, or None if failed.
    """
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        FreeCAD.Console.PrintError(f"AIAssistant: Failed to load snapshot: {e}\n")
        return None


def list_snapshots() -> List[Dict]:
    """List all available snapshots.

    Returns:
        List of snapshot summaries with timestamp, object_count, etc.
    """
    snapshots_dir = get_snapshots_dir()
    if not snapshots_dir:
        return []

    snapshots = []
    for json_file in sorted(snapshots_dir.glob("*.json"), reverse=True):
        # Skip non-snapshot files
        if "_reconstruct" in json_file.name:
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                snapshots.append({
                    "path": str(json_file),
                    "timestamp": data.get("timestamp", ""),
                    "document_name": data.get("document", {}).get("name", ""),
                    "object_count": data.get("object_count", 0),
                })
        except Exception:
            continue

    return snapshots
