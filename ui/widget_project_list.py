import json
import threading
import customtkinter as ctk
from core.env_launcher import lanzar_blender

class ProjectListWidget(ctk.CTkScrollableFrame):
    def __init__(self, parent, nextcloud_dir, status_callback, **kwargs):
        """
        Componente reutilizable que escanea y muestra la lista de proyectos.
        parent: El contenedor donde vivira este widget
        nextcloud_dir: Ruta del servidor de archivos
        status_callback: Funcion para reportar el estado a la UI principal
        """
        super().__init__(parent, **kwargs)
        self.nextcloud_dir = nextcloud_dir
        self.status_callback = status_callback
        
        self.cargar_proyectos()

    def cargar_proyectos(self):
        proyectos_encontrados = 0
        if self.nextcloud_dir.exists():
            for carpeta in self.nextcloud_dir.iterdir():
                if carpeta.is_dir():
                    config_path = carpeta / "06_conf_LOCAL" / "project_config.json"
                    if config_path.exists():
                        self.crear_boton_proyecto(config_path, carpeta)
                        proyectos_encontrados += 1

        if proyectos_encontrados == 0:
            self.status_callback("No se encontraron proyectos activos sincronizados.", "gray")
        else:
            self.status_callback(f"Sincronizacion completada. Total de proyectos: {proyectos_encontrados}", "white")

    def crear_boton_proyecto(self, config_path, project_root):
        with open(config_path, 'r', encoding='utf-8') as f:
            adn = json.load(f)
            
        nombre = adn.get("project_name", "Desconocido")
        
        if "version_locking" in adn:
            version = adn["version_locking"].get("blender_version", "??")
        else:
            version = adn.get("blender_version", "??")

        btn = ctk.CTkButton(
            self, 
            text=f"Abrir: {nombre} [Blender {version}]", 
            font=ctk.CTkFont(size=13),
            height=40,
            command=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
        )
        btn.pack(pady=5, fill="x", padx=10)

    def iniciar_proyecto_hilo(self, project_root, config_path):
        threading.Thread(
            target=lanzar_blender, 
            args=(project_root, config_path, self.status_callback), 
            daemon=True
        ).start()
