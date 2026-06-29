import json
import threading
import customtkinter as ctk
from pathlib import Path
from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from ui.window_svn_login import SVNLoginWindow

class ProjectListWidget(ctk.CTkScrollableFrame):
    def __init__(self, parent, nextcloud_dir, vault_manager, status_callback, **kwargs):
        """
        Componente reutilizable que escanea, verifica el estado de instalacion
        y despliega la lista de proyectos con acciones contextuales (Instalar o Abrir).
        También verifica las credenciales en RAM antes de proceder.
        """
        super().__init__(parent, **kwargs)
        self.nextcloud_dir = nextcloud_dir
        
        # === INYECCION DE LA BOVEDA ===
        self.vault = vault_manager
        self.status_callback = status_callback
        
        # Inicializamos el motor de instalacion local
        self.installer = LocalInstaller(nextcloud_dir)
        
        self.cargar_proyectos()

    def limpiar_lista(self):
        """Borra todos los widgets internos para poder refrescar la lista de forma limpia."""
        for widget in self.winfo_children():
            widget.destroy()

    def cargar_proyectos(self):
        self.limpiar_lista()
        proyectos_encontrados = 0
        
        if self.nextcloud_dir.exists():
            for carpeta in self.nextcloud_dir.iterdir():
                if carpeta.is_dir():
                    # La semilla global ahora vive en 05_config_estudio
                    init_path = carpeta / "05_config_estudio" / "project_init.json"
                    
                    # Soporte para proyectos antiguos (Legacy) creados con scripts anteriores
                    config_legacy_path = carpeta / "06_conf_LOCAL" / "project_config.json"
                    
                    if init_path.exists():
                        self.procesar_proyecto_hub(carpeta, init_path)
                        proyectos_encontrados += 1
                    elif config_legacy_path.exists():
                        # Proyecto antiguo pre-Hub: se asume ya instalado y listo para abrir
                        # Leemos el JSON antiguo para extraer el nombre y la version
                        with open(config_legacy_path, 'r', encoding='utf-8') as f:
                            data_legacy = json.load(f)
                        
                        nombre_legacy = data_legacy.get("project_name", carpeta.name)
                        version_legacy = data_legacy.get("blender_version", "??")
                        
                        self.crear_boton_abrir(carpeta, config_legacy_path, f"{nombre_legacy} [Blender {version_legacy}]")
                        proyectos_encontrados += 1

        if proyectos_encontrados == 0:
            self.status_callback("No se encontraron proyectos activos sincronizados.", "gray")
        else:
            self.status_callback(f"Sincronizacion completada. Total de proyectos: {proyectos_encontrados}", "white")

    def procesar_proyecto_hub(self, project_root: Path, init_path: Path):
        """Determina dinamicamente si el proyecto necesita instalacion o si ya puede abrirse."""
        with open(init_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        nombre = data.get("project_name", project_root.name)
        version = data.get("blender_version", "??")
        
        # Comprobar si el artista ya configuro su entorno local en esta PC
        esta_instalado = self.installer.verificar_instalacion(project_root)
        
        if esta_instalado:
            config_local_path = project_root / "06_conf_LOCAL" / "project_config.json"
            self.crear_boton_abrir(project_root, config_local_path, f"{nombre} [Blender {version}]")
        else:
            self.crear_boton_instalar(project_root, f"{nombre} [Requiere Configuracion]")

    def crear_boton_abrir(self, project_root: Path, config_path: Path, label_text: str):
        """Genera un boton para lanzar directamente el entorno aislado de Blender."""
        btn = ctk.CTkButton(
            self, 
            text=f"Abrir: {label_text}", 
            font=ctk.CTkFont(size=13),
            height=40,
            command=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
        )
        btn.pack(pady=5, fill="x", padx=10)

    def crear_boton_instalar(self, project_root: Path, label_text: str):
        """Genera un boton contextual llamativo para desplegar la instalacion local."""
        btn = ctk.CTkButton(
            self, 
            text=f"Instalar: {label_text}", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#D97706",      # Color ambar/naranja corporativo sobrio y limpio
            hover_color="#B45309",
            height=40,
            command=lambda: self.ejecutar_instalacion_hilo(project_root)
        )
        btn.pack(pady=5, fill="x", padx=10)

    def iniciar_proyecto_hilo(self, project_root: Path, config_path: Path):
        # === INTERCEPTOR JIT PARA ABRIR ===
        if not self.vault.has_svn_credentials():
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
            )
            return

        # Extraemos credenciales completas de la RAM para inyectarlas a Blender
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        kitsu_user, kitsu_pwd = self.vault.get_kitsu_credentials()

        threading.Thread(
            target=lanzar_blender, 
            args=(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, self.status_callback), 
            daemon=True
        ).start()

    def ejecutar_instalacion_hilo(self, project_root: Path):
        # === INTERCEPTOR JIT PARA INSTALAR ===
        if not self.vault.has_svn_credentials():
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.ejecutar_instalacion_hilo(project_root)
            )
            return

        threading.Thread(
            target=self._hilo_instalacion, 
            args=(project_root,), 
            daemon=True
        ).start()

    def _hilo_instalacion(self, project_root: Path):
        # Extraemos las claves de la RAM para que el motor haga el checkout silencioso
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        
        exito, mensaje = self.installer.instalar_entorno(project_root, svn_user, svn_pwd, self.status_callback)
        
        if exito:
            self.status_callback(mensaje, "green")
            # Forzamos un refresco grafico seguro en el hilo principal de Tkinter despues de medio segundo
            self.after(500, self.cargar_proyectos)
        else:
            self.status_callback(mensaje, "red")
