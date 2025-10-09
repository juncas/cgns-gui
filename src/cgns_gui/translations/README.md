# Translation Catalogs

Place compiled Qt translation catalogs (`.qm` files) in this directory. The
application looks for files following the pattern `cgns_gui_<locale>.qm`, for
example:

- `cgns_gui_zh_CN.qm`
- `cgns_gui_zh.qm`

To create a catalog:

1. Generate a `.ts` source file using `pyside6-lupdate`:
   ```bash
   pyside6-lupdate ../.. -ts cgns_gui_zh_CN.ts
   ```
2. Translate the generated `.ts` file with Qt Linguist.
3. Compile it into a `.qm` binary using `pyside6-lrelease`:
   ```bash
   pyside6-lrelease cgns_gui_zh_CN.ts
   ```
4. Copy the resulting `.qm` file into this folder.

On startup, the application automatically installs the matching translator
based on the system locale; if no catalog is found the interface remains in
English.
