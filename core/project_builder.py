# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/project_builder.py
# Rol Arquitectónico: I/O Orchestrator / Project Generator (B2B Multi-OS)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.6.1 (Restauración de Headless Builder)
# =========================================================================================

import os
import json
import shutil
import zipfile
import tarfile
import subprocess
import tempfile
import platform
from pathlib import Path

from core.vcs_router import VCSRouter
from core.kitsu_manager import KitsuManager

class ProjectBuilder:
    def __init__(self, config_factory):
        self.config_factory = config_factory

    @property
    def base_dir(self) -> Path:
        return self.config_factory.get_workspace_root()

    @property
    def vault_root(self) -> Path:
        return self.config_factory.get_vault_path()

    @property
    def vault_templates_dir(self) -> Path:
        return self.vault_root / "project_templates"

    @property
    def vault_blender_dir(self) -> Path:
        return self.vault_root / "blender_versions"

    def _get_os_info(self) -> str:
        system = platform.system().lower()
        if system == "linux": return "linux"
        elif system == "windows": return "windows"
        else: return "macos"

    def create_project(self, project_name: str, blender_version: str, dependencies: dict, project_template: str, splash_image_path: str = "", vcs_user: str = "", vcs_pwd: str = "") -> tuple[bool, str]:
        if not project_name.strip(): return False, "Project name cannot be empty."
        if not blender_version.strip(): return False, "You must specify a Blender version."

        folder_name = project_name.strip().lower().replace(" ", "-")
        project_path = self.base_dir / folder_name

        if project_path.exists():
            return False, f"Folder '{folder_name}' already exists on the NAS."

        kitsu = KitsuManager()
        success, kitsu_msg, kitsu_project = kitsu.create_project(project_name.strip())
        
        if not success:
            return False, f"Abortado por Kitsu: {kitsu_msg}"
            
        project_id = kitsu_project.get("id", "")
        print(f"[ProjectBuilder] Entidad Kitsu forjada con éxito. ID: {project_id}")

        try:
            vfs_svn = self.config_factory.get_vfs_svn_name()
            vfs_shared = self.config_factory.get_vfs_shared_name()
            vfs_local = self.config_factory.get_vfs_local_name()
            vfs_pipe = self.config_factory.get_vfs_pipeline_name()
            custom_dirs = self.config_factory.get_custom_dirs()

            base_folders = [
                vfs_local, vfs_shared, vfs_pipe,
                f"{vfs_svn}/pro/shots", f"{vfs_svn}/pro/assets",
                f"{vfs_svn}/pre/strips", f"{vfs_svn}/edit", f"{vfs_svn}/tools"
            ] + custom_dirs

            for folder in base_folders:
                (project_path / folder).mkdir(parents=True, exist_ok=True)

            ignore_file = project_path / ".gitignore"
            with open(ignore_file, "w", encoding="utf-8") as f:
                f.write(f"{vfs_local}/\n{vfs_shared}/\n{vfs_pipe}/\n*.blend1\n*.blend2\nquit.blend\n")

            template_path = self.vault_templates_dir / project_template
            if template_path.exists() and template_path.is_dir():
                for item in template_path.iterdir():
                    if item.is_file(): shutil.copy2(item, project_path / vfs_svn)
                    elif item.is_dir(): shutil.copytree(item, project_path / vfs_svn / item.name, dirs_exist_ok=True)

            payload_data = {
                "project_name": project_name.strip(),
                "kitsu_project_id": project_id,
                "blender_version": blender_version.strip(),
                "template": project_template.strip(),
                "dependencies": dependencies,
                "topography_signature": {
                    "vfs_svn": vfs_svn, "vfs_shared": vfs_shared,
                    "vfs_local": vfs_local, "vfs_pipeline": vfs_pipe
                }
            }

            payload_file_svn = project_path / vfs_svn / "project_init.json"
            with open(payload_file_svn, 'w', encoding='utf-8') as f: json.dump(payload_data, f, indent=4)
            shutil.copy2(payload_file_svn, project_path / vfs_pipe / "project_init.json")

            if splash_image_path:
                splash_source = Path(splash_image_path)
                if splash_source.exists() and splash_source.is_file():
                    shutil.copy(splash_source, project_path / vfs_pipe / "splash.png")
                    kitsu.upload_project_splash(project_id, splash_image_path)

            kitsu_user = os.environ.get("OPENSTUDIO_KITSU_USER", "")
            kitsu_pwd = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
            
            self._inicializar_shot_builder(blender_version, project_path, vfs_svn, vfs_local, project_id, kitsu_user, kitsu_pwd, dependencies)

            base_repo_url = self.config_factory.get_vcs_repository_url()
            
            if "localhost" in base_repo_url:
                vcs_user = "admin"
                vcs_pwd = "admin123"
                
                try:
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "svnadmin", "create", f"/home/svn/{folder_name}"], check=True, capture_output=True)
                    
                    conf_cmd = (
                        f"echo '[general]' > /home/svn/{folder_name}/conf/svnserve.conf && "
                        f"echo 'anon-access = none' >> /home/svn/{folder_name}/conf/svnserve.conf && "
                        f"echo 'auth-access = write' >> /home/svn/{folder_name}/conf/svnserve.conf && "
                        f"echo 'password-db = passwd' >> /home/svn/{folder_name}/conf/svnserve.conf"
                    )
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", conf_cmd], check=True, capture_output=True)
                    
                    pwd_cmd = f"echo '[users]' > /home/svn/{folder_name}/conf/passwd && echo 'admin = admin123' >> /home/svn/{folder_name}/conf/passwd"
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", pwd_cmd], check=True, capture_output=True)
                    
                    mkdir_cmd = f"svn mkdir file:///home/svn/{folder_name}/{vfs_svn} -m 'Init Hub Topology'"
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", mkdir_cmd], check=True, capture_output=True)
                except Exception as e:
                    print(f"[ProjectBuilder] WARNING: Failed Docker SVN setup: {e}")

            try:
                vcs_type = self.config_factory.get_vcs_adapter_type()
                final_repo_url = f"{base_repo_url}/{folder_name}/{vfs_svn}" if "localhost" in base_repo_url else f"{base_repo_url}/{folder_name}/{vfs_svn}"
                
                vcs_root = project_path / vfs_svn
                router = VCSRouter(vcs_type=vcs_type, repo_url=final_repo_url, workspace_dir=vcs_root)
                adapter = router.get_adapter()
                
                if vcs_user and vcs_pwd:
                    adapter.full_pull(username=vcs_user, password=vcs_pwd)
                    print("[ProjectBuilder] Registering untracked files to VCS...")
                    
                    if hasattr(adapter, '_run_subprocess'):
                        adapter._run_subprocess(["svn", "add", "--force", "."], cwd=vcs_root)
                    else:
                        subprocess.run(["svn", "add", "--force", "."], cwd=vcs_root, check=False, capture_output=True)
                        
                    adapter.commit(
                        message="Initial commit: Hub Project Blueprint and Edit Master", 
                        paths=["."], 
                        username=vcs_user, 
                        password=vcs_pwd
                    )
                else:
                    print("[ProjectBuilder] No VCS credentials provided. Skipping initial commit.")
            except Exception as e:
                print(f"[ProjectBuilder] Warning: Initial VCS commit failed: {e}")

            return True, f"Project '{folder_name}' successfully generated."

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n[ProjectBuilder] CRASH FATAL (Stacktrace):\n{error_trace}\n")
            return False, f"System error creating directory tree: {str(e)}"

    def _extract_dependencies_for_headless(self, extensions_dir: Path, dependencies: dict):
        """Extrae el Add-on de Kitsu en el Sandboxing VFS para que Blender lo encuentre durante la ejecución Headless."""
        addons_dict = dependencies.get("addons", {})
        
        for addon_name, addon_version in addons_dict.items():
            if "kitsu" in addon_name.lower():
                print(f"[ProjectBuilder] Buscando binario para {addon_name} v{addon_version}...")
                
                boveda_addons = self.vault_root / "addons"
                kitsu_zip = None
                
                if boveda_addons.exists():
                    for archivo in boveda_addons.rglob("*.zip"):
                        if addon_name.lower() in archivo.name.lower():
                            kitsu_zip = archivo
                            break
                            
                if kitsu_zip:
                    safe_folder = "blender_kitsu"
                    destino = extensions_dir / safe_folder

                    destino.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        import zipfile
                        with zipfile.ZipFile(kitsu_zip, 'r') as zf:
                            zf.extractall(destino)
                        print(f"[ProjectBuilder] Extension extraída en Sandbox desde {kitsu_zip.name}.")
                    except Exception as e:
                        print(f"[ProjectBuilder] Error extrayendo ZIP: {e}")
                else:
                    print(f"[ProjectBuilder] WARNING: No se encontro el ZIP para {addon_name} en {boveda_addons}")

    def _inicializar_shot_builder(self, blender_version: str, project_path: Path, vfs_svn: str, vfs_local: str, project_id: str, kitsu_user: str, kitsu_pwd: str, dependencies: dict):
        """
        Extrae Blender temporalmente y lo ejecuta en modo Headless.
        Inyecta un script puente que resuelve dinámicamente el nombre del addon Kitsu,
        autentica la sesión, establece el caché del proyecto, y delega al headless_builder.py.
        """
        os_name = self._get_os_info()
        kitsu_host = self.config_factory.get_kitsu_api_url()
        templates_dir = Path(__file__).parent / "templates"
        
        sandbox_dir = project_path / vfs_local / "blender_data"
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        extensions_dir = sandbox_dir / "extensions" / "user_default"
        extensions_dir.mkdir(parents=True, exist_ok=True)
        
        # Extracción JIT de las extensiones vitales antes de arrancar
        self._extract_dependencies_for_headless(extensions_dir, dependencies)
        
        headless_env = os.environ.copy()
        headless_env["BLENDER_USER_RESOURCES"] = str(sandbox_dir)
        headless_env["BLENDER_USER_CONFIG"] = str(sandbox_dir / "config")
        headless_env["BLENDER_USER_SCRIPTS"] = str(sandbox_dir / "scripts")
        headless_env["OPENSTUDIO_BUILD_TARGET"] = "EDIT"
        
        if os_name == "windows":
            archive_name = f"blender-{blender_version}-windows-x64.zip"
        elif os_name == "linux":
            archive_name = f"blender-{blender_version}-linux-x64.tar.xz"
        else:
            archive_name = f"blender-{blender_version}-macos-x64.dmg"

        archive_path = self.vault_blender_dir / archive_name

        if not archive_path.exists():
            print(f"[ProjectBuilder] WARNING: Archive {archive_name} not found. Skipping Headless Hook Setup.")
            return

        print(f"[ProjectBuilder] Extracting {archive_name} temporarily for Headless execution...")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            try:
                if archive_path.suffix == '.zip':
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        zf.extractall(tmp_path)
                elif '.tar' in archive_path.name or archive_path.suffix == '.xz':
                    with tarfile.open(archive_path, 'r:*') as tf:
                        tf.extractall(tmp_path)
            except Exception as e:
                print(f"[ProjectBuilder] WARNING: Extraction failed: {e}")
                return

            blender_bin = None
            for root, dirs, files in os.walk(tmp_path):
                if os_name == "windows" and "blender.exe" in files:
                    blender_bin = Path(root) / "blender.exe"
                    break
                elif os_name == "linux" and "blender" in files:
                    blender_bin = Path(root) / "blender"
                    break
                elif os_name == "macos" and "Blender" in files and "MacOS" in root:
                    blender_bin = Path(root) / "Blender"
                    break

            if not blender_bin:
                return

            script_content = f"""
import bpy
import sys
import importlib
import addon_utils
from pathlib import Path

try:
    print("[ProjectBuilder] Refrescando repositorios de extensiones locales...")
    addon_utils.modules(refresh=True)
    
    print("[ProjectBuilder] Inyectando Repositorio de Extensiones Local (Sandboxing 4.2+)...")
    prefs = bpy.context.preferences
    if hasattr(prefs, "extensions") and hasattr(prefs.extensions, "repos"):
        repos = prefs.extensions.repos
        repo = repos.get("OpenStudio_Local_Vault")
        if not repo:
            repo = repos.new(name="OpenStudio_Local_Vault")
        repo.enabled = True
        repo.use_custom_directory = True
        repo.custom_directory = r"{extensions_dir.as_posix()}"
        repo.source = 'USER'
        print("[ProjectBuilder] Repositorio de Extensiones anclado exitosamente.")
    
    kitsu_module = "bl_ext.user_default.blender_kitsu"
    try:
        bpy.ops.preferences.addon_enable(module=kitsu_module)
        print(f"[ProjectBuilder] Extension {{kitsu_module}} activada exitosamente.")
    except Exception as e:
        print("[ProjectBuilder] Fallback: Intentando cargar como Add-on clasico...")
        kitsu_module = "blender_kitsu"
        bpy.ops.preferences.addon_enable(module=kitsu_module)
        
    if kitsu_module != "blender_kitsu":
        sys.modules["blender_kitsu"] = importlib.import_module(kitsu_module)
        sys.modules["blender_kitsu.shot_builder"] = importlib.import_module(f"{{kitsu_module}}.shot_builder")
        sys.modules["blender_kitsu.shot_builder.ops"] = importlib.import_module(f"{{kitsu_module}}.shot_builder.ops")

    addon_prefs = bpy.context.preferences.addons[kitsu_module].preferences
    
    # Inyección VFS -> Garantiza que el archivo se guarde en la ruta del repositorio SVN local
    addon_prefs.project_root_dir = r"{project_path.as_posix()}"
    # Enrutamiento estructural de archivos .blend (VCS / SVN)
    if hasattr(addon_prefs, "shot_dir_name"): addon_prefs.shot_dir_name = r"{vfs_svn}/pro/shots"
    if hasattr(addon_prefs, "asset_dir_name"): addon_prefs.asset_dir_name = r"{vfs_svn}/pro/assets"
    if hasattr(addon_prefs, "seq_dir_name"): addon_prefs.seq_dir_name = r"{vfs_svn}/pre/strips"
    if hasattr(addon_prefs, "edit_dir_name"): addon_prefs.edit_dir_name = r"{vfs_svn}/edit"
    
    # Enrutamiento estructural de Media y Renders (SHARED) según el estándar del estudio
    if hasattr(addon_prefs, "shot_playblast_root_dir"): addon_prefs.shot_playblast_root_dir = r"{{vfs_shared}}/editorial/footage"
    if hasattr(addon_prefs, "seq_playblast_root_dir"): addon_prefs.seq_playblast_root_dir = r"{{vfs_shared}}/editorial/footage"
    if hasattr(addon_prefs, "frames_root_dir"): addon_prefs.frames_root_dir = r"{{vfs_shared}}/editorial/footage"
    if hasattr(addon_prefs, "edit_export_dir"): addon_prefs.edit_export_dir = r"{{vfs_shared}}/editorial/export"
    if hasattr(addon_prefs, "farm_dir"): addon_prefs.farm_dir = "render"

    print("[ProjectBuilder] Rutas de Kitsu enrutadas correctamente a VFS_SVN y VFS_SHARED")
    
    # Autenticación Silenciosa
    addon_prefs.host = r"{kitsu_host}"
    addon_prefs.email = r"{kitsu_user}"
    addon_prefs.passwd = r"{kitsu_pwd}"
    
    print("[ProjectBuilder] Autenticando Sesion en Blender...")
    bpy.ops.kitsu.session_start('EXEC_DEFAULT')
    bpy.ops.kitsu.con_productions_load('EXEC_DEFAULT')
    
    try:
        kitsu_cache = importlib.import_module(f"{{kitsu_module}}.cache")
        kitsu_cache.project_active_set_by_id(bpy.context, "{project_id}")
        addon_prefs.project_active_id = "{project_id}"
    except Exception as cache_err:
        print("[ProjectBuilder] Error en cache:", cache_err)

    if hasattr(bpy.ops.kitsu, "build_config_save_hooks"):
        bpy.ops.kitsu.build_config_save_hooks('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_settings('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_templates('EXEC_DEFAULT')
        
    print("[ProjectBuilder] Delegando al Headless Builder de la Boveda...")
    sys.path.append(r"{templates_dir.as_posix()}")
    import headless_builder
    headless_builder.main()
    
except Exception as e:
    import traceback
    print(f"[HEADLESS ERROR] Failure during Pre-Flight configuration:\\n{{traceback.format_exc()}}")
"""
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                    temp_script.write(script_content)
                    temp_script_path = temp_script.name

                print(f"[ProjectBuilder] Launching Headless Blender v{blender_version}...")
                
                # Ejecutar con el ENVIRONMENT BLINDADO (headless_env)
                result = subprocess.run(
                    [str(blender_bin), "-b", "--python", temp_script_path], 
                    env=headless_env,
                    check=False, 
                    capture_output=True, 
                    text=True
                )
                
                print(f"[HEADLESS BLENDER STDOUT]\n{result.stdout}")
                if result.stderr:
                    print(f"[HEADLESS BLENDER STDERR]\n{result.stderr}")

                os.remove(temp_script_path)
            except Exception as e:
                import traceback
                print(f"[ProjectBuilder] Critical failure invoking Headless subprocess:\n{traceback.format_exc()}")
