# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/project_builder.py
# Rol Arquitectónico: I/O Orchestrator / Project Generator (B2B Multi-OS)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.7.0
# =========================================================================================

"""
Motor aislado de operaciones de entrada/salida (I/O).
Se encarga de estructurar el árbol de directorios del estudio en el NAS (Nextcloud),
copiar plantillas maestras y ejecutar inicializaciones en segundo plano (Headless Setup).
Alineado con el estándar de directorios de Blender Studio Tools (local, shared, svn) e i18n.
"""

import json
import shutil
import subprocess
import tempfile
import os
import platform
from pathlib import Path

class ProjectBuilder:
    def __init__(self, nextcloud_dir: Path, config_factory):
        self.base_dir = nextcloud_dir
        self.config_factory = config_factory
        
        # Resolución dinámica de la Bóveda alineada con el nuevo estándar B2B
        try:
            self.vault_root = self.config_factory.get_workspace_root() / "openstudio_vault"
        except Exception:
            self.vault_root = nextcloud_dir.parent / "openstudio_vault"
            
        self.vault_templates_dir = self.vault_root / "project_templates"
        self.vault_blender_dir = self.vault_root / "blender_binaries"

    def _get_os_info(self) -> str:
        """Detecta el sistema operativo anfitrión para el motor Headless."""
        system = platform.system().lower()
        if system == "linux": return "linux"
        elif system == "windows": return "windows"
        else: return "macos"

    def create_project(self, project_name: str, blender_version: str, dependencies: dict, project_template: str, splash_image_path: str = "") -> tuple[bool, str]:
        """
        Genera el árbol de directorios para un nuevo proyecto en Nextcloud,
        escribe las configuraciones base, importa el template y dispara la inicialización Headless.
        Retorna una tupla: (Success [Bool], Message [String]) - English Anchored.
        """
        if not project_name.strip():
            return False, "Project name cannot be empty."

        if not blender_version.strip():
            return False, "You must specify a Blender version (e.g., 5.2.0)."

        # Formatear el nombre para que sea seguro en servidores y SVN (mi proyecto -> mi-proyecto)
        folder_name = project_name.strip().lower().replace(" ", "-")
        project_path = self.base_dir / folder_name

        if project_path.exists():
            return False, f"Folder '{folder_name}' already exists on the server."

        try:
            # 1. Construir el árbol de directorios recursivo (Blender Studio Tools Standard)
            carpetas_base = [
                "local",
                "shared",
                "svn/pro/shots",
                "svn/pro/assets",
                "svn/pre/strips",
                "svn/edit",
                "svn/tools",
                "svn/pipeline/blender_kitsu"
            ]

            for carpeta in carpetas_base:
                (project_path / carpeta).mkdir(parents=True, exist_ok=True)

            # 2. La red de seguridad (.nextcloudignore / .gitignore)
            # Obligamos al VCS/Sync a ignorar las carpetas efímeras (local y shared)
            ignore_file = project_path / ".nextcloudignore"
            ignore_content = "local/\nshared/\n*.blend1\n*.blend2\nquit.blend\n"
            
            with open(ignore_file, "w", encoding="utf-8") as f:
                f.write(ignore_content)

            # 3. Copiar archivo base del Template de Pipeline hacia el nodo SVN
            template_path = self.vault_templates_dir / project_template
            if template_path.exists() and template_path.is_dir():
                for item in template_path.iterdir():
                    if item.is_file():
                        shutil.copy2(item, project_path / "svn")
                    elif item.is_dir():
                        shutil.copytree(item, project_path / "svn" / item.name, dirs_exist_ok=True)

            # 4. Generar el Payload Estructural (project_init.json) dentro del pipeline de producción
            payload_data = {
                "project_name": project_name.strip(),
                "blender_version": blender_version.strip(),
                "template": project_template.strip(),
                "dependencies": dependencies
            }

            payload_file = project_path / "svn" / "pipeline" / "project_init.json"
            with open(payload_file, 'w', encoding='utf-8') as f:
                json.dump(payload_data, f, indent=4)

            # 5. Escribir el settings.json local del proyecto (Fallback local temporal)
            settings_data = {
                "vcs_engine": {
                    "active_adapter": self.config_factory.get_vcs_adapter_type(),
                    "production_folder_name": "svn"
                }
            }
            with open(project_path / "settings.json", 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4)

            # 6. Copiar el Splash Screen al entorno de pipeline
            if splash_image_path:
                splash_source = Path(splash_image_path)
                if splash_source.exists() and splash_source.is_file():
                    destino_splash = project_path / "svn" / "pipeline" / "splash.png"
                    shutil.copy(splash_source, destino_splash)

            # 7. Headless Setup: Inicializar Configuraciones del Shot Builder
            self._inicializar_shot_builder(blender_version, project_path)

            return True, f"Project '{folder_name}' successfully initialized."

        except Exception as e:
            return False, f"System error creating folders: {str(e)}"

    def _inicializar_shot_builder(self, blender_version: str, project_path: Path):
        """
        Invoca a Blender en modo Headless (background) para generar los archivos JSON
        y Hooks del Shot Builder en la carpeta pipeline/blender_kitsu del proyecto.
        """
        os_name = self._get_os_info()
        blender_folder = self.vault_blender_dir / f"blender-{blender_version}-{os_name}-x64"
        
        if os_name == "windows":
            blender_bin = blender_folder / "blender.exe"
        elif os_name == "macos":
            blender_bin = blender_folder / "Blender.app" / "Contents" / "MacOS" / "Blender"
        else:
            blender_bin = blender_folder / "blender"

        if not blender_bin.exists():
            print(f"[ProjectBuilder] WARNING: Binary {blender_bin.name} not found for Headless Setup.")
            return

        # El add-on buscará /svn y /shared automáticamente partiendo del project_root_dir
        script_content = f"""
import bpy
import addon_utils

try:
    # 1. Habilitar el add-on
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.blender_kitsu")
    
    # 2. Forzar la ruta del proyecto en memoria
    prefs = bpy.context.preferences.addons["bl_ext.user_default.blender_kitsu"].preferences
    prefs.project_root_dir = r"{project_path.as_posix()}"
    
    # 3. Disparar los Hooks Nativos del Shot Builder
    if hasattr(bpy.ops.kitsu, "build_config_save_hooks"):
        bpy.ops.kitsu.build_config_save_hooks('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_settings('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_templates('EXEC_DEFAULT')
        print("[HEADLESS OK] Shot Builder configuration files successfully generated.")
    else:
        print("[HEADLESS ERROR] Kitsu operators not found.")
except Exception as e:
    print("[HEADLESS ERROR] Failure during Shot Builder configuration:", e)
"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                temp_script.write(script_content)
                temp_script_path = temp_script.name

            print("[ProjectBuilder] Launching Headless Blender to seal Shot Builder...")
            subprocess.run([str(blender_bin), "-b", "--python", temp_script_path], check=False, capture_output=True)
            os.remove(temp_script_path)
            
        except Exception as e:
            print(f"[ProjectBuilder] Critical failure invoking Headless subprocess: {e}")
