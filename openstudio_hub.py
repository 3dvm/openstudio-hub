# =========================================================================================
# OPENSTUDIOHUB
# Módulo: openstudio_hub.py
# Rol Arquitectónico: Main App Root / Orquestador Inicial
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.4.0
# =========================================================================================

"""
Punto de entrada principal de OpenStudio Hub.
Inicializa el entorno gráfico, lee la configuración maestra B2B,
gestiona el enrutamiento base (Login vs Dashboard) e implementa
el guardián de procesos en segundo plano.
"""

import customtkinter as ctk
import tkinter.messagebox as messagebox
from pathlib import Path

# --- CORE (Motores) ---
from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

# --- UI (Vistas) ---
from ui.view_login import ViewLogin
from ui.view_artist import ViewArtist
from ui.view_td import ViewTD

# --- CONFIGURACION GLOBAL ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MacuareHub(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Título actualizado a la versión actual de la Fase 2
        self.title("OpenStudio Hub - v0.4.0")
        self.geometry("600x600")
        self.resizable(False, False)

        # Guardián de Procesos (Protección de Lock Passing)
        self.blender_instances = 0
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 1. Inicializar los Motores
        self.auth = AuthManager()
        self.vault = VaultManager()
        
        # Leemos la configuración global B2B
        settings_path = Path("settings.json")
        self.config_factory = ConfigFactory(settings_path)

        # 2. Enrutador Inicial (State Machine)
        if self.auth.login_with_saved_session():
            self.mostrar_dashboard()
        else:
            self.mostrar_login()

    def registrar_instancia(self, activa: bool):
        """Incrementa o decrementa el contador de instancias de Blender activas."""
        if activa:
            self.blender_instances += 1
        else:
            self.blender_instances = max(0, self.blender_instances - 1)

    def _on_closing(self):
        """Intercepta el cierre de la ventana para proteger los bloqueos de SVN."""
        if self.blender_instances > 0:
            messagebox.showwarning(
                "Operación Bloqueada",
                f"Tienes {self.blender_instances} sesión(es) de entorno 3D abierta(s).\n\n"
                "Cierra el programa primero para liberar los archivos maestros en el servidor (SVN Unlock) "
                "y evitar corrupción en la producción."
            )
        else:
            self.destroy()

    def limpiar_pantalla(self):
        """Destruye la vista actual para poder montar una nueva."""
        for widget in self.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        """Monta la vista de Login inyectando dependencias."""
        self.limpiar_pantalla()
        
        vista_login = ViewLogin(
            parent=self, 
            auth_manager=self.auth, 
            vault_manager=self.vault, 
            on_login_success=self.mostrar_dashboard
        )
        vista_login.pack(fill="both", expand=True)

    def mostrar_dashboard(self):
        """Monta la vista correcta dependiendo del rol extraído de Kitsu."""
        self.limpiar_pantalla()
        
        rol = self.auth.get_user_role()
        
        # SOLUCIÓN: Tomamos el Workspace Root directo mapeado en settings.json sin alteraciones
        nextcloud_dir = self.config_factory.get_workspace_root()
        
        if rol in ["td", "supervisor"]:
            vista = ViewTD(
                parent=self, 
                auth_manager=self.auth, 
                nextcloud_dir=nextcloud_dir, 
                vault_manager=self.vault,
                config_factory=self.config_factory,
                on_logout=self.ejecutar_logout
            )
        else:
            vista = ViewArtist(
                parent=self, 
                auth_manager=self.auth, 
                nextcloud_dir=nextcloud_dir,
                vault_manager=self.vault,
                config_factory=self.config_factory,
                on_logout=self.ejecutar_logout
            )
        
        vista.pack(fill="both", expand=True)

    def ejecutar_logout(self):
        """Limpia el estado global y devuelve al usuario al inicio."""
        # Evitamos el logout si hay archivos bloqueados temporalmente
        if self.blender_instances > 0:
            self._on_closing()
            return
            
        self.auth.logout()
        self.vault.clear()  # Zero-Disk Passwords: Vaciamos la RAM
        self.mostrar_login()

if __name__ == "__main__":
    app = MacuareHub()
    app.mainloop()
