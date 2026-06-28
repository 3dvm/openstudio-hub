import json
import shutil
import subprocess
import zipfile
from pathlib import Path

class LocalInstaller:
    def __init__(self, nextcloud_dir: Path):
        self.nextcloud_dir = nextcloud_dir
        # Definimos la ruta de la boveda global de software dentro de Nextcloud
        self.boveda_addons = nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "addons"

    def verificar_instalacion(self, project_root: Path) -> bool:
        """
        Verifica si el proyecto ya fue instalado localmente en esta PC.
        Revisa la existencia del JSON local y la carpeta de produccion.
        """
        config_local = project_root / "06_conf_LOCAL" / "project_config.json"
        svn_dir = project_root / "02_archivos_de_produccion"
        return config_local.exists() and svn_dir.exists()

    def instalar_entorno(self, project_root: Path, status_callback) -> tuple[bool, str]:
        """
        Ejecuta el despliegue del entorno local del artista.
        Mapea JSON, crea symlinks y sincroniza los add-ons congelados.
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

            # 1. Preparar repositorio local de produccion (SVN Receptaculo)
            svn_root = project_root / "02_archivos_de_produccion"
            svn_root.mkdir(exist_ok=True)

            # 2. Sincronizacion de Add-ons congelados (La nueva funcionalidad)
            status_callback("Sincronizando add-ons del proyecto...", "yellow")
            self._sincronizar_addons(project_root, dependencies, status_callback)

            # 3. Conectar tuberias (Symlinks para Blender Studio Tools)
            status_callback("Configurando symlinks de produccion...", "yellow")
            self._crear_symlinks(project_path=project_root, svn_path=svn_root)

            # 4. Generar el ADN Local mutado (project_config.json)
            status_callback("Generando archivo de configuracion local...", "yellow")
            
            config_local_dir = project_root / "06_conf_LOCAL"
            config_local_dir.mkdir(exist_ok=True)

            local_config_data = {
                "project_name": project_name,
                "blender_version": blender_version,
                "kitsu_host": init_data.get("kitsu_host", "https://proyectos.macuare.com.ve"),
                "paths": {
                    "root": str(project_root),
                    "svn_root": str(svn_root),
                    "assets": str(svn_root / "pro" / "assets"),
                    "shots": str(svn_root / "pro" / "shots"),
                    "render_output": str(project_root / "03_render" / "footage"),
                    "deliverables": str(project_root / "03_render" / "deliver")
                }
            }

            config_local_file = config_local_dir / "project_config.json"
            with open(config_local_file, 'w', encoding='utf-8') as f:
                json.dump(local_config_data, f, indent=4)

            # 5. Validacion de SVN (Informar si falta el Checkout)
            if not (svn_root / ".svn").exists():
                return True, "Instalacion completada. Copia de trabajo SVN requerida."
            
            return True, "Entorno local instalado y verificado con exito."

        except Exception as e:
            return False, f"Error critico durante la instalacion: {str(e)}"

    def _sincronizar_addons(self, project_root: Path, dependencies: dict, status_callback):
        local_addons_dir = project_root / "04_tools" / "addons"
        local_addons_dir.mkdir(parents=True, exist_ok=True)

        for addon_name, version in dependencies.items():
            # Construimos el nombre exacto basado en tu ls: addon_version.zip
            nombre_archivo = f"{addon_name}_{version}.zip"
            origen_addon_zip = self.boveda_addons / nombre_archivo
            destino_addon = local_addons_dir / addon_name

            if origen_addon_zip.exists():
                status_callback(f"Instalando plugin: {addon_name} (v{version})...", "yellow")
                
                # Limpiar si ya existia una version anterior localmente
                if destino_addon.exists():
                    shutil.rmtree(destino_addon)
                
                destino_addon.mkdir(parents=True, exist_ok=True)
                
                # Extraemos el ZIP directamente en la carpeta del proyecto
                with zipfile.ZipFile(origen_addon_zip, 'r') as zip_ref:
                    zip_ref.extractall(destino_addon)
            else:
                print(f"Advertencia: No se encontro el archivo {nombre_archivo} en la boveda.")

    def _crear_symlinks(self, project_path: Path, svn_path: Path):
        """Construye los enlaces simbolicos cruzados entre Nextcloud y SVN."""
        render_root = project_path / "03_render"
        edit_dir = svn_path / "edit"
        
        edit_dir.mkdir(parents=True, exist_ok=True)
        folders_to_link = ["footage", "deliver", "export"]

        for folder in folders_to_link:
            link_path = edit_dir / folder       # Enlace falso en SVN
            target_path = render_root / folder  # Carpeta real en Nextcloud
            
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Si el link no existe, lo creamos de forma segura
            if not link_path.exists() and not link_path.is_symlink():
                link_path.symlink_to(target_path, target_is_directory=True)

