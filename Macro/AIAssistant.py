# SPDX-License-Identifier: LGPL-2.1-or-later
"""
AI Assistant MVP for FreeCAD
Run this macro to open an AI chat panel that converts natural language to FreeCAD Python code.

Usage:
1. Run this macro in FreeCAD
2. Type what you want to build
3. Review code and click Run
"""

import FreeCAD
import FreeCADGui
from PySide6 import QtWidgets, QtCore
import json

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

API_URL = "http://20.64.149.209/chat/completions"

SYSTEM_PROMPT = """You are an AI assistant for FreeCAD. Convert user requests to executable Python code.

RULES:
- Return ONLY Python code, no markdown, no explanations
- Always end with doc.recompute()
- Use mm for dimensions

EXAMPLES:

# Box:
import Part
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
box = Part.makeBox(100, 50, 20)
Part.show(box, "Box")
doc.recompute()

# Cylinder:
import Part
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
cyl = Part.makeCylinder(25, 100)
Part.show(cyl, "Cylinder")
doc.recompute()

# Box with hole:
import Part, FreeCAD
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
box = Part.makeBox(100, 100, 50)
cyl = Part.makeCylinder(20, 60)
cyl.translate(FreeCAD.Vector(50, 50, -5))
result = box.cut(cyl)
Part.show(result, "BoxWithHole")
doc.recompute()

# Wall (BIM):
import Arch
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
wall = Arch.makeWall(None, length=4000, width=200, height=3000)
doc.recompute()

# Multiple objects:
import Part, FreeCAD
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
for i in range(5):
    box = Part.makeBox(20, 20, 50)
    box.translate(FreeCAD.Vector(i * 30, 0, 0))
    Part.show(box, f"Column_{i}")
doc.recompute()
"""


def call_llm(user_message):
    """Call Nakle API and return the response."""
    if not HAS_URLLIB:
        return "# Error: urllib not available"

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "sonnet",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "timeout": 120
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"# API Error {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return f"# Error: {e}"


def execute_code(code):
    """Execute Python code in FreeCAD."""
    # Clean markdown if present
    code = code.strip()
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = code[:-3]

    namespace = {
        "FreeCAD": FreeCAD,
        "FreeCADGui": FreeCADGui,
        "Part": __import__("Part"),
        "Draft": __import__("Draft"),
        "Arch": __import__("Arch"),
    }

    try:
        exec(code, namespace)
        if FreeCAD.ActiveDocument:
            FreeCAD.ActiveDocument.recompute()
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        return True, "OK"
    except Exception as e:
        return False, str(e)


class AIPanel(QtWidgets.QDockWidget):
    def __init__(self):
        super().__init__("AI Assistant")
        self._build_ui()

    def _build_ui(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)

        # Chat log
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        layout.addWidget(self.log)

        # Code display
        layout.addWidget(QtWidgets.QLabel("Generated Code:"))
        self.code = QtWidgets.QPlainTextEdit()
        self.code.setMinimumHeight(100)
        layout.addWidget(self.code)

        # Input
        layout.addWidget(QtWidgets.QLabel("What to build:"))
        self.input = QtWidgets.QLineEdit()
        self.input.setPlaceholderText("e.g. Create a 100x50x30 box")
        self.input.returnPressed.connect(self._on_send)
        layout.addWidget(self.input)

        # Buttons
        btns = QtWidgets.QHBoxLayout()
        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        btns.addWidget(self.send_btn)

        self.run_btn = QtWidgets.QPushButton("Run Code")
        self.run_btn.clicked.connect(self._on_run)
        self.run_btn.setEnabled(False)
        btns.addWidget(self.run_btn)

        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        btns.addWidget(self.clear_btn)
        layout.addLayout(btns)

        # Status
        self.status = QtWidgets.QLabel("Ready")
        layout.addWidget(self.status)

        self.setWidget(w)
        self.setMinimumWidth(300)

    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return

        self.log.append(f"<b>You:</b> {text}")
        self.input.clear()
        self.status.setText("Calling AI...")
        self.send_btn.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        response = call_llm(text)
        self.code.setPlainText(response)
        self.log.append("<b>AI:</b> Code generated")
        self.run_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText("Review code, then click Run")

    def _on_run(self):
        code = self.code.toPlainText()
        if not code:
            return

        ok, msg = execute_code(code)
        if ok:
            self.status.setText("Executed successfully")
            self.log.append("<span style='color:green'>Executed OK</span>")
        else:
            self.status.setText(f"Error: {msg}")
            self.log.append(f"<span style='color:red'>Error: {msg}</span>")

    def _on_clear(self):
        self.log.clear()
        self.code.clear()
        self.run_btn.setEnabled(False)
        self.status.setText("Ready")


# Show the panel
def show():
    mw = FreeCADGui.getMainWindow()
    panel = AIPanel()
    mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, panel)
    return panel


# Run when executed as macro
if __name__ == "__main__":
    show()
