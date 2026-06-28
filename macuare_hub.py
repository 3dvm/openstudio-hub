import os
import json
import subprocess
import threading
import customtkinter as ctk
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS ---
NEXTCLOUD_DIR = Path.home() / "Nextcloud" / "Macuare-Estudio-Archivos" / "01_PROYECTOS_ESTUDIO"

# Configuración visual de la App
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MacuareHub(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Macuare Studio Hub")
        self.geometry("600x450")
        self.resizable(False, False)

        # Título
        self.label_titulo = ctk.CTkLabel(self, text="PROYECTOS ACTIVOS", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_titulo.pack(pady=(20, 10))

        # Panel desplazable para la lista de proyectos
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=500, height=300)
        self.scroll_frame.pack(pady=10)

        # Consola de estado (feedback visual para el artista)
        self.label_estado = ctk.CTkLabel(self, text="Escaneando Nextcloud...", text_color="gray")
        self.label_estado.pack(pady=10)

        # Cargar los proyectos
        self.cargar_proyectos()

    def cargar_proyectos(self):
        """Busca carpetas en Nextcloud que tengan el ADN (project_config.json)"""
        proyectos_encontrados = 0
        
        if NEXTCLOUD_DIR.exists():
            for carpeta in NEXTCLOUD_DIR.iterdir():
                if carpeta.is_dir():
                    config_path = carpeta / "06_conf_LOCAL" / "project_config.json"
                    if config_path.exists():
                        self.crear_boton_proyecto(config_path, carpeta)
                        proyectos_encontrados += 1

        if proyectos_encontrados == 0:
            self.label_estado.configure(text="No se encontraron proyectos sincronizados.")
        else:
            self.label_estado.configure(text=f"Listos para trabajar. ({proyectos_encontrados} proyectos)")

    def crear_boton_proyecto(self, config_path, project_root):
        """Lee el JSON y crea un botón en la interfaz para ese proyecto"""
        with open(config_path, 'r', encoding='utf-8') as f:
            adn = json.load(f)
            
        nombre = adn.get("project_name", "Desconocido")
        version = adn.get("version_locking", {}).get("blender_version", "??")

        # Botón del proyecto
        btn = ctk.CTkButton(
            self.scroll_frame, 
            text=f"Abrir: {nombre}  [Blender {version}]", 
            font=ctk.CTkFont(size=14),
            height=40,
            command=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
        )
        btn.pack(pady=5, fill="x", padx=10)

    def iniciar_proyecto_hilo(self, project_root, config_path):
        """Ejecuta la lógica en un hilo separado para que la UI no se congele"""
        self.label_estado.configure(text=f"Iniciando entorno para {project_root.name}...", text_color="yellow")
        threading.Thread(target=self.lanzar_blender, args=(project_root, config_path), daemon=True).start()

    def lanzar_blender(self, project_root, config_path):
        """Aquí va la magia de tu antiguo 1_SETUP_WORKSTATION y Launcher"""
        try:
            # 1. SVN Checkout (Simulado)
            self.label_estado.configure(text="Sincronizando SVN (Archivos Pesados)...")
            # subprocess.run(["svn", "update", ...]) # Tu lógica real aquí
            
            # 2. Extraer Extensions (Simulado)
            self.label_estado.configure(text="Verificando Extensiones aisladas...")
            # Extraer ZIP maestro...

            # 3. Lanzar Blender aislado
            self.label_estado.configure(text="Arrancando Blender...", text_color="green")
            
            env = os.environ.copy()
            env["MACUARE_PROJECT_CONFIG"] = str(config_path)
            env["BLENDER_USER_SCRIPTS"] = str(project_root / "04_tools")
            
            # Lanzamos Blender de verdad
            subprocess.Popen(["blender"], env=env)
            
            # Podemos cerrar el Hub o dejarlo abierto
            # self.quit() 
            
        except Exception as e:
            self.label_estado.configure(text=f"Error: {str(e)}", text_color="red")

if __name__ == "__main__":
    app = MacuareHub()
    app.mainloop()
