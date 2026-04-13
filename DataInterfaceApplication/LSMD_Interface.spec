import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))

ICON_PATH = os.path.join(PROJECT_ROOT, 'icon', 'lsmd_icon.ico')
if not os.path.isfile(ICON_PATH):
    ICON_PATH = None

added_data = []
cal_file = os.path.join(PROJECT_ROOT, 'calibration.json')
if os.path.isfile(cal_file):
    added_data.append((cal_file, '.'))

hidden_imports = [
    'bleak.backends.winrt',
    'bleak.backends.winrt.client',
    'bleak.backends.winrt.scanner',
    'serial.tools.list_ports',
    'serial.tools.list_ports_windows',
    'PyQt6.sip',
    'numpy.core._methods',
    'numpy.lib.format',
    'asyncio',
    'asyncio.windows_events',
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=added_data,
    hiddenimports=hidden_imports,
    hookspath=[],
    excludes=['matplotlib', 'scipy', 'tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LSMD_Interface',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON_PATH,
)