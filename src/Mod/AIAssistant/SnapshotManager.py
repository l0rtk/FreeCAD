# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Snapshot Manager - Captures comprehensive object state to JSON files.

Saves full object data to project folder on each AI request for change detection.
Storage: {doc_stem}/.freecad_ai/snapshots/ in project subfolder.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import FreeCAD
import FreeCADGui


def get_snapshots_dir() -> Optional[Path]:
    """Get snapshots directory for the active document.

    Uses project subfolder: {doc_stem}/.freecad_ai/snapshots/
    """
    try:
        doc = FreeCAD.ActiveDocument
        if doc and doc.FileName:
            doc_path = Path(doc.FileName)
            # Create project subfolder: parent/doc_stem/.freecad_ai/snapshots/
            snapshots_dir = doc_path.parent / doc_path.stem / ".freecad_ai" / "snapshots"
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


def _get_next_counter(directory: Path, pattern: str = "*.json") -> int:
    """Get the next counter number based on existing files.

    Parses filenames like '001_...json' and returns max + 1.

    Args:
        directory: Directory to scan for existing files.
        pattern: Glob pattern to match files.

    Returns:
        Next counter number (starts at 1).
    """
    max_counter = 0
    for f in directory.glob(pattern):
        name = f.stem
        # Extract counter from start of filename (e.g., "001_2026-01-16")
        if "_" in name:
            try:
                counter = int(name.split("_")[0])
                max_counter = max(max_counter, counter)
            except ValueError:
                pass
    return max_counter + 1


def save_snapshot(include_brep: bool = True) -> tuple:
    """Save a comprehensive snapshot of all document objects.

    Uses counter-based naming: {counter:03d}_{date}_{time}.json
    Example: 001_2026-01-16_16-57.json

    Args:
        include_brep: Whether to include BREP data for exact geometry reconstruction.

    Returns:
        Tuple of (snapshot_id, path) or (None, None) if failed.
        snapshot_id is the filename without extension, used for session linking.
    """
    snapshot = capture_current_state(include_brep=include_brep)
    if not snapshot:
        FreeCAD.Console.PrintWarning("AIAssistant: No active document for snapshot\n")
        return (None, None)

    snapshots_dir = get_snapshots_dir()
    if not snapshots_dir:
        FreeCAD.Console.PrintWarning("AIAssistant: Could not determine snapshots directory\n")
        return (None, None)

    # Generate counter-based filename
    counter = _get_next_counter(snapshots_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    snapshot_id = f"{counter:03d}_{timestamp}"

    # Save JSON snapshot
    json_path = snapshots_dir / f"{snapshot_id}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        FreeCAD.Console.PrintMessage(f"AIAssistant: Snapshot saved to {json_path}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"AIAssistant: Failed to save snapshot JSON: {e}\n")
        return (None, None)

    return (snapshot_id, str(json_path))
