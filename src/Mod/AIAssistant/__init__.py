# SPDX-License-Identifier: LGPL-2.1-or-later
"""
AIAssistant - Natural language CAD modeling assistant for FreeCAD.

This module provides an AI-powered chat interface that converts natural
language descriptions into FreeCAD Python code.

Usage:
    import AIAssistant
    AIAssistant.show()

    Or press Ctrl+Shift+A
"""

__version__ = "0.1.0"

_panel = None


def show():
    """Show the AI Assistant panel."""
    global _panel
    import FreeCAD
    import FreeCADGui
    from PySide6 import QtCore
    from . import AIPanel

    mw = FreeCADGui.getMainWindow()
    if mw is None:
        FreeCAD.Console.PrintWarning("AIAssistant: No main window\n")
        return None

    if _panel is None:
        _panel = AIPanel.AIAssistantDockWidget()
        _panel.setObjectName("AIAssistantDockWidget")
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, _panel)

    _panel.show()
    _panel.raise_()
    return _panel


def hide():
    """Hide the AI Assistant panel."""
    global _panel
    if _panel:
        _panel.hide()


def toggle():
    """Toggle the AI Assistant panel."""
    global _panel
    if _panel is None:
        show()
    elif _panel.isVisible():
        _panel.hide()
    else:
        _panel.show()
        _panel.raise_()
