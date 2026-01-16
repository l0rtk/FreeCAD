# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Change Detector - Compares before/after snapshots to detect document changes.

Detects created, modified, and deleted objects by comparing two document snapshots.
Generates human-readable change descriptions for UI display.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class PropertyChange:
    """Single property change within an object."""
    property_name: str
    old_value: Any
    new_value: Any
    unit: str = ""

    def format_value(self, value: Any) -> str:
        """Format a property value for display."""
        if value is None:
            return "None"
        if isinstance(value, dict):
            if "x" in value and "y" in value and "z" in value:
                return f"({value['x']:.1f}, {value['y']:.1f}, {value['z']:.1f})"
            return str(value)
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def to_string(self) -> str:
        """Generate human-readable string for this change."""
        old_str = self.format_value(self.old_value)
        new_str = self.format_value(self.new_value)
        unit_str = f" {self.unit}" if self.unit else ""
        return f"{self.property_name}: {old_str}{unit_str} -> {new_str}{unit_str}"


@dataclass
class ObjectChange:
    """Change to a single object."""
    object_name: str
    object_label: str
    object_type: str
    change_type: str  # "created", "modified", "deleted"
    dimensions: Dict[str, float] = field(default_factory=dict)
    property_changes: List[PropertyChange] = field(default_factory=list)
    position: Optional[Dict[str, float]] = None

    def get_type_display(self) -> str:
        """Get clean type name for display."""
        type_map = {
            "Part::Box": "Box",
            "Part::Cylinder": "Cylinder",
            "Part::Sphere": "Sphere",
            "Part::Cone": "Cone",
            "Part::Torus": "Torus",
            "Part::Feature": "Shape",
            "Part::Cut": "Cut",
            "Part::Fuse": "Fusion",
            "Part::Common": "Intersection",
            "Part::Extrusion": "Extrusion",
            "Part::Revolution": "Revolution",
            "Sketcher::SketchObject": "Sketch",
            "PartDesign::Body": "Body",
            "PartDesign::Pad": "Pad",
            "PartDesign::Pocket": "Pocket",
            "PartDesign::Fillet": "Fillet",
            "PartDesign::Chamfer": "Chamfer",
            "Spreadsheet::Sheet": "Spreadsheet",
        }
        return type_map.get(self.object_type, self.object_type.split("::")[-1])

    def format_dimensions(self) -> str:
        """Format dimensions for display."""
        if not self.dimensions:
            return ""

        parts = []
        # Prioritize common dimension names
        for key in ["Length", "Width", "Height", "Radius", "Radius1", "Radius2", "Diameter"]:
            if key in self.dimensions:
                val = self.dimensions[key]
                if isinstance(val, (int, float)):
                    parts.append(f"{val:.1f}mm")

        if parts:
            return " x ".join(parts[:3])  # Max 3 dimensions

        # Fall back to any dimensions
        for key, val in list(self.dimensions.items())[:3]:
            if isinstance(val, (int, float)):
                parts.append(f"{key}: {val:.1f}mm")
        return ", ".join(parts)

    def to_string(self) -> str:
        """Generate human-readable string for this change."""
        label = self.object_label or self.object_name
        type_name = self.get_type_display()

        if self.change_type == "created":
            dims = self.format_dimensions()
            if dims:
                return f"Created {label} ({type_name}: {dims})"
            return f"Created {label} ({type_name})"

        elif self.change_type == "deleted":
            return f"Deleted {label} ({type_name})"

        elif self.change_type == "modified":
            if self.property_changes:
                changes_str = ", ".join(pc.to_string() for pc in self.property_changes[:3])
                return f"Modified {label}: {changes_str}"
            return f"Modified {label}"

        return f"{self.change_type}: {label}"


