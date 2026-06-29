import os
import json
import subprocess
from pathlib import Path



def lanzar_blender(project_root: Path, config_path: Path, svn_user: str, svn_pwd: str, kitsu_user: str, kitsu_pwd: str, status_callback):
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

        status_callback(f"Arrancando {project_root.name}...", "green")

        env = os.environ.copy()
        env["MACUARE_PROJECT_CONFIG"] = str(config_path)

        sandbox_dir = project_root / "06_conf_LOCAL" / "blender_data"
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        env["BLENDER_USER_RESOURCES"] = str(sandbox_dir)

#        env["BLENDER_USER_SCRIPTS"] = str(project_root / "04_tools")
        env["MACUARE_SVN_USER"] = svn_user
        env["MACUARE_SVN_PASSWORD"] = svn_pwd
        env["KITSU_USER"] = kitsu_user
        env["KITSU_PWD"] = kitsu_pwd

        status_callback(f"Arrancando {project_root.name}...", "green")

        proceso = subprocess.Popen([str(blender_bin), "--app-template", template_name], env=env)

        status_callback(f"Blender en ejecucion ({project_root.name})...", "#00aaff")

        proceso.wait()

        status_callback(f"Sesion de {project_root.name} terminada.", "green")
    except Exception as e:
        status_callback(f"Error: {str(e)}", "red")
        print(f"Error detallado: {e}")

