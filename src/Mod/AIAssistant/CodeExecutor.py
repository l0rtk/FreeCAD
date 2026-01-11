# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Code Executor - Safely executes AI-generated Python code in FreeCAD.
"""

import FreeCAD
import FreeCADGui

# Patterns that might indicate dangerous operations
BLOCKED_PATTERNS = [
    "os.system",
    "subprocess",
    "shutil.rmtree",
    "shutil.remove",
    "__import__('os')",
    "__import__(\"os\")",
    "eval(",
    "open(",
    "file(",
    ".write(",
    "requests.",
    "urllib.",
    "socket.",
]


def execute(code: str) -> tuple:
    """
    Execute Python code in FreeCAD's environment.

    Args:
        code: Python code string to execute

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Clean the code
    code = _clean_code(code)

    if not code.strip():
        return False, "No code to execute"

    # Safety check
    safety_result = _safety_check(code)
    if safety_result:
        return False, safety_result

    # Build execution namespace with FreeCAD modules
    namespace = _build_namespace()

    try:
        # Execute the code
        exec(code, namespace)

        # Recompute document
        if FreeCAD.ActiveDocument:
            FreeCAD.ActiveDocument.recompute()

        # Fit view to show results
        try:
            if FreeCADGui.ActiveDocument and FreeCADGui.ActiveDocument.ActiveView:
                FreeCADGui.ActiveDocument.ActiveView.fitAll()
        except Exception:
            pass

        return True, "Code executed successfully"

    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"

    except NameError as e:
        return False, f"Name error: {e}"

    except AttributeError as e:
        return False, f"Attribute error: {e}"

    except Exception as e:
        return False, f"Execution error: {type(e).__name__}: {e}"


def _clean_code(code: str) -> str:
    """Clean up code - remove markdown formatting if present."""
    code = code.strip()

    # Remove markdown code fences
    lines = code.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _safety_check(code: str) -> str:
    """
    Check code for potentially dangerous operations.

    Returns:
        Error message if dangerous pattern found, empty string if safe.
    """
    code_lower = code.lower()

    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in code_lower:
            return f"Blocked potentially dangerous operation: {pattern}"

    return ""


def _build_namespace() -> dict:
    """Build the execution namespace with FreeCAD modules."""
    namespace = {
        "FreeCAD": FreeCAD,
        "FreeCADGui": FreeCADGui,
        "App": FreeCAD,
        "Gui": FreeCADGui,
    }

    # Import common modules
    modules_to_import = [
        "Part",
        "Draft",
        "Arch",
        "Sketcher",
        "PartDesign",
        "Mesh",
    ]

    for mod_name in modules_to_import:
        try:
            namespace[mod_name] = __import__(mod_name)
        except ImportError:
            pass

    # Try to import BIM module
    try:
        import BIM
        namespace["BIM"] = BIM
    except ImportError:
        pass

    # Try to import BIM.ArchPrecast
    try:
        from BIM import ArchPrecast
        namespace["ArchPrecast"] = ArchPrecast
    except ImportError:
        pass

    return namespace


def validate_code(code: str) -> tuple:
    """
    Validate code without executing it.

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    code = _clean_code(code)

    if not code.strip():
        return False, "Empty code"

    # Safety check
    safety_result = _safety_check(code)
    if safety_result:
        return False, safety_result

    # Try to compile
    try:
        compile(code, "<ai_generated>", "exec")
        return True, "Code is valid"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
