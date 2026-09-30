# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

project_dir = os.path.abspath(".")
backend_dir = os.path.join(project_dir, "backend")

# Datas to bundle inside executable / _MEIPASS
datas = [
    (os.path.join(project_dir, "frontend", "dist"), "frontend_dist"),
    (os.path.join(backend_dir, "alembic"), "alembic"),
    (os.path.join(backend_dir, "alembic.ini"), "."),
    (os.path.join(project_dir, "postgres"), "postgres"),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "engineio.async_drivers.asgi",
    "app",
    "app.main",
    "app.config",
    "app.paths",
    "app.api",
    "app.api.router",
    "app.api.routes",
    "app.api.routes.profiles",
    "app.api.routes.analytics",
    "app.api.routes.export",
    "app.api.routes.ai_insights",
    "app.database",
    "app.database.session",
    "app.database.base",
    "app.models",
    "app.models.profile",
    "app.models.post",
    "app.models.collection",
    "app.models.anomaly",
    "app.models.enums",
    "app.services",
    "app.services.collection_service",
    "app.services.analytics_service",
    "app.services.export_service",
    "app.services.profile_service",
    "app.collectors",
    "app.collectors.base",
    "app.collectors.registry",
    "app.collectors.exceptions",
    "app.collectors.browser",
    "app.collectors.browser.base",
    "app.collectors.browser.selenium_driver",
    "app.collectors.instagram",
    "app.collectors.instagram.collector",
    "app.collectors.instagram.parser",
    "app.collectors.x",
    "app.collectors.x.collector",
    "app.collectors.x.parser",
    "app.collectors.facebook",
    "app.collectors.facebook.collector",
    "app.collectors.facebook.parser",
    "app.analytics",
    "app.analytics.growth",
    "app.analytics.engagement",
    "app.analytics.content",
    "app.analytics.frequency",
    "app.analytics.comparison",
    "app.analytics.anomalies",
    "app.ai",
    "app.ai.prompts",
    "app.ai.schemas",
    "app.ai.service",
    "app.ai.providers",
    "app.ai.providers.mock_provider",
    "app.ai.providers.openai_provider",
    "app.scheduler",
    "app.scheduler.scheduler",
    "app.desktop",
    "app.desktop.postgres_manager",
    "app.desktop.migration_manager",
    "psycopg",
    "psycopg_binary",
    "sqlalchemy",
    "sqlalchemy.ext.baked",
    "alembic",
    "alembic.script",
    "alembic.environment",
    "pydantic",
    "pydantic_settings",
    "fastapi",
    "starlette",
    "openpyxl",
    "httpx",
]

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

selenium_hiddenimports = collect_submodules("selenium")
selenium_datas = collect_data_files("selenium")

datas += selenium_datas
hiddenimports += selenium_hiddenimports

a = Analysis(
    ['desktop_launcher.py'],
    pathex=[project_dir, backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='SocialScope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SocialScope',
)
