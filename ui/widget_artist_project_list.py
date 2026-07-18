# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_artist_project_list.py
# Rol Arquitectónico: UI Component / Artist Project Grid & Launcher (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

"""
Componente de Cuadrícula de Proyectos para el rol de Artista.
Filtra los proyectos asignados, evalúa la presencia local de los archivos (Workspace)
y orquesta dinámicamente la Instalación (vía LocalInstaller) o el Lanzamiento de Blender.
Implementa Internacionalización nativa (i18n).
"""

import json
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QLabel, QPushButton, QScrollArea, QWidget, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QResizeEvent

from core.local_installer import LocalInstaller

class ArtistProjectWorker(QThread):
    """Hilo secundario para extraer los proyectos accesibles para el artista desde Kitsu."""
    data_ready = Signal(list)

    def __init__(self, auth_manager):
        super().__init__()
        self.auth = auth_manager

    def run(self):
        import gazu
        try:
            # En v0.8+ podríamos filtrar explícitamente por 'tareas asignadas',
            # por ahora traemos los proyectos abiertos a los que el rol tiene acceso.
            proyectos = gazu.project.all_open_projects()
            self.data_ready.emit(proyectos)
        except Exception as e:
            print(f"[ArtistProjectList] Fetch Error: {e}")
            self.data_ready.emit([])


class ProjectInstallWorker(QThread):
    """Hilo secundario para no congelar la UI mientras LocalInstaller descarga el SVN/Blender."""
    progress_update = Signal(str, str)
    finished_install = Signal(bool, str)

    def __init__(self, installer, project_root, vcs_user, vcs_pwd, user_role):
        super().__init__()
        self.installer = installer
        self.project_root = project_root
        self.vcs_user = vcs_user
        self.vcs_pwd = vcs_pwd
        self.user_role = user_role

    def run(self):
        success, msg = self.installer.instalar_entorno(
            project_root=self.project_root,
            vcs_user=self.vcs_user,
            vcs_pwd=self.vcs_pwd,
            status_callback=self._emit_status,
            user_role=self.user_role
        )
        self.finished_install.emit(success, msg)

    def _emit_status(self, mensaje, color):
        self.progress_update.emit(mensaje, color)


