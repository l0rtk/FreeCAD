# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Preview Manager - Manages 3D preview of objects before actual execution.

Executes code in a temporary document and shows preview objects as
green transparent shapes in the main document. User can approve or cancel.

For deletion operations, highlights target objects in red instead of sandbox.
"""

import re
import FreeCAD
import FreeCADGui
import Part
from typing import List, Dict, Optional, Tuple

# Preview styling for creation
PREVIEW_COLOR = (0.1, 0.9, 0.3)  # Green
PREVIEW_TRANSPARENCY = 70  # 70% transparent

# Preview styling for deletion
DELETION_COLOR = (0.9, 0.2, 0.2)  # Red
DELETION_TRANSPARENCY = 50  # 50% transparent

# Patterns that indicate deletion operations
_DELETION_PATTERNS = [
    r'\.removeObject\s*\(\s*["\'](\w+)["\']\s*\)',  # doc.removeObject('Name')
    r'\.removeObjectsFromDocument\s*\(',             # bulk removal
]


class PreviewManager:
    """Manages preview objects before actual execution.

    Workflow:
    1. create_preview(code) - Execute in temp doc, show green preview
    2. User sees preview in 3D view
    3. approve() or cancel() - Clear preview, optionally execute for real
    """

    def __init__(self):
        self._preview_objects: List[str] = []  # Names of preview objects in main doc
        self._temp_doc = None
        self._main_doc_name: Optional[str] = None
        self._pending_code: str = ""

        # Deletion preview state
        self._is_deletion: bool = False
        self._deletion_targets: List[str] = []  # Object names to be deleted
        self._deletion_originals: Dict[str, Dict] = {}  # Original appearance to restore

    def create_preview(self, code: str) -> tuple:
        """Create preview - route to deletion or creation path.

        For deletion operations (code contains removeObject), highlights
        target objects in red. For creation, executes in sandbox and
        shows green transparent preview.

        Args:
            code: Python code to execute

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        main_doc = FreeCAD.ActiveDocument
        if not main_doc:
            FreeCAD.Console.PrintWarning("AIAssistant: No active document for preview\n")
            return (False, "No active document")

        self._main_doc_name = main_doc.Name
        self._pending_code = code

        # Clear any existing preview
        self.clear_preview()

        # Check if this is a deletion operation
        deletion_targets = self._detect_deletion_targets(code)

        if deletion_targets:
            # Deletion path - red highlight on existing objects
            self._is_deletion = True
            return self._create_deletion_preview(deletion_targets)
        else:
            # Creation path - sandbox execution
            self._is_deletion = False
            return self._create_sandbox_preview(code)

    def _detect_deletion_targets(self, code: str) -> List[str]:
        """Parse code to find objects targeted for deletion.

        Args:
            code: Python code to analyze

        Returns:
            List of object names to be deleted, or empty if not deletion
        """
        targets = []
        for pattern in _DELETION_PATTERNS:
            matches = re.findall(pattern, code)
            if matches:
                FreeCAD.Console.PrintMessage(
                    f"AIAssistant: Pattern '{pattern}' matched: {matches}\n"
                )
            targets.extend(matches)
        result = list(set(targets))  # dedupe
        if result:
            FreeCAD.Console.PrintMessage(
                f"AIAssistant: Detected deletion targets: {result}\n"
            )
        return result

    def _create_deletion_preview(self, target_names: List[str]) -> tuple:
        """Create deletion preview by highlighting target objects in red.

        Args:
            target_names: Object names to be deleted

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        doc = FreeCAD.ActiveDocument
        if not doc:
            return (False, "No active document")

        found = []
        not_found = []

        for name in target_names:
            obj = doc.getObject(name)
            if obj and hasattr(obj, 'ViewObject') and obj.ViewObject:
                # Store original appearance
                vo = obj.ViewObject
                self._deletion_originals[name] = {
                    'color': vo.ShapeColor if hasattr(vo, 'ShapeColor') else None,
                    'transparency': vo.Transparency if hasattr(vo, 'Transparency') else None,
                    'line_color': vo.LineColor if hasattr(vo, 'LineColor') else None,
                }
                # Apply red highlight
                if hasattr(vo, 'ShapeColor'):
                    vo.ShapeColor = DELETION_COLOR
                if hasattr(vo, 'Transparency'):
                    vo.Transparency = DELETION_TRANSPARENCY
                if hasattr(vo, 'LineColor'):
                    vo.LineColor = (0.7, 0.1, 0.1)  # Dark red edges
                found.append(name)
            else:
                not_found.append(name)

        self._deletion_targets = found

        if not found:
            msg = f"Objects not found: {', '.join(not_found)}"
            FreeCAD.Console.PrintWarning(f"AIAssistant: {msg}\n")
            return (False, msg)

        FreeCAD.Console.PrintMessage(
            f"AIAssistant: Created deletion preview for {len(found)} objects\n"
        )

        if not_found:
            # Partial success - some objects found, some not
            FreeCAD.Console.PrintWarning(
                f"AIAssistant: Objects not found: {', '.join(not_found)}\n"
            )

        return (True, "")

    def _create_sandbox_preview(self, code: str) -> tuple:
        """Execute code in temp doc and show preview in main doc.

        This is the original creation preview path.

        Args:
            code: Python code to execute

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Create temporary document
        try:
            self._temp_doc = FreeCAD.newDocument("__AIPreview__", hidden=True)
        except TypeError:
            # Older FreeCAD versions may not support hidden parameter
            self._temp_doc = FreeCAD.newDocument("__AIPreview__")

        try:
            # Build execution environment for temp doc
            exec_globals = {
                'FreeCAD': FreeCAD,
                'Part': Part,
                'doc': self._temp_doc,
            }

            # Add common imports
            try:
                import Draft
                exec_globals['Draft'] = Draft
            except ImportError:
                pass

            try:
                import Arch
                exec_globals['Arch'] = Arch
            except ImportError:
                pass

            # Execute code in temp doc
            # Temporarily set temp doc as active
            FreeCAD.setActiveDocument(self._temp_doc.Name)

            try:
                exec(code, exec_globals)
                self._temp_doc.recompute()
            finally:
                # ALWAYS restore original active document, even on failure
                if self._main_doc_name and FreeCAD.getDocument(self._main_doc_name):
                    FreeCAD.setActiveDocument(self._main_doc_name)

            main_doc = FreeCAD.ActiveDocument

            # Copy shapes to main doc as preview
            preview_count = 0
            for obj in self._temp_doc.Objects:
                # Skip origin objects
                if obj.TypeId in ("App::Origin", "App::Plane", "App::Line"):
                    continue

                if hasattr(obj, 'Shape') and obj.Shape and not obj.Shape.isNull():
                    self._add_preview_shape(main_doc, obj)
                    preview_count += 1

            main_doc.recompute()

            # Fit view to show preview
            try:
                if FreeCADGui.ActiveDocument and FreeCADGui.ActiveDocument.ActiveView:
                    FreeCADGui.ActiveDocument.ActiveView.fitAll()
            except Exception:
                pass

            FreeCAD.Console.PrintMessage(f"AIAssistant: Created preview with {preview_count} objects\n")

            if preview_count > 0:
                return (True, "")
            else:
                return (False, "No preview objects created - code may not produce visible geometry")

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            FreeCAD.Console.PrintError(f"AIAssistant: Preview failed: {e}\n")
            self.clear_preview()
            return (False, error_msg)

    def _add_preview_shape(self, doc, source_obj):
        """Add a preview shape to main document.

        Args:
            doc: Target document (main doc)
            source_obj: Source object from temp doc
        """
        try:
            preview_name = f"__preview_{source_obj.Name}"
            preview = doc.addObject("Part::Feature", preview_name)
            preview.Shape = source_obj.Shape.copy()
            preview.Label = f"[Preview] {source_obj.Label}"

            # Style as green transparent
            if hasattr(preview, 'ViewObject') and preview.ViewObject:
                preview.ViewObject.ShapeColor = PREVIEW_COLOR
                preview.ViewObject.Transparency = PREVIEW_TRANSPARENCY
                preview.ViewObject.DisplayMode = "Shaded"
                # Make slightly darker line color for edges
                preview.ViewObject.LineColor = (0.0, 0.7, 0.2)

            self._preview_objects.append(preview_name)

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"AIAssistant: Failed to add preview for {source_obj.Name}: {e}\n")

    def clear_preview(self):
        """Remove all preview objects and restore deletion highlights."""
        # Clear creation preview objects
        if self._main_doc_name:
            try:
                doc = FreeCAD.getDocument(self._main_doc_name)
                if doc:
                    for name in self._preview_objects:
                        if doc.getObject(name):
                            doc.removeObject(name)
                    doc.recompute()
            except Exception as e:
                FreeCAD.Console.PrintWarning(f"AIAssistant: Error clearing preview: {e}\n")

        self._preview_objects = []

        # Clear deletion preview (restore original appearance)
        self._clear_deletion_preview()

        # Close temp document
        if self._temp_doc:
            try:
                FreeCAD.closeDocument(self._temp_doc.Name)
            except Exception:
                pass
            self._temp_doc = None

    def _clear_deletion_preview(self):
        """Restore original appearance of deletion-highlighted objects."""
        doc = FreeCAD.ActiveDocument
        if not doc:
            self._deletion_originals = {}
            self._deletion_targets = []
            return

        for name, original in self._deletion_originals.items():
            obj = doc.getObject(name)
            if obj and hasattr(obj, 'ViewObject') and obj.ViewObject:
                vo = obj.ViewObject
                if original.get('color') and hasattr(vo, 'ShapeColor'):
                    vo.ShapeColor = original['color']
                if original.get('transparency') is not None and hasattr(vo, 'Transparency'):
                    vo.Transparency = original['transparency']
                if original.get('line_color') and hasattr(vo, 'LineColor'):
                    vo.LineColor = original['line_color']

        self._deletion_originals = {}
        self._deletion_targets = []
        self._is_deletion = False

    def approve(self) -> str:
        """Approve preview - clear preview and return code for real execution.

        Returns:
            The code to execute for real
        """
        code = self._pending_code
        self.clear_preview()
        self._pending_code = ""
        return code

    def cancel(self):
        """Cancel preview - clear preview without executing."""
        self.clear_preview()
        self._pending_code = ""
        FreeCAD.Console.PrintMessage("AIAssistant: Preview cancelled\n")

    def get_preview_summary(self) -> List[Dict]:
        """Get list of objects that will be created or deleted.

        Returns:
            List of dicts with name, label, type for each object
        """
        # For deletion preview, return info about objects to be deleted
        if self._is_deletion and self._deletion_targets:
            return self._get_deletion_summary()

        # For creation preview, return info from temp doc
        if not self._temp_doc:
            return []

        result = []
        for obj in self._temp_doc.Objects:
            # Skip origin objects
            if obj.TypeId in ("App::Origin", "App::Plane", "App::Line"):
                continue

            # Get human-readable type
            type_name = obj.TypeId.split("::")[-1] if "::" in obj.TypeId else obj.TypeId

            # Get dimensions if it's a shape
            dimensions = {}
            if hasattr(obj, 'Shape') and obj.Shape and not obj.Shape.isNull():
                bbox = obj.Shape.BoundBox
                dimensions = {
                    "width": round(bbox.XLength, 2),
                    "depth": round(bbox.YLength, 2),
                    "height": round(bbox.ZLength, 2),
                }

            result.append({
                "name": obj.Name,
                "label": obj.Label,
                "type": type_name,
                "dimensions": dimensions
            })

        return result

    def _get_deletion_summary(self) -> List[Dict]:
        """Get summary of objects to be deleted.

        Returns:
            List of dicts with name, label, type for each deletion target
        """
        doc = FreeCAD.ActiveDocument
        if not doc:
            return []

        result = []
        for name in self._deletion_targets:
            obj = doc.getObject(name)
            if obj:
                # Get human-readable type
                type_name = obj.TypeId.split("::")[-1] if "::" in obj.TypeId else obj.TypeId

                # Get dimensions if it's a shape
                dimensions = {}
                if hasattr(obj, 'Shape') and obj.Shape and not obj.Shape.isNull():
                    bbox = obj.Shape.BoundBox
                    dimensions = {
                        "width": round(bbox.XLength, 2),
                        "depth": round(bbox.YLength, 2),
                        "height": round(bbox.ZLength, 2),
                    }

                result.append({
                    "name": obj.Name,
                    "label": obj.Label,
                    "type": type_name,
                    "dimensions": dimensions
                })

        return result

    def has_preview(self) -> bool:
        """Check if there's an active preview (creation or deletion)."""
        return len(self._preview_objects) > 0 or len(self._deletion_targets) > 0

    def is_deletion_preview(self) -> bool:
        """Check if current preview is a deletion preview."""
        return self._is_deletion

    def get_pending_code(self) -> str:
        """Get the pending code for the current preview."""
        return self._pending_code
