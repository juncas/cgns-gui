# CGNS GUI Project Status

## Current Version: 0.3.0-dev (pyCGNS Migration Complete)

### Recent Major Updates (October 2025)

#### ✅ Completed
1. **pyCGNS Migration** - Migrated from h5py to pyCGNS for CGNS file parsing
   - Full support for CGNS/SIDS structure
   - Handles Family_t, ZoneBC_t, BC_t nodes correctly
   - See `docs/migration/` for detailed reports

2. **Family Support** - Complete CGNS Family integration
   - Family hierarchy display in tree view
   - Family-based coloring for boundary conditions
   - Multi-section selection per Family
   - Automatic BC-to-Family matching (including partial matching)

3. **Performance Optimization**
   - Asynchronous file loading (prevents UI freeze)
   - Volume elements hidden by default
   - Configurable transparency settings

4. **Bug Fixes**
   - Fixed symmetry BC matching (tri_symmetry, quad_symmetry)
   - Fixed Family color assignment (extended palette to 12 colors)
   - Fixed orientation axes interaction bug
   - Immediate highlight refresh on tree selection

#### 🔄 In Progress
- Unit test updates (Windows encoding issues with pyCGNS temp files)
- Documentation updates

#### ⏳ Planned Features
- FlowSolution data visualization
- Additional element types (polygons, polyhedra)
- Internationalization (i18n framework exists, needs translations)
- Cell data inspection and query tools

## Project Structure

```
cgns-gui/
├── src/cgns_gui/          # Main application source
│   ├── app.py             # Main window and UI
│   ├── loader.py          # CGNS file parser (pyCGNS-based)
│   ├── model.py           # Data structures (CgnsModel, Zone, Section, Family)
│   ├── scene.py           # VTK rendering pipeline
│   ├── selection.py       # Selection synchronization
│   ├── interaction.py     # VTK interactor customization
│   └── i18n.py            # Internationalization support
├── tests/                 # Test suite
│   ├── fixtures/          # Test data files (.cgns)
│   ├── test_app.py        # GUI tests (pytest-qt)
│   ├── test_loader.py     # Loader tests
│   └── test_scene.py      # Scene manager tests
├── docs/                  # Documentation (see docs/README.md)
│   ├── development/       # Dev plans and notes
│   ├── migration/         # pyCGNS migration docs
│   ├── testing/           # Test reports and guides
│   └── windows/           # Windows-specific docs
├── tools/                 # Build and packaging scripts
├── pyproject.toml         # Project metadata and dependencies
└── cgns-gui.spec          # PyInstaller build specification
```

## Dependencies

**Runtime:**
- Python 3.10+
- PySide6 6.7+ (Qt6 GUI framework)
- VTK 9.3+ (3D visualization)
- pyCGNS 6.3+ (CGNS file parsing) **conda-forge only!**
- numpy

**Development:**
- pytest, pytest-qt (testing)
- ruff (linting and formatting)

## Quick Start

```bash
# Install pyCGNS (conda only!)
conda install -c conda-forge pycgns

# Run application
python -m cgns_gui.app

# Run tests
pytest

# Lint code
ruff check .
```

## Platform Support

- ✅ **Windows 10/11** - Full support, native packaging
- ✅ **Linux** - Supported (requires XCB libraries)
- ⚠️ **macOS** - Should work but untested

### Known Issues
- Windows RDP/virtual displays: Use `--offscreen` flag
- pyCGNS not on PyPI: Must install via conda-forge

## Documentation

See `docs/README.md` for complete documentation index.

Key documents:
- [Development Plan](docs/development/development-plan.md)
- [Migration Report](docs/migration/MIGRATION_FINAL_REPORT.md)
- [Testing Guide](docs/testing/QUICK_TEST_GUIDE.md)
- [Windows Setup](docs/windows/windows-setup.md)

## Contributing

1. Check [Development Plan](docs/development/development-plan.md) for current priorities
2. Review [GUI Test Checklist](docs/testing/GUI_TEST_CHECKLIST.md) before PRs
3. Follow code style (enforced by ruff)
4. Add tests for new features
5. Update documentation

## License

See LICENSE file for details.