@dataclass
class ChangeSet:
    """Complete set of changes from code execution."""
    created: List[ObjectChange] = field(default_factory=list)
    modified: List[ObjectChange] = field(default_factory=list)
    deleted: List[ObjectChange] = field(default_factory=list)
    code: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_success: bool = True
    execution_message: str = ""

    def is_empty(self) -> bool:
        """Check if there are no changes."""
        return not self.created and not self.modified and not self.deleted

    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.created) + len(self.modified) + len(self.deleted)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "created": [
                {
                    "object_name": c.object_name,
                    "object_label": c.object_label,
                    "object_type": c.object_type,
                    "change_type": c.change_type,
                    "dimensions": c.dimensions,
                    "display_text": c.to_string(),
                }
                for c in self.created
            ],
            "modified": [
                {
                    "object_name": c.object_name,
                    "object_label": c.object_label,
                    "object_type": c.object_type,
                    "change_type": c.change_type,
                    "property_changes": [
                        {
                            "property_name": pc.property_name,
                            "old_value": pc.old_value,
                            "new_value": pc.new_value,
                            "unit": pc.unit,
                            "display_text": pc.to_string(),
                        }
                        for pc in c.property_changes
                    ],
                    "display_text": c.to_string(),
                }
                for c in self.modified
            ],
            "deleted": [
                {
                    "object_name": c.object_name,
                    "object_label": c.object_label,
                    "object_type": c.object_type,
                    "change_type": c.change_type,
                    "display_text": c.to_string(),
                }
                for c in self.deleted
            ],
            "code": self.code,
            "timestamp": self.timestamp,
            "execution_success": self.execution_success,
            "execution_message": self.execution_message,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChangeSet":
        """Create ChangeSet from dictionary."""
        change_set = cls(
            code=data.get("code", ""),
            timestamp=data.get("timestamp", ""),
            execution_success=data.get("execution_success", True),
            execution_message=data.get("execution_message", ""),
        )

        for c in data.get("created", []):
            change_set.created.append(ObjectChange(
                object_name=c.get("object_name", ""),
                object_label=c.get("object_label", ""),
                object_type=c.get("object_type", ""),
                change_type="created",
                dimensions=c.get("dimensions", {}),
            ))

        for c in data.get("modified", []):
            prop_changes = [
                PropertyChange(
                    property_name=pc.get("property_name", ""),
                    old_value=pc.get("old_value"),
                    new_value=pc.get("new_value"),
                    unit=pc.get("unit", ""),
                )
                for pc in c.get("property_changes", [])
            ]
            change_set.modified.append(ObjectChange(
                object_name=c.get("object_name", ""),
                object_label=c.get("object_label", ""),
                object_type=c.get("object_type", ""),
                change_type="modified",
                property_changes=prop_changes,
            ))

        for c in data.get("deleted", []):
            change_set.deleted.append(ObjectChange(
                object_name=c.get("object_name", ""),
                object_label=c.get("object_label", ""),
                object_type=c.get("object_type", ""),
                change_type="deleted",
            ))

        return change_set


def _extract_dimensions(obj_data: Dict) -> Dict[str, float]:
    """Extract key dimensions from object properties."""
    dimensions = {}
    props = obj_data.get("properties", {})

    # Priority dimension properties
    dim_props = ["Length", "Width", "Height", "Radius", "Radius1", "Radius2",
                 "Diameter", "Depth", "Size", "Angle1", "Angle2"]

    for prop in dim_props:
        if prop in props:
            prop_data = props[prop]
            if isinstance(prop_data, dict) and "value" in prop_data:
                dimensions[prop] = prop_data["value"]
            elif isinstance(prop_data, (int, float)):
                dimensions[prop] = prop_data

    # Also try shape bounding box if no explicit dimensions
    if not dimensions:
        shape = obj_data.get("shape", {})
        bb = shape.get("bounding_box", {})
        size = bb.get("size", [])
        if len(size) >= 3:
            dimensions["Length"] = size[0]
            dimensions["Width"] = size[1]
            dimensions["Height"] = size[2]

    return dimensions


def _get_property_value(prop_data: Any) -> Any:
    """Extract the actual value from property data."""
    if isinstance(prop_data, dict):
        return prop_data.get("value")
    return prop_data


def _get_property_unit(prop_data: Any) -> str:
    """Extract unit from property data."""
    if isinstance(prop_data, dict):
        unit = prop_data.get("unit", "")
        if unit and unit != "mm":
            return unit
        prop_type = prop_data.get("type", "")
        if "Length" in prop_type or "Distance" in prop_type:
            return "mm"
        if "Angle" in prop_type:
            return "deg"
    return ""


