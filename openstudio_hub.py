# =========================================================================================
# OPENSTUDIOHUB
# Módulo: openstudio_hub.py
# Rol Arquitectónico: Main App Root / Orquestador Inicial (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.7.1
# =========================================================================================

"""
Punto de entrada principal de OpenStudio Hub.
Inicializa el entorno gráfico nativo en Qt (PySide6), lee la configuración maestra B2B,
gestiona el enrutamiento base (Login vs Dashboard) e implementa el guardián de procesos.
Optimizado para Cero-Latencia en el arranque del Dashboard.
"""

import sys
from pathlib import Path

# --- PySide6 (Motor Gráfico) ---
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtGui import QCloseEvent

# --- CORE (Motores) ---
from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

# --- UI (Vistas) ---
from ui.view_login import ViewLogin
from ui.view_artist import ViewArtist
from ui.view_td import ViewTD


class MacuareHub(QMainWindow):
    def __init__(self):
        super().__init__()

        # Título base (Se sobrescribe dinámicamente tras el login)
        self.setWindowTitle(self.tr("OpenStudio Hub - v0.7.1"))
        self.resize(1000, 700) 
        self.setMinimumSize(800, 600)

        # Guardián de Procesos (Protección de Lock Passing)
        self.blender_instances = 0

        # 1. Inicializar los Motores Base
        self.auth = AuthManager()
        self.vault = VaultManager()
        
        settings_path = Path("settings.json")
        self.config_factory = ConfigFactory(settings_path)

        # 2. Enrutador Inicial (State Machine MVC)
        self.mostrar_login()

    def registrar_instancia(self, activa: bool):
        """Incrementa o decrementa el contador de instancias de Blender activas."""
        if activa:
            self.blender_instances += 1
        else:
            self.blender_instances = max(0, self.blender_instances - 1)

    def closeEvent(self, event: QCloseEvent):
        """Intercepta el cierre de la ventana nativa de Qt para proteger la integridad del SVN."""
        if self.blender_instances > 0:
            mensaje = self.tr(
                "You have {0} 3D environment session(s) open.\n\n"
                "Please close the program first to release the master files on the server (SVN Unlock) "
                "and avoid production corruption."
            ).format(self.blender_instances)
            
            QMessageBox.warning(
                self,
                self.tr("Blocked Operation"),
                mensaje
            )
            event.ignore() 
        else:
            self.auth.logout()
            self.vault.clear()
            event.accept()

    def mostrar_login(self):
        """Monta la vista de Login en el contenedor central."""
        self.setWindowTitle(self.tr("OpenStudio Hub - v0.7.1"))
        
        vista_login = ViewLogin(
            parent=self, 
            auth_manager=self.auth, 
            vault_manager=self.vault, 
            config_factory=self.config_factory,
            on_login_success=self.mostrar_dashboard
        )
        self.setCentralWidget(vista_login)

    def mostrar_dashboard(self):
        """Monta el Dashboard inyectando el contexto B2B local (Cero Latencia)."""
        # Leemos el nombre del estudio directamente de la configuración local (SSoT)
        studio_name = self.config_factory.get_studio_name()
        if not studio_name:
            studio_name = "OpenStudio"
            
        self.setWindowTitle(self.tr("{0} Hub - v0.7.1").format(studio_name))
        
        # Enrutamiento de Vistas (Factory)
        rol = self.auth.get_user_role()
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
        
        self.setCentralWidget(vista)

    def ejecutar_logout(self):
        """Limpia el estado global de Qt y revierte al formulario de acceso."""
        if self.blender_instances > 0:
            self.close() 
            return
            
        self.auth.logout()
        self.vault.clear()  
        self.mostrar_login()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # ---------------------------------------------------------
    # INYECCIÓN GLOBAL DE ESTILOS (QSS)
    # ---------------------------------------------------------
    theme_path = Path("macuare_theme.qss")
    if theme_path.exists():
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            print("[OPENSTUDIO HUB] ✓ Corporate QSS theme loaded successfully.")
        except Exception as e:
            print(f"[OPENSTUDIO HUB] ❌ Error reading QSS file: {e}")
    else:
        print("[OPENSTUDIO HUB] ⚠️ WARNING: 'macuare_theme.qss' not found. Starting with OS native theme.")
        
    window = MacuareHub()
    window.show()
    sys.exit(app.exec())
