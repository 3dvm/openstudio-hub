# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/local_installer.py
# Rol Arquitectónico: Deployment Engine / Jailing Router
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0
# =========================================================================================

"""
Motor de despliegue y orquestación local.
Ejecuta la clonación inicial del VCS, extrae herramientas en aislamiento (local/),
resuelve Symlinks VFS (shared/) y bifurca la sincronización (Full vs Sparse Jailing).
"""

import json
import shutil
import zipfile
import tarfile
import platform
import os
from pathlib import Path
from typing import Tuple, Dict, Optional

from .vcs_router import VCSRouter
from core.sparse_manager import SparseManager

class LocalInstaller:
    def __init__(self, nextcloud_dir: Path, config_factory):
        self.nextcloud_dir = nextcloud_dir
        self.config_factory = config_factory 
        
        # Resolución dinámica de la Bóveda alineada con B2B
        try:
            self.vault_root = self.config_factory.get_workspace_root() / "openstudio_vault"
        except Exception:
            self.vault_root = self.nextcloud_dir.parent / "openstudio_vault"

        self.boveda_addons = self.vault_root / "addons"
        self.boveda_blender = self.vault_root / "blender_binaries"
        self.boveda_templates = self.vault_root / "project_templates"

    def verificar_instalacion(self, project_root: Path) -> bool:
        """
        Verifica si el proyecto ya fue instalado localmente en esta PC.
        Revisa la existencia del JSON local y la carpeta de control de versiones.
        """
        prod_folder = self.config_factory.get_production_folder_name()
        config_local = project_root / "local" / "project_config.json"
        vcs_dir = project_root / prod_folder
        return config_local.exists() and vcs_dir.exists()

    def _get_os_info(self) -> Tuple[str, str]:
        system = platform.system().lower()
        if system == "linux":
            return "linux", "tar.xz"
        elif system == "windows":
            return "windows", "zip"
        else:
            return "macos", "dmg"

    def _instalar_blender(self, project_root: Path, version: str, status_callback):
        """Busca el comprimido en la bóveda y lo extrae en local/blender-build del proyecto."""
        os_name, ext = self._get_os_info()
        archive_name = f"blender-{version}-{os_name}-x64.{ext}"
        archive_path = self.boveda_blender / archive_name

        dest_dir = project_root / "local" / "blender-build"
        folder_name_extracted = f"blender-{version}-{os_name}-x64"
        final_exec_dir = dest_dir / folder_name_extracted

        if final_exec_dir.exists():
            status_callback(f"Blender {version} is already cached locally.", "white")
            return

        if not archive_path.exists():
            raise FileNotFoundError(f"Installer not found in Vault: {archive_path}")

        status_callback(f"Extracting Blender {version} (This will take a couple of minutes)...", "yellow")
        dest_dir.mkdir(parents=True, exist_ok=True)

        if ext == "tar.xz":
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(path=dest_dir)
        elif ext == "zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)

        status_callback(f"Blender {version} extracted successfully.", "green")

    def _gestionar_vcs(self, project_root: Path, vcs_user: str, vcs_pwd: str, status_callback, 
                       user_role: str, task_metadata: Optional[Dict[str, str]]) -> bool:
        """Bifurcador RBAC: Evalúa el rol y orquesta la clonación (Full Pull vs Sparse Jailing)."""
        prod_folder = self.config_factory.get_production_folder_name()
        vcs_root = project_root / prod_folder
        
        vcs_type = self.config_factory.get_vcs_adapter_type()
        base_repo_url = self.config_factory.get_vcs_repository_url()
        final_repo_url = f"{base_repo_url}/{project_root.name}/{prod_folder}"

        router = VCSRouter(vcs_type=vcs_type, repo_url=final_repo_url, workspace_dir=vcs_root)
        
        is_sparse_enabled = getattr(self.config_factory, 'is_vendor_sparse_enabled', lambda: True)()
        
        # === BIFURCACIÓN DE JAILING ===
        if user_role == "vendor" and is_sparse_enabled:
            sparse_manager = SparseManager(vcs_router=router, status_callback=status_callback)
            success = sparse_manager.setup_vendor_workspace(task_metadata, vcs_user, vcs_pwd)
            return success
        
        # === FULL CHECKOUT (Staff: Artists, Leads, TDs) ===
        adapter = router.get_adapter()
        status_callback(f"Synchronizing Full Workspace with {vcs_type.upper()}...", "yellow")
        
        try:
            adapter.full_pull(username=vcs_user, password=vcs_pwd)
            status_callback(f"{vcs_type.upper()}: Synchronization completed successfully.", "green")
            return True
        except RuntimeError as e:
            status_callback("Repository connection failed: Check your credentials or network.", "red")
            print(f"[MACUARE HUB] VCS Driver Error: {e}")
            return False

    def instalar_entorno(self, project_root: Path, vcs_user: str, vcs_pwd: str, status_callback,
                         user_role: str = "artist", task_metadata: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
        """
        Ejecuta el despliegue del entorno local del artista de forma secuencial.
        """
        prod_folder = self.config_factory.get_production_folder_name()
        vcs_root = project_root / prod_folder

        try:
            # 1. FAIL FAST: Clonamos el VCS primero para descargar la configuración del pipeline
            status_callback("Authenticating and syncing VCS workspace...", "yellow")
            checkout_ok = self._gestionar_vcs(
                project_root, vcs_user, vcs_pwd, status_callback, user_role, task_metadata
            )
            
            if not checkout_ok:
                return False, ""

            # 2. Lectura del Payload Estructural
            init_json_path = vcs_root / "pipeline" / "project_init.json"
            
            if not init_json_path.exists():
                return False, f"Critical: project_init.json not found in {prod_folder}/pipeline/ after VCS sync."

            status_callback("Reading global pipeline configuration...", "yellow")
            with open(init_json_path, 'r', encoding='utf-8') as f:
                init_data = json.load(f)

            project_name = init_data.get("project_name", project_root.name)
            blender_version = init_data.get("blender_version", "5.1.2")
            dependencies = init_data.get("dependencies", {})

            # 3. Instalación de Blender Aislado
            self._instalar_blender(project_root, blender_version, status_callback)

            # 4. Inyección de Plantillas de Estudio
            template_name = init_data.get("template", "Macuare_Estudio")
            self._instalar_template(project_root, template_name, blender_version, status_callback)

            # 5. Extensiones y Add-ons
            status_callback("Deploying project extensions...", "yellow")
            self._sincronizar_addons(project_root, dependencies, status_callback)
            
            # 6. Conexión de Tuberías VFS (Symlinks)
            status_callback("Configuring production VFS symlinks...", "yellow")
            self._crear_symlinks(project_path=project_root, svn_path=vcs_root)

            # 7. Sello Mutado (Local ADN)
            status_callback("Generating local workspace configuration...", "yellow")
            
            config_local_dir = project_root / "local"
            config_local_dir.mkdir(exist_ok=True)

            local_config_data = {
                "project_name": project_name,
                "blender_version": blender_version,
                "kitsu_host": init_data.get("kitsu_host", self.config_factory.get_kitsu_api_url()),
                "dependencies": dependencies,
                "paths": {
                    "root": str(project_root),
                    "svn_root": str(vcs_root),
                    "assets": str(vcs_root / "pro" / "assets"),
                    "shots": str(vcs_root / "pro" / "shots"),
                    "render_output": str(project_root / "shared" / "editorial" / "footage"),
                    "deliverables": str(project_root / "shared" / "editorial" / "deliver")
                }
            }

            config_local_file = config_local_dir / "project_config.json"
            with open(config_local_file, 'w', encoding='utf-8') as f:
                json.dump(local_config_data, f, indent=4)
            
            return True, "Local workspace installed and verified successfully."

        except Exception as e:
            return False, f"Critical error during local installation: {str(e)}"

    def _sincronizar_addons(self, project_root: Path, dependencies: dict, status_callback):
        extensions_dir = project_root / "local" / "blender_data" / "extensions" / "user_default"
        extensions_dir.mkdir(parents=True, exist_ok=True)

        for addon_name, version in dependencies.items():
            nombre_archivo = f"{addon_name}_{version}.zip"
            origen_addon_zip = self.boveda_addons / nombre_archivo
            destino_addon = extensions_dir / addon_name

            if origen_addon_zip.exists():
                if not destino_addon.exists():
                    status_callback(f"Deploying extension: {addon_name} (v{version})...", "yellow")
                    destino_addon.mkdir(parents=True, exist_ok=True)
                    try:
                        with zipfile.ZipFile(origen_addon_zip, 'r') as zip_ref:
                            zip_ref.extractall(destino_addon)
                    except zipfile.BadZipFile:
                        status_callback(f"Error: Archive {nombre_archivo} is corrupted.", "red")
            else:
                status_callback(f"Warning: Extension {nombre_archivo} not found in Vault.", "red")

    def _crear_symlinks(self, project_path: Path, svn_path: Path):
        """Mapea las carpetas efímeras (shared/editorial) hacia el working copy del VCS."""
        shared_edit_dir = project_path / "shared" / "editorial"
        svn_edit_dir = svn_path / "edit"
        svn_edit_dir.mkdir(parents=True, exist_ok=True)
        
        folders_to_link = ["footage", "deliver", "export"]

        for folder in folders_to_link:
            target_path = shared_edit_dir / folder  
            target_path.mkdir(parents=True, exist_ok=True)
            
            link_path = svn_edit_dir / folder       
            if not link_path.exists() and not link_path.is_symlink():
                try:
                    link_path.symlink_to(target_path, target_is_directory=True)
                except OSError as e:
                    print(f"[VFS WARNING] Symlink creation failed (Privilege issue?): {e}")

    def _instalar_template(self, project_root: Path, template_name: str, blender_version: str, status_callback):
        source_path = self.boveda_templates / template_name
        if not source_path.exists():
            status_callback(f"Warning: Project template '{template_name}' not found.", "red")
            return

        os_name, _ = self._get_os_info()
        ver_major = ".".join(blender_version.split(".")[:2])
        blender_folder = f"blender-{blender_version}-{os_name}-x64"
        dest_path = (
            project_root / "local" / "blender-build" / blender_folder / 
            ver_major / "scripts" / "startup" / "bl_app_templates_system" / template_name
        )

        status_callback(f"Injecting template '{template_name}' into isolated container...", "yellow")
        if dest_path.exists():
            shutil.rmtree(dest_path)
            
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_path, dest_path, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
        
        splash_custom = project_root / "svn" / "pipeline" / "splash.png"
        if splash_custom.exists():
            shutil.copy(splash_custom, dest_path / "splash.png")
