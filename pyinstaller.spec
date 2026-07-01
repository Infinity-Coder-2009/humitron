# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/api/server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('src/humitron', 'humitron'),
    ],
    hiddenimports=[
        'humitron.agent',
        'humitron.config.loader',
        'humitron.tools.registry',
        'humitron.tools.file_ops',
        'humitron.tools.bash',
        'humitron.tools.web',
        'humitron.memory.conversation',
        'humitron.models.tools',
        'humitron.models.agent',
        'humitron.utils.logging',
        'humitron.utils.safety',
        'humitron.llm.providers',
        'humitron.orchestrator.planner',
        'pydantic',
        'pydantic_core',
        'yaml',
        'loguru',
        'rich',
        'httpx',
        'uvicorn',
        'fastapi',
        'starlette',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='humitron-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)