class ArtistProjectListWidget(QFrame):
    def __init__(self, parent, config_factory, auth_manager, vault_manager, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.config_factory = config_factory
        self.auth = auth_manager
        self.vault = vault_manager
        self.status_callback = status_callback
        
        self._project_widgets = []
        self._current_cols = 0
        
        self.setObjectName("ArtistProjectListWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()

    def _build_ui(self):
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Header Area
        header_layout = QHBoxLayout()
        lbl_title = QLabel(self.tr("My Assigned Projects"))
        lbl_title.setObjectName("H2Title")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton(self.tr("Refresh Feed"))
        self.btn_refresh.setObjectName("SecondaryButton")
        self.btn_refresh.setFixedSize(120, 35)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.cargar_proyectos)
        header_layout.addWidget(self.btn_refresh)
        
        content_layout.addLayout(header_layout)

        # Scrollable Grid
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)  
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.grid_widget)
        content_layout.addWidget(self.scroll_area, stretch=1)

    # ---------------------------------------------------------
    # RESPONSIVE GRID LOGIC
    # ---------------------------------------------------------
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._rearrange_grid()

    def _rearrange_grid(self):
        if not self._project_widgets:
            return

        viewport_width = self.scroll_area.viewport().width()
        card_width = 340 
        spacing = self.grid_layout.spacing()
        
        cols = max(1, (viewport_width + spacing) // (card_width + spacing))

        if getattr(self, '_current_cols', 0) == cols:
            return

        self._current_cols = cols
        row, col = 0, 0

        for widget in self._project_widgets:
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

    # ---------------------------------------------------------
    # FETCH & RENDER LOGIC
    # ---------------------------------------------------------
    def _emit_status(self, mensaje: str, color: str = "white"):
        if self.status_callback:
            self.status_callback(mensaje, color)

    def cargar_proyectos(self):
        self._emit_status(self.tr("🔄 Syncing project assignments with server..."), "yellow")
        self.btn_refresh.setEnabled(False)
        
        for widget in self._project_widgets:
            widget.hide()
            widget.deleteLater()
        self._project_widgets.clear()
        
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.worker = ArtistProjectWorker(self.auth)
        self.worker.data_ready.connect(self._renderizar_proyectos)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _renderizar_proyectos(self, proyectos: list):
        self.btn_refresh.setEnabled(True)
        if not proyectos:
            self._emit_status(self.tr("⚠️ No active assigned projects found."), "yellow")
            return
            
        self._emit_status(self.tr("🟢 Synced: {0} active project(s).").format(len(proyectos)), "green")
        
        # Obtenemos la raíz del NAS para comprobar estados
        nas_root = self.config_factory.get_workspace_root()
        
        for project_data in proyectos:
            project_name = project_data.get('name', 'Unknown')
            folder_name = project_name.lower().replace(" ", "-")
            project_path = nas_root / folder_name
            
            tarjeta = self._crear_tarjeta_proyecto(project_name, project_path)
            self._project_widgets.append(tarjeta)
            
        self._current_cols = 0 
        self._rearrange_grid()

    def _crear_tarjeta_proyecto(self, project_name: str, project_path: Path) -> QFrame:
        """Fabrica una tarjeta de proyecto con botones contextuales."""
        card = QFrame()
        card.setObjectName("FloatingCard")
        card.setStyleSheet("background-color: #1E293B; border-radius: 8px; border: 1px solid #334155;")
        card.setFixedSize(340, 160)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        lbl_title = QLabel(project_name)
        lbl_title.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 16px; border: none;")
        layout.addWidget(lbl_title)
        
        # Estado Local (Instalado vs Nube)
        installer = LocalInstaller(self.config_factory.get_workspace_root(), self.config_factory)
        is_installed = installer.verificar_instalacion(project_path)
        
        lbl_status = QLabel()
        lbl_status.setStyleSheet("font-size: 12px; border: none;")
        
        if is_installed:
            lbl_status.setText(self.tr("Status: Ready on Disk"))
            lbl_status.setStyleSheet("color: #10B981; border: none;")
        else:
            lbl_status.setText(self.tr("Status: Cloud Only (Needs Installation)"))
            lbl_status.setStyleSheet("color: #94A3B8; border: none;")
            
        layout.addWidget(lbl_status)
        layout.addStretch()
        
        # Botón de Acción Dinámico
        btn_action = QPushButton()
        btn_action.setFixedHeight(35)
        btn_action.setCursor(Qt.PointingHandCursor)
        
        if is_installed:
            btn_action.setText(self.tr("Launch Project"))
            btn_action.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; border-radius: 6px; border: none;")
            btn_action.clicked.connect(lambda _, p=project_path: self._lanzar_blender(p))
        else:
            btn_action.setText(self.tr("Install Workspace ↓"))
            btn_action.setStyleSheet("background-color: #10B981; color: #0F172A; font-weight: bold; border-radius: 6px; border: none;")
            btn_action.clicked.connect(lambda _, p=project_path, b=btn_action: self._instalar_entorno(p, b))
            
        layout.addWidget(btn_action)
        return card

    # ---------------------------------------------------------
    # ACCIONES: INSTALL & LAUNCH
    # ---------------------------------------------------------
    def _instalar_entorno(self, project_path: Path, boton: QPushButton):
        boton.setEnabled(False)
        boton.setText(self.tr("Installing... Please wait"))
        boton.setStyleSheet("background-color: #F59E0B; color: #0F172A; font-weight: bold; border-radius: 6px; border: none;")
        
        installer = LocalInstaller(self.config_factory.get_workspace_root(), self.config_factory)
        
        # Recuperamos credenciales SVN/Git (Aquí asumimos que el VaultManager las tiene cacheadas)
        kitsu_creds = self.vault.get_kitsu_credentials()
        vcs_user = kitsu_creds.get("email", "") if kitsu_creds else ""
        vcs_pwd = kitsu_creds.get("password", "") if kitsu_creds else ""
        user_role = self.auth.get_user_role()

        self.install_worker = ProjectInstallWorker(installer, project_path, vcs_user, vcs_pwd, user_role)
        self.install_worker.progress_update.connect(self._emit_status)
        self.install_worker.finished_install.connect(self._on_install_finished)
        self.install_worker.start()

    def _on_install_finished(self, success: bool, msg: str):
        if success:
            self._emit_status(self.tr("✓ Workspace deployed: {0}").format(msg), "green")
            # Recargar la vista para que el botón cambie a "Launch Project"
            self.cargar_proyectos()
        else:
            self._emit_status(self.tr("✗ Installation Failed: {0}").format(msg), "red")
            QMessageBox.critical(self, self.tr("Deployment Error"), msg)
            self.cargar_proyectos()

    def _lanzar_blender(self, project_path: Path):
        """Lee la configuración local y ejecuta el Blender inyectando el proyecto."""
        config_path = project_path / "local" / "project_config.json"
        
        if not config_path.exists():
            self._emit_status(self.tr("Error: Local configuration missing. Reinstall workspace."), "red")
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                local_config = json.load(f)
                
            blender_version = local_config.get("blender_version", "")
            
            # Instanciar un instalador efímero para usar su buscador de ejecutables
            installer = LocalInstaller(self.config_factory.get_workspace_root(), self.config_factory)
            os_name, _ = installer._get_os_info()
            
            blender_folder = installer.boveda_blender / f"blender-{blender_version}-{os_name}-x64"
            
            if os_name == "windows":
                blender_bin = blender_folder / "blender.exe"
            elif os_name == "macos":
                blender_bin = blender_folder / "Blender.app" / "Contents" / "MacOS" / "Blender"
            else:
                blender_bin = blender_folder / "blender"

            if not blender_bin.exists():
                self._emit_status(self.tr("Error: Blender {0} binary not found in Vault.").format(blender_version), "red")
                return

            self._emit_status(self.tr("🚀 Launching Blender {0}...").format(blender_version), "green")
            
            # Lanzamos el proceso de forma desvinculada (no bloquea la UI)
            # Pasamos --project_root como argumento para que el hub o scripts puedan atraparlo
            subprocess.Popen([str(blender_bin), "--", "--project_root", str(project_path)])
            
            # Notificamos a la aplicación principal que Blender está abierto (Guardián de Procesos)
            main_window = self.window()
            if hasattr(main_window, 'registrar_instancia'):
                main_window.registrar_instancia(True)

        except Exception as e:
            self._emit_status(self.tr("Failed to launch DCC: {0}").format(str(e)), "red")
