# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/project_builder.py
# Rol Arquitectónico: I/O Orchestrator / Project Generator (B2B Multi-OS)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.8.4 (Compressed Headless Execution)
# =========================================================================================

"""
Isolated Input/Output (I/O) operations engine.
Scaffolds the studio's directory tree on the NAS based on Semantic Topography mapping.
Copies master templates, generates project_init.json payloads, and executes 
Headless Blender initialization. Fully bound to dynamic ConfigFactory states.
"""

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

            self._inicializar_shot_builder(blender_version, project_path, vfs_pipe)

            # -------------------------------------------------------------------------------------
            # 7.5 AUTO-PROVISIONAMIENTO DEL REPOSITORIO (DEMO DOCKER)
            # -------------------------------------------------------------------------------------
            base_repo_url = self.config_factory.get_vcs_repository_url()
            
            if "localhost" in base_repo_url:
                # Override hardcoded de credenciales para el entorno local (Demo)
                vcs_user = "admin"
                vcs_pwd = "admin123"
                
                try:
                    print(f"[ProjectBuilder] Provisioning local SVN repo: {folder_name} inside Docker...")
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "svnadmin", "create", f"/home/svn/{folder_name}"], check=True)
                    
                    conf_cmd = (
                        f"echo '[general]' > /home/svn/{folder_name}/conf/svnserve.conf && "
                        f"echo 'anon-access = none' >> /home/svn/{folder_name}/conf/svnserve.conf && "
                        f"echo 'auth-access = write' >> /home/svn/{folder_name}/conf/svnserve.conf && "
                        f"echo 'password-db = passwd' >> /home/svn/{folder_name}/conf/svnserve.conf"
                    )
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", conf_cmd], check=True)
                    
                    # Credenciales inyectadas de forma estática en el contenedor
                    pwd_cmd = f"echo '[users]' > /home/svn/{folder_name}/conf/passwd && echo 'admin = admin123' >> /home/svn/{folder_name}/conf/passwd"
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", pwd_cmd], check=True)
                    
                    mkdir_cmd = f"svn mkdir file:///home/svn/{folder_name}/{vfs_svn} -m 'Init Hub Topology'"
                    subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", mkdir_cmd], check=True)
                except Exception as e:
                    print(f"[ProjectBuilder] WARNING: Failed to provision Docker SVN (might already exist): {e}")

            # -------------------------------------------------------------------------------------
            # 8. VCS COMMIT INICIAL
            # -------------------------------------------------------------------------------------
            try:
                vcs_type = self.config_factory.get_vcs_adapter_type()
                final_repo_url = f"{base_repo_url}/{folder_name}/{vfs_svn}" if "localhost" in base_repo_url else f"{base_repo_url}/{folder_name}/{vfs_svn}"
                
                vcs_root = project_path / vfs_svn
                router = VCSRouter(vcs_type=vcs_type, repo_url=final_repo_url, workspace_dir=vcs_root)
                adapter = router.get_adapter()
                
                if vcs_user and vcs_pwd:
                    # 1. Enlazar la carpeta local con el servidor SVN (.svn)
                    adapter.full_pull(username=vcs_user, password=vcs_pwd)
                    
                    # 2. Registrar TODOS los archivos y plantillas nuevas en el radar de SVN
                    print("[ProjectBuilder] Registering untracked files to VCS...")
                    subprocess.run(["svn", "add", "--force", str(vcs_root)], check=False, capture_output=True)
                    
                    # 3. Subir el Blueprint oficial
                    adapter.commit(
                        message="Initial commit: Hub Project Blueprint (project_init.json)", 
                        paths=[str(payload_file_svn)], 
                        username=vcs_user, 
                        password=vcs_pwd
                    )
                else:
                    print("[ProjectBuilder] No VCS credentials provided. Skipping initial commit.")
            except Exception as e:
                print(f"[ProjectBuilder] Warning: Initial VCS commit failed: {e}")

            return True, f"Project '{folder_name}' successfully generated."

        except Exception as e:
            return False, f"System error creating directory tree: {str(e)}"

    def _inicializar_shot_builder(self, blender_version: str, project_path: Path, pipeline_folder: str):
        """
        Invokes Blender in Headless mode (background) to generate JSON files.
        Intelligently extracts the compressed vault archive into a Temp directory, 
        executes the hook, and automatically purges the binary cache[cite: 6].
        """
        os_name = self._get_os_info()
        
        # Mapeo de archivos comprimidos
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
        
        # Descompresión volátil controlada por el recolector de basura
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            try:
                if archive_path.suffix == '.zip':
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        zf.extractall(tmp_path)
                elif '.tar' in archive_path.name or archive_path.suffix == '.xz':
                    with tarfile.open(archive_path, 'r:*') as tf:
                        tf.extractall(tmp_path)
                else:
                    print(f"[ProjectBuilder] WARNING: Unsupported archive format {archive_path.suffix}.")
                    return
            except Exception as e:
                print(f"[ProjectBuilder] WARNING: Extraction failed: {e}")
                return

            # Búsqueda profunda del binario dentro del contenedor extraído
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

            if not blender_bin or not blender_bin.exists():
                print(f"[ProjectBuilder] WARNING: Binary not found inside extracted archive. Skipping Hook.")
                return

            # --- SCRIPT HEADLESS ---
            script_content = f"""
import bpy
import addon_utils

try:
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.blender_kitsu")
    
    prefs = bpy.context.preferences.addons["bl_ext.user_default.blender_kitsu"].preferences
    prefs.project_root_dir = r"{project_path.as_posix()}"
    
    if hasattr(bpy.ops.kitsu, "build_config_save_hooks"):
        bpy.ops.kitsu.build_config_save_hooks('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_settings('EXEC_DEFAULT')
        bpy.ops.kitsu.build_config_save_templates('EXEC_DEFAULT')
        print("[HEADLESS OK] Shot Builder configuration sealed.")
    else:
        print("[HEADLESS WARNING] Kitsu operators missing.")
except Exception as e:
    print("[HEADLESS ERROR] Failure during Shot Builder configuration:", e)
"""
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                    temp_script.write(script_content)
                    temp_script_path = temp_script.name

                print(f"[ProjectBuilder] Launching Headless Blender v{blender_version}...")
                subprocess.run([str(blender_bin), "-b", "--python", temp_script_path], check=False, capture_output=True)
                os.remove(temp_script_path)
            except Exception as e:
                print(f"[ProjectBuilder] Critical failure invoking Headless subprocess: {e}")
