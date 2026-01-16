# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Syntax Highlighter - Python syntax highlighting for code blocks.
"""

from PySide6 import QtCore, QtGui


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    """Syntax highlighter for Python code."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []
        self._setup_rules()

    def _setup_rules(self):
        """Setup highlighting rules."""
        # Keywords
        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtGui.QColor("#c678dd"))  # Purple
        keyword_format.setFontWeight(QtGui.QFont.Bold)

        keywords = [
            "and", "as", "assert", "async", "await", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "False",
            "finally", "for", "from", "global", "if", "import", "in",
            "is", "lambda", "None", "nonlocal", "not", "or", "pass",
            "raise", "return", "True", "try", "while", "with", "yield"
        ]
        for word in keywords:
            pattern = QtCore.QRegularExpression(rf"\b{word}\b")
            self._rules.append((pattern, keyword_format))

        # Built-in functions
        builtin_format = QtGui.QTextCharFormat()
        builtin_format.setForeground(QtGui.QColor("#61afef"))  # Blue

        builtins = [
            "abs", "all", "any", "bin", "bool", "bytearray", "bytes",
            "callable", "chr", "classmethod", "compile", "complex",
            "delattr", "dict", "dir", "divmod", "enumerate", "eval",
            "exec", "filter", "float", "format", "frozenset", "getattr",
            "globals", "hasattr", "hash", "help", "hex", "id", "input",
            "int", "isinstance", "issubclass", "iter", "len", "list",
            "locals", "map", "max", "memoryview", "min", "next", "object",
            "oct", "open", "ord", "pow", "print", "property", "range",
            "repr", "reversed", "round", "set", "setattr", "slice",
            "sorted", "staticmethod", "str", "sum", "super", "tuple",
            "type", "vars", "zip"
        ]
        for word in builtins:
            pattern = QtCore.QRegularExpression(rf"\b{word}\b")
            self._rules.append((pattern, builtin_format))

        # FreeCAD specific
        freecad_format = QtGui.QTextCharFormat()
        freecad_format.setForeground(QtGui.QColor("#e5c07b"))  # Yellow

        freecad_names = [
            "FreeCAD", "FreeCADGui", "Arch", "Part", "Draft", "Sketcher",
            "PartDesign", "Mesh", "doc", "ActiveDocument", "Vector",
            "Placement", "Rotation", "makeStructure", "makeWall",
            "makeLine", "makeBox", "makeCylinder", "makeSphere",
            "newDocument", "recompute"
        ]
        for word in freecad_names:
            pattern = QtCore.QRegularExpression(rf"\b{word}\b")
            self._rules.append((pattern, freecad_format))

        # Strings (double quotes)
        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(QtGui.QColor("#98c379"))  # Green

        self._rules.append((
            QtCore.QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            string_format
        ))

        # Strings (single quotes)
        self._rules.append((
            QtCore.QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            string_format
        ))

        # f-strings
        fstring_format = QtGui.QTextCharFormat()
        fstring_format.setForeground(QtGui.QColor("#98c379"))

        self._rules.append((
            QtCore.QRegularExpression(r'f"[^"\\]*(\\.[^"\\]*)*"'),
            fstring_format
        ))
        self._rules.append((
            QtCore.QRegularExpression(r"f'[^'\\]*(\\.[^'\\]*)*'"),
            fstring_format
        ))

        # Numbers
        number_format = QtGui.QTextCharFormat()
        number_format.setForeground(QtGui.QColor("#d19a66"))  # Orange

        self._rules.append((
            QtCore.QRegularExpression(r"\b\d+\.?\d*\b"),
            number_format
        ))

        # Comments
        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#5c6370"))  # Gray
        comment_format.setFontItalic(True)

        self._rules.append((
            QtCore.QRegularExpression(r"#[^\n]*"),
            comment_format
        ))

        # Decorators
        decorator_format = QtGui.QTextCharFormat()
        decorator_format.setForeground(QtGui.QColor("#e5c07b"))

        self._rules.append((
            QtCore.QRegularExpression(r"@\w+"),
            decorator_format
        ))

        # Class/function names after def/class keywords
        func_name_format = QtGui.QTextCharFormat()
        func_name_format.setForeground(QtGui.QColor("#61afef"))
        func_name_format.setFontWeight(QtGui.QFont.Bold)

        self._rules.append((
            QtCore.QRegularExpression(r"\bdef\s+(\w+)"),
            func_name_format,
            1  # Capture group index
        ))
        self._rules.append((
            QtCore.QRegularExpression(r"\bclass\s+(\w+)"),
            func_name_format,
            1
        ))

        # Self/cls
        self_format = QtGui.QTextCharFormat()
        self_format.setForeground(QtGui.QColor("#e06c75"))  # Red
        self_format.setFontItalic(True)

        self._rules.append((
            QtCore.QRegularExpression(r"\bself\b"),
            self_format
        ))
        self._rules.append((
            QtCore.QRegularExpression(r"\bcls\b"),
            self_format
        ))

    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        for rule in self._rules:
            if len(rule) == 2:
                pattern, fmt = rule
                group = 0
            else:
                pattern, fmt, group = rule

            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                if group > 0 and match.lastCapturedIndex() >= group:
                    start = match.capturedStart(group)
                    length = match.capturedLength(group)
                else:
                    start = match.capturedStart()
                    length = match.capturedLength()
                self.setFormat(start, length, fmt)


class MultilineStringHighlighter(QtGui.QSyntaxHighlighter):
    """Extended highlighter with multiline string support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._python = PythonHighlighter.__new__(PythonHighlighter)
        self._python.__init__(None)

        # Triple quote state
        self.triple_single = 1
        self.triple_double = 2

        self.string_format = QtGui.QTextCharFormat()
        self.string_format.setForeground(QtGui.QColor("#98c379"))

    def highlightBlock(self, text):
        """Apply highlighting with multiline string support."""
        # Apply single-line rules first
        for rule in self._python._rules:
            if len(rule) == 2:
                pattern, fmt = rule
                group = 0
            else:
                pattern, fmt, group = rule

            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                if group > 0 and match.lastCapturedIndex() >= group:
                    start = match.capturedStart(group)
                    length = match.capturedLength(group)
                else:
                    start = match.capturedStart()
                    length = match.capturedLength()
                self.setFormat(start, length, fmt)

        # Handle multiline strings
        self._highlight_multiline(text, "'''", self.triple_single)
        self._highlight_multiline(text, '"""', self.triple_double)

    def _highlight_multiline(self, text, delimiter, state):
        """Handle multiline string highlighting."""
        if self.previousBlockState() == state:
            start = 0
            add = 0
        else:
            start = text.find(delimiter)
            add = len(delimiter)

        while start >= 0:
            end = text.find(delimiter, start + add)
            if end == -1:
                self.setCurrentBlockState(state)
                length = len(text) - start
            else:
                length = end - start + len(delimiter)

            self.setFormat(start, length, self.string_format)
            start = text.find(delimiter, start + length)
