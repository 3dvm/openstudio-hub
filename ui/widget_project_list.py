# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_project_list.py
# Rol Arquitectónico: UI Component / JIT Interceptor
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.3.1
# =========================================================================================

"""
Componente reutilizable que escanea y despliega la lista de proyectos.
Verifica el estado de instalación y las credenciales en RAM antes de proceder,
actuando como el interceptor Just-In-Time (JIT) principal de la interfaz.
"""

import json
import threading
import customtkinter as ctk
from pathlib import Path
from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from ui.window_svn_login import SVNLoginWindow

class ProjectListWidget(ctk.CTkScrollableFrame):
    def __init__(self, parent, nextcloud_dir: Path, auth_manager, vault_manager, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.nextcloud_dir = nextcloud_dir
        
        # === INYECCION DE DEPENDENCIAS ===
        self.auth_manager = auth_manager
        self.vault = vault_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        # Inicializamos el motor de instalacion local inyectándole el factory
        self.installer = LocalInstaller(nextcloud_dir, config_factory)
        
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
            self.status_callback("Esperando credenciales de repositorio...", "yellow")
            self.update_idletasks() # FIX: Forzar renderizado antes de secuestrar el hilo con la modal
            
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
            )
            return

        # Extraemos credenciales de SVN y Kitsu de forma segura desde la memoria RAM
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        kitsu_user, kitsu_pwd = self.vault.get_kitsu_credentials()
        
        # Obtenemos metadatos desde el AuthManager
        kitsu_host = self.auth_manager.kitsu_host
        user_role = self.auth_manager.get_user_role()

        # Input interactivo temporal para capturar el TaskType
        dialog = ctk.CTkInputDialog(text="Ingrese el Tipo de Tarea\n(ej. animation, rigging, lookdev):", title="Context-Aware Tooling")
        task_type = dialog.get_input()
        
        if not task_type:
            self.status_callback("Lanzamiento cancelado por el usuario.", "red")
            return

        self.status_callback("Iniciando entorno aislado...", "yellow")

        # Lanzamos el hilo inyectando TODAS las credenciales (en crudo) para que el bootstrap las procese
        threading.Thread(
            target=lanzar_blender, 
            args=(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type, self.status_callback), 
            daemon=True
        ).start()

    def ejecutar_instalacion_hilo(self, project_root: Path):
        # === INTERCEPTOR JIT PARA INSTALAR ===
        if not self.vault.has_svn_credentials():
            self.status_callback("Esperando credenciales de repositorio...", "yellow")
            self.update_idletasks() # FIX: Forzar renderizado antes de secuestrar el hilo con la modal
            
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
            self.after(500, self.cargar_proyectos)
        else:
            self.status_callback(mensaje, "red")
            # Issue 4: Sincronización asíncrona fallida. Purgamos de inmediato la RAM 
            # para obligar a la interfaz a desplegar de nuevo el modal JIT en el próximo intento.
            self.vault.clear()
