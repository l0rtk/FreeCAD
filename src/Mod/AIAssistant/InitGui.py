# SPDX-License-Identifier: LGPL-2.1-or-later
"""
AIAssistant GUI initialization.
Registers the AI Assistant panel in FreeCAD.
"""

import FreeCAD
import FreeCADGui
from PySide6 import QtCore, QtWidgets

# Global panel reference
_panel = None
_initialized = False


def get_main_window():
    """Get FreeCAD main window."""
    return FreeCADGui.getMainWindow()


def create_panel():
    """Create and register the AI Assistant panel."""
    global _panel, _initialized

    if _initialized:
        return _panel

    mw = get_main_window()
    if mw is None:
        # Retry later
        QtCore.QTimer.singleShot(500, create_panel)
        return None

    try:
        from . import AIPanel
        _panel = AIPanel.AIAssistantDockWidget()
        _panel.setObjectName("Std_AIAssistant")

        # Add to main window (right side, hidden initially)
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, _panel)
        _panel.hide()

        # Add toggle action to View menu
        _add_to_view_menu(mw, _panel)

        _initialized = True
        FreeCAD.Console.PrintLog("AIAssistant panel created\n")

    except Exception as e:
        FreeCAD.Console.PrintError(f"AIAssistant init error: {e}\n")

    return _panel


def _add_to_view_menu(mw, panel):
    """Add the panel's toggle action to View menu."""
    # Get the dock widget's built-in toggle action
    toggle_action = panel.toggleViewAction()
    toggle_action.setText("AI Assistant")
    toggle_action.setShortcut("Ctrl+Shift+A")
    toggle_action.setStatusTip("Toggle AI Assistant panel")

    # Find View menu
    menubar = mw.menuBar()
    view_menu = None

    for action in menubar.actions():
        menu_text = action.text().replace("&", "")
        if menu_text == "View":
            view_menu = action.menu()
            break

    if view_menu:
        # Find insertion point (before separator/toolbars section)
        actions = view_menu.actions()
        insert_pos = None

        for i, action in enumerate(actions):
            if action.isSeparator():
                # Insert before first separator that comes after panel items
                # Look for pattern: panels... separator... toolbars
                if i > 3:  # After a few panel entries
                    insert_pos = action
                    break

        if insert_pos:
            view_menu.insertAction(insert_pos, toggle_action)
        else:
            # Fallback: add at the end before last separator
            view_menu.addAction(toggle_action)

        FreeCAD.Console.PrintLog("AIAssistant added to View menu\n")
    else:
        FreeCAD.Console.PrintWarning("Could not find View menu\n")


def show_panel():
    """Show the AI Assistant panel."""
    global _panel
    if _panel is None:
        create_panel()
    if _panel:
        _panel.show()
        _panel.raise_()


def toggle_panel():
    """Toggle AI Assistant panel visibility."""
    global _panel
    if _panel is None:
        create_panel()
    if _panel:
        _panel.setVisible(not _panel.isVisible())
        if _panel.isVisible():
            _panel.raise_()


class AIAssistantCommand:
    """FreeCAD command to toggle the AI Assistant panel."""

    def GetResources(self):
        return {
            "MenuText": "AI Assistant",
            "ToolTip": "Toggle AI Assistant panel for natural language modeling",
            "Accel": "Ctrl+Shift+A",
        }

    def Activated(self):
        toggle_panel()

    def IsActive(self):
        return True


# Register command
FreeCADGui.addCommand("Std_AIAssistant", AIAssistantCommand())

# Initialize panel after GUI is ready
# Use longer delay to ensure main window is fully constructed
QtCore.QTimer.singleShot(2000, create_panel)

FreeCAD.Console.PrintLog("AIAssistant module loaded\n")
