# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/project_builder.py
# Rol Arquitectónico: I/O Orchestrator / Project Generator
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.0
# =========================================================================================

"""
Motor aislado de operaciones de entrada/salida (I/O).
Se encarga de estructurar el árbol de directorios del estudio en el NAS (Nextcloud),
copiar plantillas maestras y ejecutar inicializaciones en segundo plano (Headless Setup).
"""

import json
import shutil
import subprocess
import tempfile
import os
from pathlib import Path

class ProjectBuilder:
    def __init__(self, nextcloud_dir: Path):
        self.base_dir = nextcloud_dir
        # Rutas maestras de la bóveda de software
        self.vault_templates_dir = self.base_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "templates"
        self.vault_blender_dir = self.base_dir.parent / "04_BIBLIOTECA_ASSETS" / "blender_versions"

    def create_project(self, project_name: str, blender_version: str, dependencies: dict, project_template: str, splash_image_path: str = "") -> tuple[bool, str]:
        """
        Genera el árbol de directorios para un nuevo proyecto en Nextcloud,
        escribe las configuraciones base, importa el template y dispara la inicialización Headless.
        Retorna una tupla: (Éxito [Booleano], Mensaje [String])
        """
        if not project_name.strip():
            return False, "El nombre del proyecto no puede estar vacío."

        if not blender_version.strip():
            return False, "Debes especificar una versión de Blender (ej. 5.1.2)."

        # Formatear el nombre para que sea seguro en servidores y SVN (mi proyecto -> mi-proyecto)
        folder_name = project_name.strip().lower().replace(" ", "-")
        project_path = self.base_dir / folder_name

        if project_path.exists():
            return False, f"La carpeta '{folder_name}' ya existe en el servidor."

        try:
            # 1. Construir el árbol de directorios recursivo (Issue 3)
            # Ahora SÍ creamos 02_archivos_de_produccion porque es el Génesis del SVN
            carpetas_base = [
                "01_Brief_y_Refs",
                "02_archivos_de_produccion/pro/shots",
                "02_archivos_de_produccion/pro/assets",
                "02_archivos_de_produccion/pre/strips",
                "02_archivos_de_produccion/edit",
                "02_archivos_de_produccion/pipeline/blender_kitsu",
                "03_render",
                "04_tools",
                "05_config_estudio",
                "06_conf_LOCAL"
            ]

            for carpeta in carpetas_base:
                (project_path / carpeta).mkdir(parents=True, exist_ok=True)

            # 2. La red de seguridad (.nextcloudignore)
            # Obligamos a Nextcloud a ignorar las carpetas pesadas/locales desde el día 1
            ignore_file = project_path / ".nextcloudignore"
            ignore_content = "06_conf_LOCAL\n*.blend1\n*.blend2\nquit.blend\n"
            
            with open(ignore_file, "w", encoding="utf-8") as f:
                f.write(ignore_content)

            # 3. Copiar archivo base del Template de Pipeline
            template_path = self.vault_templates_dir / project_template
            if template_path.exists() and template_path.is_dir():
                for item in template_path.iterdir():
                    if item.is_file():
                        shutil.copy2(item, project_path / "02_archivos_de_produccion")
                    elif item.is_dir():
                        shutil.copytree(item, project_path / "02_archivos_de_produccion" / item.name, dirs_exist_ok=True)

            # 4. Generar el Payload Estructural (project_init.json)
            payload_data = {
                "project_name": project_name.strip(),
                "blender_version": blender_version.strip(),
                "template": project_template.strip(),
                "dependencies": dependencies # Ya viene estructurado por categorías
            }

            payload_file = project_path / "05_config_estudio" / "project_init.json"
            with open(payload_file, 'w', encoding='utf-8') as f:
                json.dump(payload_data, f, indent=4)

            # 5. Escribir el settings.json local del proyecto (Fallback)
            settings_data = {
                "vcs_engine": {
                    "active_adapter": "svn",
                    "production_folder_name": "02_archivos_de_produccion"
                }
            }
            with open(project_path / "settings.json", 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4)

            # 6. Copiar el Splash Screen
            if splash_image_path:
                splash_source = Path(splash_image_path)
                if splash_source.exists() and splash_source.is_file():
                    destino_splash = project_path / "05_config_estudio" / "splash.png"
                    shutil.copy(splash_source, destino_splash)

            # 7. Headless Setup: Inicializar Configuraciones del Shot Builder (Issue 7)
            self._inicializar_shot_builder(blender_version, project_path)

            return True, f"Proyecto '{folder_name}' inicializado. Esperando SVN Commit inicial."

        except Exception as e:
            return False, f"Error de sistema al crear carpetas: {str(e)}"

    def _inicializar_shot_builder(self, blender_version: str, project_path: Path):
        """
        Invoca a Blender en modo Headless (background) para generar los archivos JSON
        y Hooks del Shot Builder en la carpeta pipeline/blender_kitsu del proyecto.
        """
        blender_folder = self.vault_blender_dir / f"blender-{blender_version}-linux-x64"
        blender_bin = blender_folder / "blender"

        if not blender_bin.exists():
            print(f"[ProjectBuilder] ADVERTENCIA: No se encontró Blender {blender_version} para el Headless Setup.")
            return

        # Script dinámico que inyectaremos temporalmente en Blender
        script_content = f"""
import bpy
import addon_utils

try:
    # 1. Habilitar el add-on
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.blender_kitsu")
    
    # 2. Forzar la ruta del proyecto en memoria para que el add-on sepa dónde guardar
    prefs = bpy.context.preferences.addons["bl_ext.user_default.blender_kitsu"].preferences
    prefs.project_root_dir = r"{project_path.as_posix()}"
    
    # 3. Disparar los Hooks Nativos del Shot Builder
    if hasattr(bpy.ops.kitsu, "build_config_save_hooks"):
        bpy.ops.kitsu.build_config_save_hooks('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_settings('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_templates('EXEC_DEFAULT')
        print("[HEADLESS OK] Archivos de configuración del Shot Builder generados exitosamente.")
    else:
        print("[HEADLESS ERROR] No se encontraron los operadores de Kitsu.")
except Exception as e:
    print("[HEADLESS ERROR] Fallo durante la configuración del Shot Builder:", e)
"""
        try:
            # Crear archivo Python temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                temp_script.write(script_content)
                temp_script_path = temp_script.name

            print("[ProjectBuilder] Lanzando Blender Headless para sellar el Shot Builder...")
            
            # Ejecutar Blender en Background (-b) procesando el script (--python)
            subprocess.run([str(blender_bin), "-b", "--python", temp_script_path], check=False, capture_output=True)
            
            os.remove(temp_script_path)
            
        except Exception as e:
            print(f"[ProjectBuilder] Fallo crítico al invocar subproceso Headless: {e}")
