# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/env_launcher.py
# Rol Arquitectónico: Subprocess Orchestrator / Sandboxing
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.9
# =========================================================================================

"""
Orquestador de subprocesos para el ecosistema OpenStudio.
Se encarga de ubicar el binario de Blender, construir el entorno aislado (Sandboxing),
e inyectar las variables de entorno para el Context-Aware Tooling y la navegación RNA.
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional

def lanzar_blender(project_root: Path, config_path: Path, svn_user: str, svn_pwd: str, 
                   kitsu_user: str, kitsu_pwd: str, kitsu_host: str, user_role: str, 
                   task_data: dict, target_file: Optional[Path], status_callback,
                   production_folder: str = "02_archivos_de_produccion"):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
                adn = json.load(f)

        template_name = adn.get("template", "Macuare_Estudio")

        if "version_locking" in adn:
            version = adn["version_locking"]["blender_version"]
        else:
            version = adn.get("blender_version", "5.1.2")

        status_callback(f"Buscando Blender {version}...", "yellow")

        # 1. Buscar en boveda global
        boveda_blender = Path.home() / "Nextcloud" / "Macuare-Estudio-Archivos" / "04_BIBLIOTECA_ASSETS" / "blender_versions"
        blender_folder = boveda_blender / f"blender-{version}-linux-x64"
        blender_bin = blender_folder / "blender"

        # 2. Buscar localmente en el proyecto si no esta en boveda (Ej. Aether X)
        if not blender_bin.exists():
            blender_bin = project_root / "06_conf_LOCAL" / "blender-build" / f"blender-{version}-linux-x64" / "blender"

        if not blender_bin.exists():
            raise FileNotFoundError(f"No se encontro el ejecutable para Blender {version}")

        status_callback("Preparando variables de entorno...", "yellow")

        env = os.environ.copy()
        env["OPENSTUDIO_PROJECT_CONFIG"] = str(config_path)

        task_type = task_data.get("task_type_name", "generic")
        project_name = task_data.get("project_name", project_root.name)

        # Configurar Variables de Entorno OS del contexto de producción
        env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
        env["OPENSTUDIO_PRODUCTION_FOLDER"] = production_folder
        env["OPENSTUDIO_USER_ROLE"] = user_role
        env["OPENSTUDIO_TASK_TYPE"] = task_type
        
        # Inyección de Kitsu (Zero-Disk Passwords: En crudo solo para el subproceso temporal)
        env["OPENSTUDIO_KITSU_USER"] = kitsu_user
        env["OPENSTUDIO_KITSU_PWD"] = kitsu_pwd
        env["OPENSTUDIO_KITSU_HOST"] = kitsu_host

        # ---------------------------------------------------------
        # INYECCIÓN DE CONTEXTO DE TAREA (Navegación RNA UI)
        # ---------------------------------------------------------
        env["OPENSTUDIO_TARGET_FILE"] = str(target_file) if target_file else ""
        
        env["OPENSTUDIO_KITSU_PROJECT_ID"] = task_data.get("project_id", "")
        env["OPENSTUDIO_PROJECT_NAME"] = project_name
        
        env["OPENSTUDIO_KITSU_ENTITY_TYPE"] = task_data.get("entity_type", "SHOT").upper()
        env["OPENSTUDIO_KITSU_TASK_TYPE_ID"] = task_data.get("task_type_id", "")
        env["OPENSTUDIO_KITSU_TASK_TYPE_NAME"] = task_type
        env["OPENSTUDIO_KITSU_ENTITY_ID"] = task_data.get("entity_id", "")
        env["OPENSTUDIO_KITSU_ENTITY_NAME"] = task_data.get("entity_name", "")
        
        # Metadatos Dinámicos (Shot vs Asset)
        env["OPENSTUDIO_KITSU_SEQUENCE_ID"] = task_data.get("sequence_id", "")
        env["OPENSTUDIO_KITSU_SEQUENCE_NAME"] = task_data.get("sequence_name", "")
        env["OPENSTUDIO_KITSU_ASSET_TYPE_ID"] = task_data.get("asset_type_id", "")
        env["OPENSTUDIO_KITSU_ASSET_TYPE_NAME"] = task_data.get("asset_type_name", "")

        # Override de directorios de Blender (Sandboxing)
        sandbox_dir = project_root / "06_conf_LOCAL" / "blender_data"
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        env["BLENDER_USER_RESOURCES"] = str(sandbox_dir)
        env["BLENDER_USER_CONFIG"] = str(sandbox_dir / "config")
        env["BLENDER_USER_SCRIPTS"] = str(sandbox_dir / "scripts")

        env["OPENSTUDIO_SVN_USER"] = svn_user
        env["OPENSTUDIO_SVN_PASSWORD"] = svn_pwd

        # 2. Preparar el script bootstrap
        bootstrap_src = Path(__file__).parent / "templates" / "bootstrap.py"
        bootstrap_dst = project_root / "06_conf_LOCAL" / "bootstrap.py"

        bootstrap_dst.parent.mkdir(parents=True, exist_ok=True)
        if bootstrap_src.exists():
            shutil.copy2(bootstrap_src, bootstrap_dst)
        else:
            raise FileNotFoundError("No se encontro core/templates/bootstrap.py")

        status_callback(f"Arrancando {project_name} (Contexto: {task_type.upper()})...", "green")

        # 4. Lanzar el subproceso con el template y el script bootstrap
        cmd = [str(blender_bin), "--app-template", template_name, "--python", str(bootstrap_dst)]
        proceso = subprocess.Popen(cmd, env=env)

        status_callback(f"Blender en ejecucion ({project_name})...", "#00aaff")

        proceso.wait()

        status_callback(f"Sesion de {project_name} terminada.", "green")
    except Exception as e:
        status_callback(f"Error: {str(e)}", "red")
        print(f"Error detallado: {e}")

def _buscar_blender_exe(project_root: Path) -> Path:
    """Busca el binario de Blender dentro de 06_conf_LOCAL."""
    build_dir = project_root / "06_conf_LOCAL" / "blender-build"
    for exe in build_dir.rglob("blender*"):
        if exe.is_file() and os.access(exe, os.X_OK):
            return exe
    return Path("blender")
