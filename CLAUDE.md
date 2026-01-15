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

Natural language interface for creating 3D objects. Key components:

- **AIPanel.py**: Main dock widget, orchestrates LLM requests and UI
- **PreviewManager.py**: Executes code in sandbox temp document, shows green transparent preview
- **PreviewWidget.py**: UI for approve/cancel preview actions
- **ChangeWidget.py**: Displays created/modified/deleted objects after execution
- **CodeBlockWidget.py**: Syntax-highlighted code display with Run button
- **LLMBackend.py**: API communication with language model
- **ContextBuilder.py**: Builds document context for LLM requests
- **SessionManager.py**: Persists conversation history

**Preview Flow**:
1. User sends message → LLM returns code
2. Code executes in temp document (sandbox)
3. Shapes copied to main doc as green transparent preview
4. User clicks "Approve & Create" → real execution
5. ChangeWidget shows what was created/modified/deleted

**Auto-Fix Feature**:
When preview fails (e.g., code references non-existent objects), the error is automatically sent back to LLM for correction. This loops up to 3 times before falling back to showing the code block. User never sees the errors - just slightly longer "thinking..." animation.

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
