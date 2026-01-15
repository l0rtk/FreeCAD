# FreeCAD AI Assistant Context

You are helping design a 3D model in FreeCAD.

## Workflow: Direct Source Editing

**source.py** is the single source of truth for this design. It's a Python script that generates the FreeCAD geometry when executed.

**To make design changes:**
1. Read source.py to understand the current design
2. Use the Edit tool to modify source.py directly
3. CREATE objects: Add code to source.py
4. DELETE objects: Remove the relevant code from source.py
5. MODIFY objects: Edit the relevant code in source.py

**Example - to delete an object named "Roof":**
- DO: Use Edit tool to remove the lines that create "Roof" from source.py
- DON'T: Return `doc.removeObject('Roof')` code

**To answer questions (not modify design):**
Return a clear text explanation.

## Code Rules

- Use millimeters for dimensions
- End code with `doc.recompute()`
- Use descriptive Labels for objects
- Use object Names (not Labels) when referencing in code

## Context Files

- **source.py** - The design expressed as Python code (edit this directly)
- **snapshots/** - JSON snapshots of object state
- **sessions/** - Conversation history
