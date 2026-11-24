# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# 1. Agregamos tus carpetas
datas = [('src', 'src'), ('data', 'data'), ('model', 'model'), ('.streamlit', '.streamlit')]

# 2. Obligamos a recolectar el frontend web interno de Streamlit
datas += collect_data_files('streamlit')
datas += copy_metadata('streamlit')

a = Analysis(
    ['lanzador.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'pandas',
        'openpyxl'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='OptimizacionRiego',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Cambia a True si en el futuro necesitas ver los errores en consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icono.ico', # Opcional: Quita el "#" si lograste conseguir una imagen .ico real
)