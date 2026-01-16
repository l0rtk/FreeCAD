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

## When Unsure About FreeCAD API

You have access to the entire FreeCAD codebase. When unsure about API usage:

1. **Search for examples** using Grep to find how an API is used:
   ```
   Grep pattern="makeHelix" path="{{FREECAD_SOURCE}}"
   Grep pattern="makePipe" path="{{FREECAD_SOURCE}}"
   ```

2. **Look at test files** - they contain working examples:
   ```
   Grep pattern="Part.makeBox" path="{{FREECAD_SOURCE}}" glob="*Test*.py"
   ```

3. **Check workbench implementations** for complex operations:
   - Part module: `{{FREECAD_SOURCE}}/Mod/Part/`
   - PartDesign module: `{{FREECAD_SOURCE}}/Mod/PartDesign/`
   - Draft module: `{{FREECAD_SOURCE}}/Mod/Draft/`

4. **Common API gotchas to avoid**:
   - Circular edges have only 1 vertex (don't access `edge.Vertexes[1]`)
   - Edge/face indices change after boolean operations
   - Use `edge.Length` and `edge.BoundBox` instead of vertex indices for edge detection
   - Helix/sweep operations need proper wire preparation

**Always search for working examples before using unfamiliar API calls.**

## Context Files

- **source.py** - The design expressed as Python code (edit this directly)
- **activity.ndjson** - NDJSON log of all interactions (one JSON object per line)
- **snapshots/** - JSON snapshots of document state (objects, geometry)
- **screenshots/** - Viewport images sent with each message
- **sessions/** - Conversation history and LLM debug data
