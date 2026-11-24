# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# 1. Agregamos tus carpetas
datas = [('src', 'src'), ('data', 'data'), ('model', 'model'), ('.streamlit', '.streamlit')]

# 2. Obligamos a recolectar el frontend web interno de Streamlit
datas += collect_data_files('streamlit')
datas += copy_metadata('streamlit')

# 3. Librerías que PyInstaller no puede descubrir solo.
# La carpeta src/ viaja como dato, no como código analizado, así que PyInstaller
# nunca lee sus imports. Si no se listan aquí, el .exe arranca pero predict.py
# falla con ModuleNotFoundError y la app cae al modo de reglas de ejemplo.
ocultos = [
    'streamlit',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'pandas',
    'openpyxl',
    'joblib',        # carga model/modelo_riego.pkl (predict.py)
    'numpy',
    'altair',        # gráficos de componentes.py
]
# scikit-learn: el .pkl guarda objetos de sklearn, así que el paquete entero
# (y scipy, del que depende) tiene que estar dentro del ejecutable.
ocultos += collect_submodules('sklearn')
ocultos += collect_submodules('scipy')

a = Analysis(
    ['lanzador.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=ocultos,
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