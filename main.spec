# main.spec
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('AudioPilot_Logo2.ico', '.'),
        ('AudioPilot_Logo2.png', '.'),
        ('styles.qss', '.'),
        ('AudioPilot_Logo3.png', '.')
    ],
    hiddenimports=[
        'Data',
        'osc_handlers',
        'ui',
        'utils',
        'pyqtgraph',
        'pythonosc',
        'numpy'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(
    a.pure, 
    a.zipped_data, 
    cipher=None
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Hide the console window
    icon='AudioPilot_Logo2.ico', # Set the icon for the app
    splash='AudioPilot_Logo3.png',  # Set the splash screen
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AudioPilot'
)