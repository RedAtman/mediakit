# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onefile spec for mediakit.

Kept as a spec (not CLI flags) on purpose: --add-data uses a different
source:dest separator per OS, and copy_metadata/hiddenimports cannot be
expressed as flags without repeating them in every CI matrix leg.

Build: pyinstaller mediakit.spec --noconfirm --distpath <dir> --workpath <dir>
"""
from PyInstaller.utils.hooks import copy_metadata

datas = [
    # utils/media.py reads this next to itself to build the extension registry
    ('utils/media_types.json', 'utils'),
    # without the dist metadata the frozen binary reports "mediakit unknown",
    # since utils/cli.py resolves the version from installed distribution metadata
    *copy_metadata('mediakit'),
]

hiddenimports = [
    # config.py loads the logger with import_module('utils.logger.init'), which
    # static analysis cannot see; dictConfig then reflects the filters/formatters
    # by their dotted string names
    'utils.logger.init',
    'utils.logger.lexers',
    'utils.logger.formatters',
    'utils.logger.filters',
    # src/__init__.py: import_module('src.signals')
    'src.signals',
    # base.video/base.audio used to be listed here because folder.py resolved them
    # with import_module(f'base.{media_type}'); they are now static names in
    # MEDIA_CLASSES, so the analyser finds them on its own.
]

excludes = [
    # pulls in PyInstaller's multiprocessing runtime hook, whose onefile child dies
    # with "No module named 'array'". Nothing here uses it: utils/executor.py is
    # ThreadPoolExecutor-only (it used to borrow multiprocessing.cpu_count).
    # The import graph reaches it only through ffmpeg-python -> future.moves.
    'multiprocessing',
]

a = Analysis(
    ['cli.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mediakit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # upx is not installed on every runner and its output is not reproducible
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
