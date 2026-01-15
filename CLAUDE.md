# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands (using Pixi)

```bash
# Initialize git submodules (required first time)
pixi run initialize

# Configure and build (debug by default)
pixi run configure        # or configure-release
pixi run build            # or build-release
pixi run install          # or install-release

# Run tests
pixi run test             # or test-release
ctest --test-dir build/debug --output-on-failure  # verbose test output
ctest --test-dir build/debug -R <pattern>         # run specific tests

# Run FreeCAD
pixi run freecad          # or freecad-release
```

## Manual CMake Build

```bash
git submodule update --init --recursive
cmake --preset conda-linux-debug    # or conda-linux-release, conda-macos-*, conda-windows-*
cmake --build build/debug -j$(nproc)
cmake --install build/debug
```

## Code Style

**C++**: Uses clang-format (LLVM-based, Qt style)
- 4-space indent, 100 column limit
- Braces on new line after class/struct/function/namespace
- Pointer/reference alignment: left (`int* ptr`)

**Python**: Uses black formatter
- Line length: 100
- PEP 8 naming: `snake_case` for functions/variables, `CamelCase` for classes

**Pre-commit hooks**: Run `pre-commit run --all-files` before committing. Hooks apply to specific directories (see `.pre-commit-config.yaml` for scope).

## Architecture

