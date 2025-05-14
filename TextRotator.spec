# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['C:\\Users\\user\\Desktop\\text_rotator2\\text_rotator.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\user\\Desktop\\text_rotator2\\assets', 'assets'), ('C:\\Users\\user\\Desktop\\text_rotator2\\models', 'models'), ('C:\\Users\\user\\Desktop\\text_rotator2\\ui', 'ui'), ('C:\\Users\\user\\Desktop\\text_rotator2\\utils', 'utils')],
    hiddenimports=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TextRotator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\user\\Desktop\\text_rotator2\\assets\\app.ico'],
)
