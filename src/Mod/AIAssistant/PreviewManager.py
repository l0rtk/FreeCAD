# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Preview Manager - Manages 3D preview of objects before actual execution.

Executes code in a temporary document and shows preview objects as
green transparent shapes in the main document. User can approve or cancel.
"""

import FreeCAD
import FreeCADGui
import Part
from typing import List, Dict, Optional

# Preview styling
PREVIEW_COLOR = (0.1, 0.9, 0.3)  # Green
PREVIEW_TRANSPARENCY = 70  # 70% transparent


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

    def create_preview(self, code: str) -> bool:
        """Execute code in temp doc and show preview in main doc.

        Args:
            code: Python code to execute

        Returns:
            True if preview created successfully
        """
        main_doc = FreeCAD.ActiveDocument
        if not main_doc:
            FreeCAD.Console.PrintWarning("AIAssistant: No active document for preview\n")
            return False

        self._main_doc_name = main_doc.Name
        self._pending_code = code

        # Clear any existing preview
        self.clear_preview()

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
            original_doc = FreeCAD.ActiveDocument
            FreeCAD.setActiveDocument(self._temp_doc.Name)

            exec(code, exec_globals)
            self._temp_doc.recompute()

            # Restore original active document
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
            return preview_count > 0

        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant: Preview failed: {e}\n")
            import traceback
            traceback.print_exc()
            self.clear_preview()
            return False

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
        """Remove all preview objects and close temp document."""
        # Remove preview objects from main doc
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

        # Close temp document
        if self._temp_doc:
            try:
                FreeCAD.closeDocument(self._temp_doc.Name)
            except Exception:
                pass
            self._temp_doc = None

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
        """Get list of objects that will be created.

        Returns:
            List of dicts with name, label, type for each object
        """
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

    def has_preview(self) -> bool:
        """Check if there's an active preview."""
        return len(self._preview_objects) > 0

    def get_pending_code(self) -> str:
        """Get the pending code for the current preview."""
        return self._pending_code