### Core (`src/`)
- **Base/**: Foundation utilities (Vector3D, Matrix, Placement, Quantity, Console)
- **App/**: Application core (Document, DocumentObject, PropertyLinks, Transaction, Expression engine)
- **Gui/**: Qt6-based GUI framework, 3D visualization with Coin3D
- **Main/**: Entry point

### Workbenches (`src/Mod/`)
Each workbench follows this structure:
- `App/`: C++ application logic and DocumentObjects
- `Gui/`: ViewProviders and GUI commands
- Python integration throughout

**Key workbenches**:
- **Part**: TopoShape wrapper around OpenCASCADE
- **PartDesign**: Parametric solid modeling (Body, Features)
- **Sketcher**: 2D constraint-based sketching
- **Assembly**: Constraint-based assembly with solver
- **FEM**: Finite element analysis
- **CAM**: Computer-aided manufacturing
- **TechDraw**: Technical drawing generation
- **Draft/BIM**: 2D drafting and building information modeling
- **AIAssistant**: Natural language CAD modeling assistant

### AIAssistant Module (`src/Mod/AIAssistant/`)

Natural language interface for creating 3D objects. Uses a Cursor-inspired dark theme UI.

#### Core Components

| File | Purpose |
|------|---------|
| `AIPanel.py` | Main dock widget, orchestrates LLM requests, settings, and UI integration |
| `ChatWidget.py` | Chat message list, handles message types (user, assistant, plan, preview, code) |
| `PreviewManager.py` | Executes code in sandbox temp document, creates green transparent previews |
| `PreviewWidget.py` | UI for approve/cancel preview with optional auto-approve countdown |
| `ChangeWidget.py` | Displays created/modified/deleted objects after execution |
| `CodeBlockWidget.py` | Syntax-highlighted code display with Run button |
| `ClaudeCodeBackend.py` | Communicates with Claude via `claude` CLI subprocess |
| `ContextBuilder.py` | Builds document context for LLM requests, supports object filtering |
| `SessionManager.py` | Persists conversation history to JSON |
| `Theme.py` | Centralized color palette and styling constants |

#### Advanced Features

| File | Purpose |
|------|---------|
| `PlanWidget.py` | Plan mode UI - shows numbered steps for approval before code generation |
| `StepPreviewWidget.py` | Multi-step diff view - individual step previews with states |
| `ContextSelectionWidget.py` | Context selection dropdown (All/Selected/Custom object modes) |

#### Settings Menu (⋯ button)

- **Debug mode** - Shows raw context sent to LLM
- **Auto-accept previews** - Automatically approve after 500ms delay
- **Plan mode (2-phase)** - Get plan approval before code generation
- **Clear conversation** - Reset chat history

#### User Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STANDARD MODE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User Message ──→ Context Selection ──→ LLM Request ──→ Code        │
│                   (All/Selected/Custom)                              │
│                          │                                           │
│                          ▼                                           │
│              ┌─────────────────────────┐                            │
│              │    Preview Sandbox      │                            │
│              │  (temp doc execution)   │                            │
│              └───────────┬─────────────┘                            │
│                          │                                           │
│              ┌───────────┴───────────┐                              │
│              │     Preview Failed?   │                              │
│              └───────────┬───────────┘                              │
│                    yes/  │ \no                                       │
│                   ┌──────┘  └──────┐                                │
│                   ▼                ▼                                 │
│           Auto-Fix Loop      PreviewWidget                          │
│           (up to 3x)        (green shapes)                          │
│                   │                │                                 │
│                   │       ┌────────┴────────┐                       │
│                   │       │  Auto-Accept?   │                       │
│                   │       └────────┬────────┘                       │
│                   │          yes/  │ \no                            │
│                   │         ┌──────┘  └──────┐                      │
│                   │         ▼                ▼                       │
│                   │    500ms delay     Manual Approve               │
│                   │         │                │                       │
│                   │         └────────┬───────┘                      │
│                   │                  ▼                               │
│                   │         Execute in Main Doc                     │
│                   │                  │                               │
│                   │                  ▼                               │
│                   │           ChangeWidget                          │
│                   │      (shows what changed)                       │
│                   │                                                  │
│                   └──→ CodeBlockWidget (fallback after 3 failures) │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         PLAN MODE (2-PHASE)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User Message ──→ LLM Call #1 ──→ PlanWidget                        │
│                   (plan only)     (numbered steps)                   │
│                                        │                             │
│                          ┌─────────────┴─────────────┐              │
│                          │                           │               │
│                          ▼                           ▼               │
│                    [Approve]                   [Edit Plan]           │
│                          │                           │               │
│                          │              User modifies text           │
│                          │                           │               │
│                          └─────────────┬─────────────┘              │
│                                        ▼                             │
│                              LLM Call #2                             │
│                           (code generation)                          │
│                                        │                             │
│                                        ▼                             │
│                              Standard Preview Flow                   │
│                                   (see above)                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Context Selection

The context selector (above input area) controls what objects are included in LLM context:

- **All objects** - Entire document (default)
- **Selected only** - Only objects selected in FreeCAD's 3D view
- **Custom...** - Manual checkbox selection with expandable list

This affects the `objects_filter` parameter passed to `ContextBuilder.build_context()`.

#### Preview System

1. **Sandbox Execution**: Code runs in a temporary document (`__AIPreview__`)
2. **Shape Copying**: Result shapes copied to main document as transparent green overlays
3. **ViewProvider Styling**: Preview objects use custom transparency and color
4. **Cleanup**: Preview objects removed on cancel; replaced with real objects on approve

#### Auto-Fix Loop

When preview fails (e.g., code references non-existent objects):
1. Error captured and sent back to LLM with context
2. LLM generates corrected code
3. Retry preview (up to 3 attempts)
4. Falls back to CodeBlockWidget if all attempts fail
5. User never sees intermediate errors - just slightly longer "thinking..." animation

#### Signal Flow

```
ChatWidget signals:
  - messageSent(str)           → AIPanel._on_send()
  - previewApproved(str)       → AIPanel._on_preview_approved()
  - previewCancelled()         → AIPanel._on_preview_cancelled()
  - planApproved(str)          → AIPanel._on_plan_approved()
  - planEdited(str)            → AIPanel._on_plan_edited()
  - planCancelled()            → AIPanel._on_plan_cancelled()

ContextSelectionWidget signals:
  - selectionChanged()         → Updates context for next request

PreviewWidget signals:
  - approved()                 → Execute code in main document
  - cancelled()                → Remove preview shapes
```

#### LLM Backend

Uses `ClaudeCodeBackend` which spawns `claude` CLI as subprocess:
- Streams responses via `--output-format stream-json`
- Handles conversation context via `--continue` flag
- Falls back gracefully if CLI not available

### Key Patterns
- **Property System**: Dynamic properties on DocumentObjects with expression support
- **Extension Architecture**: GroupExtension, GeoFeatureGroupExtension, LinkBaseExtension
- **ViewProvider**: Separates 3D visualization from data model
- **pybind11**: C++/Python bindings

### Dependencies
- OpenCASCADE (OCCT 7.8): Geometry kernel
- Qt6/PySide6: GUI framework
- Coin3D/Pivy: 3D scene graph
- Python 3.11+

## Testing

Tests use Google Test (GTest). Test sources are in `tests/src/` with subdirectories mirroring the module structure. Each workbench can have its own test target (e.g., `Sketcher_tests_run`, `Part_tests_run`).

## Contribution Notes

- PRs should be minimal, addressing exactly one problem
- Each commit must compile independently when merged
- Breaking Python API changes require clear migration documentation
- UI changes require before/after screenshots in PR
- FreeCAD uses a single `main` branch (no topic branches on main repo)
