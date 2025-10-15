# CGNS GUI - AI Coding Agent Instructions

## Project Overview

A PySide6 + VTK desktop application for visualizing and interacting with CGNS (CFD General Notation System) mesh files. This is a CFD visualization tool supporting zone/section browsing, 3D rendering, interactive selection, and boundary condition display.

## Architecture

### Core Components (src/cgns_gui/)

- **model.py**: Immutable data model using `@dataclass(slots=True)`
  - `CgnsModel` → `Zone` → `Section` → `MeshData` (points + connectivity)
  - `BoundaryInfo` tracks BC metadata (name, grid_location)
  - Section keys are `(zone_name: str, section_id: int)` tuples throughout the codebase

- **loader.py**: CGNS file parser built on **pyCGNS** (not h5py!)
  - Uses `CGNS.MAP.load()` to load CGNS/Python tree: `[name, value, children, type]`
  - Handles CGNS/SIDS nodes: `Zone_t`, `Elements_t`, `ZoneBC_t`, `BC_t`, `Family_t`
  - Supports: BAR_2, TRI_3, QUAD_4, TETRA_4, PYRA_5, PENTA_6, HEXA_8
  - Element types resolved via `_ELEMENT_TYPE_BY_CODE` (int → str) or `ElementTypeName` node

- **scene.py**: VTK rendering pipeline
  - `SceneManager` converts `Section` → `vtkActor`, manages visibility/transparency/highlighting
  - `RenderStyle.SURFACE` vs `RenderStyle.WIREFRAME` (mutually exclusive, not additive)
  - Actor tracking via `(zone_name, section_id)` keys bidirectionally
  - Surface elements (QUAD/TRI) default to 0.3 transparency for internal visibility

- **selection.py**: Synchronizes tree widget ↔ VTK picker
  - `SelectionController` uses `vtkCellPicker` for actor selection
  - `_updating` flag prevents selection loops between tree and viewport

- **interaction.py**: Custom VTK interactor behaviors
  - `AdaptiveTrackballCameraStyle` adjusts pan/rotation based on scene bounds
  - `InteractionController` manages keyboard shortcuts (R=reset, W=wireframe, S=surface)

- **app.py**: Main window assembly (~960 lines)
  - `_ModelTreeWidget` displays Zone/Section hierarchy with cell counts
  - `SectionDetailsWidget` shows properties + transparency slider
  - `_SettingsDialog` for background color and render mode preferences

### Platform-Specific Behavior

**Windows OpenGL detection** (`_windows_supports_opengl()`):
- Creates temporary `vtkRenderWindow()` to test `SupportsOpenGL()`
- Remote desktop/virtual display drivers often fail → app auto-switches to `--offscreen` mode
- See `docs/windows-opengl-troubleshooting.md` for RDP/ToDesk/Oray workarounds

**Linux XCB requirements** (`_missing_xcb_libs()`):
- Checks for required Qt/OpenGL libraries at startup
- Missing libs trigger user-friendly error with install commands
- `CGNS_GUI_DISABLE_OFFSCREEN_FALLBACK=1` forces GUI mode (advanced users)

## Critical Dependencies

**pyCGNS is mandatory** - installed via conda only:
```bash
conda install -c conda-forge pycgns
```
- **Not available on PyPI** - pip install will fail
- The h5py-based loader was deprecated (see `MIGRATION_FINAL_REPORT.md`)
- Importing `CGNS.MAP` or `CGNS.PAT` without conda install causes startup failure

## Development Workflows

### Run Application
```bash
python -m cgns_gui.app                    # Normal mode
python -m cgns_gui.app --offscreen        # Headless/CI mode
```

### Testing
```bash
pytest                                     # All tests (uses pytest-qt for GUI)
pytest tests/test_loader.py               # Specific module
QT_QPA_PLATFORM=offscreen pytest          # CI environment
```

### Linting & Formatting
```bash
ruff check .                               # Lint check
ruff check . --fix                         # Auto-fix
```

### Building Distributables
```bash
python tools/build_package.py              # Creates wheel + sdist in dist/
pyinstaller cgns-gui.spec                  # Standalone executable (includes .qm translations)
```

## Code Conventions

### Import Handling
- Use relative imports within `cgns_gui` package: `from .model import CgnsModel`
- Fallback for direct execution in `app.py`:
  ```python
  try:
      from .loader import CgnsLoader
  except ImportError:
      from cgns_gui.loader import CgnsLoader
  ```

### VTK Integration
- Always import `vtkmodules.vtkRenderingOpenGL2` before other VTK modules (required backend)
- Suppress VTK warnings: `vtkOutputWindow.SetGlobalWarningDisplay(0)`
- VTK callbacks use dynamic types: `def _on_event(self, obj, event)` → add `# noqa: ANN001`

### Data Model Patterns
- Section keys `(zone_name, section_id)` are used everywhere - never split them
- Always check `section.boundary is None` to distinguish body vs BC sections
- Use `Zone.iter_body_sections()` / `iter_boundary_sections()` for filtered iteration

### Testing with CGNS Files
- Create test CGNS files using `CGNS.MAP.save()` (see `tests/test_loader.py` fixtures)
- Node structure: `[name, value, children, label]` where `label` ends in `_t`
- Element ranges are 1-indexed (CGNS convention), connectivity is 0-indexed (Python)

## Known Gotchas

1. **CGNS Element Indexing**: CGNS uses 1-based vertex indices, convert to 0-based for VTK/numpy
2. **Render Mode Logic**: Surface mode does NOT show wireframe edges (use dedicated toggle)
3. **Selection Reentrancy**: Always set `self._updating = True` in selection methods to avoid loops
4. **pyCGNS Node Types**: Node type labels end in `_t` (e.g., `Zone_t`, not `Zone`)
5. **VTK Actor Visibility**: Hidden actors still exist in renderer, check `actor.GetVisibility()`

## File Organization

- `src/cgns_gui/`: Main package (PEP 420 namespace, no `__init__.py` logic)
- `tests/`: pytest suite using `pytest-qt` for GUI testing
- `docs/`: Development guides (Windows setup, pyCGNS migration, release process)
- `tools/`: Build scripts (not part of package)
- Root test files (`test_*.py`): Legacy integration tests, prefer `tests/` for new tests

## CI/CD

GitHub Actions runs on `ubuntu-latest` and `windows-latest`:
- Environment: `QT_QPA_PLATFORM=offscreen`, `CGNS_GUI_FORCE_OFFSCREEN=1`
- **No conda in CI** - pyCGNS is manually installed via pip (special case for CI)
- Workflow: lint → pytest → build → wheel smoke test
- See `.github/workflows/ci.yml` for exact commands

## Future Extensions

- **FlowSolution support**: pyCGNS already loads `FlowSolution_t` nodes, extend model.py
- **I18n**: Translation framework exists (`src/cgns_gui/i18n.py`), add `.ts` files to `translations/`
- **Additional cell types**: Extend `_SUPPORTED_ELEMENT_SIZES` and `_ELEMENT_TYPE_TO_VTK` mappings
