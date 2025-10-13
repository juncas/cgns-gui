# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Get the source directory
src_dir = Path('src/cgns_gui')

# Collect all translation files
datas = []
translations_dir = src_dir / 'translations'
if translations_dir.exists():
    for qm_file in translations_dir.glob('*.qm'):
        datas.append((str(qm_file), 'cgns_gui/translations'))

a = Analysis(
    ['src/cgns_gui/app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'vtkmodules',
        'vtkmodules.all',
        'vtkmodules.qt.QVTKRenderWindowInteractor',
        'vtkmodules.vtkRenderingOpenGL2',
        'vtkmodules.vtkInteractionStyle',
        'vtkmodules.vtkRenderingCore',
        'vtkmodules.vtkCommonCore',
        'vtkmodules.vtkCommonDataModel',
        'vtkmodules.vtkRenderingAnnotation',
        'vtkmodules.vtkInteractionWidgets',
        'h5py',
        'h5py.defs',
        'h5py.utils',
        'h5py.h5ac',
        'h5py._proxy',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cgns-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cgns-gui',
)