def _compare_properties(before_obj: Dict, after_obj: Dict) -> List[PropertyChange]:
    """Compare all properties between two object states."""
    changes = []
    before_props = before_obj.get("properties", {})
    after_props = after_obj.get("properties", {})

    # Properties to skip (internal or noisy)
    skip_props = {"Label", "Label2", "ExpressionEngine", "Proxy", "ViewObject"}

    # Check all properties in after state
    all_props = set(before_props.keys()) | set(after_props.keys())

    for prop_name in all_props:
        if prop_name in skip_props:
            continue

        before_data = before_props.get(prop_name)
        after_data = after_props.get(prop_name)

        before_val = _get_property_value(before_data)
        after_val = _get_property_value(after_data)

        # Compare values
        if before_val != after_val:
            # Skip if both None-ish
            if before_val is None and after_val is None:
                continue

            # Handle float comparison with tolerance
            if isinstance(before_val, float) and isinstance(after_val, float):
                if abs(before_val - after_val) < 0.001:
                    continue

            unit = _get_property_unit(after_data) or _get_property_unit(before_data)
            changes.append(PropertyChange(
                property_name=prop_name,
                old_value=before_val,
                new_value=after_val,
                unit=unit,
            ))

    # Check placement changes
    before_placement = before_obj.get("placement", {})
    after_placement = after_obj.get("placement", {})

    before_pos = before_placement.get("position", {})
    after_pos = after_placement.get("position", {})

    if before_pos and after_pos:
        pos_changed = False
        for axis in ["x", "y", "z"]:
            if abs(before_pos.get(axis, 0) - after_pos.get(axis, 0)) > 0.001:
                pos_changed = True
                break

        if pos_changed:
            changes.append(PropertyChange(
                property_name="Position",
                old_value=before_pos,
                new_value=after_pos,
                unit="mm",
            ))

    return changes


def _detect_created_objects(before: Optional[Dict], after: Optional[Dict]) -> List[ObjectChange]:
    """Find objects that exist in after but not in before."""
    created = []

    if after is None:
        return created

    before_names = set()
    if before:
        before_names = {obj["name"] for obj in before.get("objects", [])}

    for obj in after.get("objects", []):
        if obj["name"] not in before_names:
            created.append(ObjectChange(
                object_name=obj["name"],
                object_label=obj.get("label", obj["name"]),
                object_type=obj.get("type", "Unknown"),
                change_type="created",
                dimensions=_extract_dimensions(obj),
            ))

    return created


def _detect_deleted_objects(before: Optional[Dict], after: Optional[Dict]) -> List[ObjectChange]:
    """Find objects that exist in before but not in after."""
    deleted = []

    if before is None:
        return deleted

    after_names = set()
    if after:
        after_names = {obj["name"] for obj in after.get("objects", [])}

    for obj in before.get("objects", []):
        if obj["name"] not in after_names:
            deleted.append(ObjectChange(
                object_name=obj["name"],
                object_label=obj.get("label", obj["name"]),
                object_type=obj.get("type", "Unknown"),
                change_type="deleted",
            ))

    return deleted


def _detect_modified_objects(before: Optional[Dict], after: Optional[Dict]) -> List[ObjectChange]:
    """Find objects that exist in both but with different properties."""
    modified = []

    if before is None or after is None:
        return modified

    # Build lookup maps
    before_map = {obj["name"]: obj for obj in before.get("objects", [])}
    after_map = {obj["name"]: obj for obj in after.get("objects", [])}

    # Check objects that exist in both
    common_names = set(before_map.keys()) & set(after_map.keys())

    for name in common_names:
        before_obj = before_map[name]
        after_obj = after_map[name]

        property_changes = _compare_properties(before_obj, after_obj)

        if property_changes:
            modified.append(ObjectChange(
                object_name=name,
                object_label=after_obj.get("label", name),
                object_type=after_obj.get("type", "Unknown"),
                change_type="modified",
                property_changes=property_changes,
            ))

    return modified


def detect_changes(before: Optional[Dict], after: Optional[Dict], code: str = "") -> ChangeSet:
    """Compare two snapshots and return detected changes.

    Args:
        before: Snapshot dictionary before code execution (or None for new document).
        after: Snapshot dictionary after code execution (or None if document was closed).
        code: The executed code string (for reference).

    Returns:
        ChangeSet containing all detected changes.
    """
    return ChangeSet(
        created=_detect_created_objects(before, after),
        modified=_detect_modified_objects(before, after),
        deleted=_detect_deleted_objects(before, after),
        code=code,
    )


def format_change_summary(change_set: ChangeSet) -> str:
    """Generate a text summary of changes for display."""
    if change_set.is_empty():
        return "No changes detected"

    lines = []

    for change in change_set.created:
        lines.append(f"+ {change.to_string()}")

    for change in change_set.modified:
        lines.append(f"~ {change.to_string()}")

    for change in change_set.deleted:
        lines.append(f"- {change.to_string()}")

    return "\n".join(lines)
