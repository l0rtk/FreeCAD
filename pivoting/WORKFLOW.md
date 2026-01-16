# FreeCAD Workflow - Understanding the Flow

## Overview

Everything happens in the **same FreeCAD environment**. The "levels" are stages of refinement, not different tools or environments.

---

## The Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SINGLE FreeCAD DOCUMENT                                 │
│                     (one .FCStd file)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LEVEL 1: AI creates initial geometry                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  User: "Create 30x20m warehouse"                                     │   │
│  │           ↓                                                          │   │
│  │  AI generates Python code                                            │   │
│  │           ↓                                                          │   │
│  │  FreeCAD executes code → 3D MODEL appears                           │   │
│  │  (columns, beams, slabs are now objects in the document)            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          ↓                                                  │
│                    SAME DOCUMENT                                            │
│                          ↓                                                  │
│  LEVEL 2: Structural sizing (enhance the same objects)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Calculation engine reads the model                                  │   │
│  │           ↓                                                          │   │
│  │  "Column_A1 is 400x400, but needs 500x500 for this load"            │   │
│  │           ↓                                                          │   │
│  │  Updates the SAME column object's dimensions                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          ↓                                                  │
│                    SAME DOCUMENT                                            │
│                          ↓                                                  │
│  LEVEL 3: Eurocode validation (check the same objects)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Run EN 1992 checks on each member                                   │   │
│  │           ↓                                                          │   │
│  │  "Beam_1: M_Ed = 450 kNm, M_Rd = 520 kNm → OK (87% utilization)"   │   │
│  │           ↓                                                          │   │
│  │  Store results as properties on the SAME objects                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  FINAL: One document with validated design                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  warehouse.FCStd contains:                                           │   │
│  │  • 3D geometry (visual model)                                        │   │
│  │  • Properties (dimensions, materials, utilization)                   │   │
│  │  • Can export to IFC, PDF drawings, etc.                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## FreeCAD Document Structure

```
FreeCAD DOCUMENT (.FCStd file)
│
├── Objects (the 3D things)
│   ├── Column_A1        ← Has properties: Width=500, Height=8000, Material=C40
│   ├── Column_A2
│   ├── Beam_1           ← Has properties: Length=6000, Depth=600, Role="Beam"
│   ├── Beam_2
│   ├── Roof_Slab
│   └── ...
│
├── Properties (metadata on objects)
│   ├── Dimensions (parametric - change one, model updates)
│   ├── Materials
│   ├── Custom properties (we can add: Utilization, Load, etc.)
│
└── Views (how you see it)
    ├── 3D View
    ├── 2D Drawings (TechDraw)
    └── Schedules (tables of quantities)
```

---

## Code Example

```python
# This all happens in ONE FreeCAD session/document

import FreeCAD
import Arch

# Create document (or use existing)
doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Warehouse")

# LEVEL 1: Create a column
column = Arch.makeStructure(400, 400, 8000)  # 400x400mm, 8m tall
column.Label = "Column_A1"

# LEVEL 2: Later, we realize it's too small, so we UPDATE it
column.Width = 500   # Now 500mm
column.Length = 500  # Now 500mm
# The 3D model updates automatically!

# LEVEL 3: Add custom property for utilization
column.addProperty("App::PropertyFloat", "Utilization", "Structural")
column.Utilization = 0.87  # 87% utilized

doc.recompute()  # Refresh the 3D view

# Save the document
doc.saveAs("/path/to/warehouse.FCStd")
```

---

## User Experience Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   1. User opens FreeCAD                                                     │
│   2. User opens AI Assistant (Ctrl+Shift+A)                                │
│   3. User types: "Create a 30x20m warehouse for heavy storage"             │
│                                                                             │
│   4. AI generates code → FreeCAD shows 3D model                            │
│      (User sees columns, beams, walls appear)                              │
│                                                                             │
│   5. [FUTURE] Button: "Validate Structure"                                 │
│      → Runs Eurocode checks                                                 │
│      → Shows: "Column A1: 87% OK, Beam 3: 102% FAIL ⚠️"                    │
│      → AI suggests: "Increase Beam 3 depth to 700mm"                       │
│                                                                             │
│   6. User: "OK, fix it"                                                    │
│      → AI updates the beam in the SAME model                               │
│                                                                             │
│   7. User: "Export calculation report"                                     │
│      → PDF with all Eurocode checks                                        │
│                                                                             │
│   All in ONE window, ONE file, ONE workflow                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Concept

**Levels 1-3 are NOT different tools or environments.**

They are stages of refinement on the **same model**:

| Level | What Happens | Same Document? |
|-------|--------------|----------------|
| Level 1 | AI creates the geometry | ✓ Yes |
| Level 2 | AI/Engine sizes members properly | ✓ Yes (updates objects) |
| Level 3 | Engine validates against Eurocode | ✓ Yes (adds properties) |

The FreeCAD document is the **single source of truth** throughout the entire workflow.

---

## File Formats

| Format | Purpose |
|--------|---------|
| `.FCStd` | FreeCAD native (ZIP with XML + geometry) |
| `.ifc` | Industry standard for BIM exchange |
| `.step` | CAD exchange format |
| `.pdf` | Drawings and reports |

---

*Part of the Cursor for Builders project*
