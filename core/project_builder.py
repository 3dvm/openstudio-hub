import json
import shutil
from pathlib import Path
from re import template

class ProjectBuilder:
    def __init__(self, nextcloud_dir: Path):
        self.base_dir = nextcloud_dir

    def create_project(self, project_name: str, blender_version: str, dependencies: dict, project_template: str, splash_image_path: str = "") -> tuple[bool, str]:
        """
        Genera el árbol de directorios para un nuevo proyecto en Nextcloud,
        escribe el archivo .nextcloudignore por seguridad, y deja el Payload (Semilla).
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
            # 1. Construir el árbol de directorios estándar de Nextcloud
            # NOTA: 02_archivos_de_produccion y 06_conf_LOCAL NO se crean aquí,
            # se crearán dinámicamente en la PC del artista durante la instalación.
            carpetas_base = [
                "01_Brief_y_Refs",
                "03_render",
                "04_tools",
                "05_config_estudio"
            ]

            for carpeta in carpetas_base:
                (project_path / carpeta).mkdir(parents=True, exist_ok=True)

            # 2. La red de seguridad (.nextcloudignore)
            # Obligamos a Nextcloud a ignorar las carpetas pesadas/locales desde el día 1
            ignore_file = project_path / ".nextcloudignore"
            ignore_content = "02_archivos_de_produccion\n06_conf_LOCAL\n*.blend1\n*.blend2\nquit.blend\n"
            
            with open(ignore_file, "w", encoding="utf-8") as f:
                f.write(ignore_content)

            # 3. Generar el Payload / Semilla (project_init.json)
            payload_data = {
                "project_name": project_name.strip(),
                "blender_version": blender_version.strip(),
                "kitsu_host": "https://proyectos.macuare.com.ve",
                "template": project_template.strip(),
                "dependencies": dependencies
            }

            payload_file = project_path / "05_config_estudio" / "project_init.json"
            
            with open(payload_file, 'w', encoding='utf-8') as f:
                json.dump(payload_data, f, indent=4)

            # === NUEVO: COPIAR EL SPLASH SCREEN ===
            if splash_image_path:
                splash_source = Path(splash_image_path)
                if splash_source.exists() and splash_source.is_file():
                    destino_splash = project_path / "05_config_estudio" / "splash.png"
                    shutil.copy(splash_source, destino_splash)

            return True, f"Proyecto '{folder_name}' inicializado. Esperando instalación en clientes."

        except Exception as e:
            return False, f"Error de sistema al crear carpetas: {str(e)}"
