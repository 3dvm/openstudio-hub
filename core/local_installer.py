import json
import shutil
import zipfile
import tarfile
import platform
import os
from pathlib import Path
from .vcs_router import VCSRouter

class LocalInstaller:
    def __init__(self, nextcloud_dir: Path, config_factory):
        self.nextcloud_dir = nextcloud_dir
        self.config_factory = config_factory # Inyectado desde el Hub
        # Definimos la ruta de la boveda global de software dentro de Nextcloud
        self.boveda_addons = nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "addons"
        self.boveda_blender = nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "blender_versions"

    def verificar_instalacion(self, project_root: Path) -> bool:
        """
            Verifica si el proyecto ya fue instalado localmente en esta PC.
            Revisa la existencia del JSON local y la carpeta de produccion.
        """
        config_local = project_root / "06_conf_LOCAL" / "project_config.json"
        vcs_dir = project_root / "02_archivos_de_produccion"
        return config_local.exists() and vcs_dir.exists()

    def _get_os_info(self):
        """Detecta el sistema operativo para buscar la extensión correcta."""
        system = platform.system().lower()
        if system == "linux":
            return "linux", "tar.xz"
        elif system == "windows":
            return "windows", "zip"
        else:
            return "macos", "dmg"

    def _instalar_blender(self, project_root: Path, version: str, status_callback):
        """Busca el comprimido en la bóveda y lo extrae en el 06_conf_LOCAL del proyecto."""
        os_name, ext = self._get_os_info()
        archive_name = f"blender-{version}-{os_name}-x64.{ext}"
        archive_path = self.boveda_blender / archive_name

        # Destino local: [proyecto]/06_conf_LOCAL/blender-build
        dest_dir = project_root / "06_conf_LOCAL" / "blender-build"
        folder_name_extracted = f"blender-{version}-{os_name}-x64"
        final_exec_dir = dest_dir / folder_name_extracted

        if final_exec_dir.exists():
            status_callback(f"Blender {version} ya está listo en caché local.", "white")
            return

        if not archive_path.exists():
            raise FileNotFoundError(f"No se encontró el instalador en la bóveda: {archive_path}")

        status_callback(f"Extrayendo Blender {version} (Esto tomará un par de minutos)...", "yellow")
        dest_dir.mkdir(parents=True, exist_ok=True)

        if ext == "tar.xz":
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(path=dest_dir)
        elif ext == "zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)

        status_callback(f"Blender {version} extraído con éxito.", "green")

    def _gestionar_vcs(self, project_root: Path, vcs_user: str, vcs_pwd: str, status_callback) -> bool:
        """
        Orquesta la comunicación con el Abstract Factory (VCSRouter) aislando los comandos CLI.
        """
        vcs_root = project_root / "02_archivos_de_produccion"
        
        vcs_type = self.config_factory.get_vcs_adapter_type()
        base_repo_url = self.config_factory.get_vcs_repository_url()
        
        project_name_safe = project_root.name.replace("-", "_") 
        final_repo_url = f"{base_repo_url}/{project_name_safe}/02_archivos_de_produccion"

        router = VCSRouter(vcs_type=vcs_type, repo_url=final_repo_url, workspace_dir=vcs_root)
        adapter = router.get_adapter()
        
        status_callback(f"Sincronizando Workspace con {vcs_type.upper()}...", "yellow")
        
        try:
            adapter.full_pull(username=vcs_user, password=vcs_pwd)
            status_callback(f"{vcs_type.upper()}: Sincronización completada con éxito.", "green")
            return True
        except RuntimeError as e:
            status_callback(f"Fallo de conexión al repositorio: Revisa tus credenciales o conexión.", "red")
            print(f"[MACUARE HUB] Error en Controlador VCS: {e}")
            return False

    def instalar_entorno(self, project_root: Path, vcs_user: str, vcs_pwd: str, status_callback) -> tuple[bool, str]:
        """
            Ejecuta el despliegue del entorno local del artista.
        """
        init_json_path = project_root / "05_config_estudio" / "project_init.json"
        
        if not init_json_path.exists():
            return False, "Error: No se encontro la semilla global project_init.json"

        try:
            status_callback("Leyendo configuracion global...", "yellow")
            with open(init_json_path, 'r', encoding='utf-8') as f:
                init_data = json.load(f)

            project_name = init_data.get("project_name", project_root.name)
            blender_version = init_data.get("blender_version", "5.1.2")
            dependencies = init_data.get("dependencies", {})

            # === FAIL FAST: Verificamos credenciales y conexión de red ANTES de extraer Blender ===
            checkout_ok = self._gestionar_vcs(project_root, vcs_user, vcs_pwd, status_callback)
            
            if not checkout_ok:
                # Abortamos de inmediato. El JSON local no se creará, previniendo el falso positivo.
                return False, "Conexión al repositorio rechazada. Instalación abortada."

            # Si el VCS fue exitoso, continuamos con las tareas pesadas de disco
            self._instalar_blender(project_root, blender_version, status_callback)

            template_name = init_data.get("template", "Macuare_Estudio")
            self._instalar_template(project_root, template_name, blender_version, status_callback)

            status_callback("Sincronizando extensiones del proyecto...", "yellow")
            self._sincronizar_addons(project_root, dependencies, status_callback)
            
            # Conectar tuberias (Symlinks para cachés pesados)
            vcs_root = project_root / "02_archivos_de_produccion"
            status_callback("Configurando symlinks de produccion...", "yellow")
            self._crear_symlinks(project_path=project_root, svn_path=vcs_root)

            # Generar el ADN Local mutado (project_config.json)
            status_callback("Generando archivo de configuracion local...", "yellow")
            
            config_local_dir = project_root / "06_conf_LOCAL"
            config_local_dir.mkdir(exist_ok=True)

            local_config_data = {
                "project_name": project_name,
                "blender_version": blender_version,
                "kitsu_host": init_data.get("kitsu_host", "https://proyectos.macuare.com.ve"),
                "dependencies": dependencies,
                "paths": {
                    "root": str(project_root),
                    "svn_root": str(vcs_root),
                    "assets": str(vcs_root / "pro" / "assets"),
                    "shots": str(vcs_root / "pro" / "shots"),
                    "render_output": str(project_root / "03_render" / "footage"),
                    "deliverables": str(project_root / "03_render" / "deliver")
                }
            }

            config_local_file = config_local_dir / "project_config.json"
            with open(config_local_file, 'w', encoding='utf-8') as f:
                json.dump(local_config_data, f, indent=4)
            
            return True, "Entorno local instalado y verificado con exito."

        except Exception as e:
            return False, f"Error critico durante la instalacion: {str(e)}"

    def _sincronizar_addons(self, project_root: Path, dependencies: dict, status_callback):
        extensions_dir = project_root / "06_conf_LOCAL" / "blender_data" / "extensions" / "user_default"
        extensions_dir.mkdir(parents=True, exist_ok=True)

        for addon_name, version in dependencies.items():
            nombre_archivo = f"{addon_name}_{version}.zip"
            origen_addon_zip = self.boveda_addons / nombre_archivo
            destino_addon = extensions_dir / addon_name

            if origen_addon_zip.exists():
                if not destino_addon.exists():
                    status_callback(f"Desplegando extension: {addon_name} (v{version})...", "yellow")
                    destino_addon.mkdir(parents=True, exist_ok=True)
                    try:
                        with zipfile.ZipFile(origen_addon_zip, 'r') as zip_ref:
                            zip_ref.extractall(destino_addon)
                    except zipfile.BadZipFile:
                        status_callback(f"Error: El archivo {nombre_archivo} esta corrupto.", "red")
            else:
                status_callback(f"Advertencia: No se encontro la extension {nombre_archivo} en la boveda.", "red")

    def _crear_symlinks(self, project_path: Path, svn_path: Path):
        render_root = project_path / "03_render"
        edit_dir = svn_path / "edit"
        edit_dir.mkdir(parents=True, exist_ok=True)
        folders_to_link = ["footage", "deliver", "export"]

        for folder in folders_to_link:
            link_path = edit_dir / folder       
            target_path = render_root / folder  
            target_path.mkdir(parents=True, exist_ok=True)
            if not link_path.exists() and not link_path.is_symlink():
                link_path.symlink_to(target_path, target_is_directory=True)

    def _instalar_template(self, project_root: Path, template_name: str, blender_version: str, status_callback):
        source_path = self.nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "templates" / template_name
        if not source_path.exists():
            status_callback(f"Advertencia: No se encontró la plantilla '{template_name}'.", "red")
            return

        os_name, _ = self._get_os_info()
        ver_major = ".".join(blender_version.split(".")[:2])
        blender_folder = f"blender-{blender_version}-{os_name}-x64"
        dest_path = (
            project_root / "06_conf_LOCAL" / "blender-build" / blender_folder / 
            ver_major / "scripts" / "startup" / "bl_app_templates_system" / template_name
        )

        status_callback(f"Inyectando plantilla '{template_name}' en contenedor aislado...", "yellow")
        if dest_path.exists():
            shutil.rmtree(dest_path)
            
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_path, dest_path, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
        
        splash_custom = project_root / "05_config_estudio" / "splash.png"
        if splash_custom.exists():
            shutil.copy(splash_custom, dest_path / "splash.png")
