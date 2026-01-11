# SPDX-License-Identifier: LGPL-2.1-or-later
"""AIAssistant GUI initialization."""

# Note: FreeCAD and FreeCADGui are pre-loaded by FreeCAD before this runs
FreeCAD.Console.PrintMessage(">>> AIAssistant InitGui loading\n")

_panel = None


def show_panel():
    """Show the AI Assistant panel."""
    global _panel

    mw = FreeCADGui.getMainWindow()
    if mw is None:
        FreeCAD.Console.PrintWarning("AIAssistant: No main window\n")
        return None

    if _panel is None:
        try:
            from PySide6 import QtCore
            # Use absolute import instead of relative
            import AIAssistant.AIPanel as AIPanel
            _panel = AIPanel.AIAssistantDockWidget()
            _panel.setObjectName("AIAssistantDockWidget")
            mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, _panel)
            FreeCAD.Console.PrintMessage(">>> AIAssistant panel created\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant error: {e}\n")
            import traceback
            traceback.print_exc()
            return None

    _panel.show()
    _panel.raise_()
    return _panel


def toggle_panel():
    """Toggle panel visibility."""
    global _panel
    if _panel is None:
        show_panel()
    elif _panel.isVisible():
        _panel.hide()
    else:
        _panel.show()
        _panel.raise_()


class AIAssistantCommand:
    """Command to toggle AI Assistant."""

    def GetResources(self):
        return {
            "MenuText": "AI Assistant",
            "ToolTip": "Toggle AI Assistant panel",
            "Accel": "Ctrl+Shift+A",
        }

    def Activated(self):
        # Import the module to access functions that persist
        import AIAssistant
        AIAssistant.toggle()

    def IsActive(self):
        return True


# Register the command
FreeCADGui.addCommand("Std_AIAssistant", AIAssistantCommand())
FreeCAD.Console.PrintMessage(">>> AIAssistant command registered\n")


# Add to View menu after delay
def _setup_menu():
    FreeCAD.Console.PrintMessage(">>> AIAssistant setting up menu\n")
    try:
        from PySide6 import QtGui  # QAction is in QtGui in PySide6
        mw = FreeCADGui.getMainWindow()
        if mw:
            for action in mw.menuBar().actions():
                if "View" in action.text():
                    menu = action.menu()
                    if menu:
                        act = QtGui.QAction("AI Assistant", mw)
                        act.setShortcut("Ctrl+Shift+A")
                        # Use the registered command instead of direct function reference
                        act.triggered.connect(lambda: FreeCADGui.runCommand("Std_AIAssistant"))
                        menu.addAction(act)
                        FreeCAD.Console.PrintMessage(">>> AIAssistant added to View menu\n")
                        return
    except Exception as e:
        FreeCAD.Console.PrintWarning(f"AIAssistant menu error: {e}\n")


from PySide6 import QtCore
QtCore.QTimer.singleShot(3000, _setup_menu)

FreeCAD.Console.PrintMessage(">>> AIAssistant InitGui loaded\n")
