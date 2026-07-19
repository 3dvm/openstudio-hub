# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_artist.py
# Rol Arquitectónico: UI View / Artist Dashboard (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.4.3 (Strict NAS Path Validation)
# =========================================================================================

"""
Main dashboard for Studio Artists.
Inherits from BaseDashboardView to enforce DRY principles and corporate UI guidelines.
Fetches assigned tasks from Kitsu (Gazu API) and renders them in a responsive grid.
Validates VFS semantic topography with strict physical path checks to prevent I/O crashes.
"""

import gazu
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, 
                               QScrollArea, QStackedWidget, QFrame, QPushButton)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QResizeEvent

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

from ui.base_dashboard import BaseDashboardView
from core.local_installer import LocalInstaller

# Intenta importar el componente nativo de Tarjeta de Tarea, si existe.
try:
    from ui.components.task_card import TaskCard
except ImportError:
    TaskCard = None


class FetchArtistTasksWorker(QThread):
    """Hilo secundario asíncrono para consultar las tareas asignadas al usuario en Kitsu."""
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth = auth_manager

    def run(self):
        try:
            user = gazu.client.get_current_user()
            all_tasks = gazu.task.all_tasks_for_person(user)
            
            status_targets = ["Todo", "WIP", "Retake", "Ready to Start", "Revision Needed"]
            tasks = [
                t for t in all_tasks 
                if (t.get("task_status_name") in status_targets or 
                    t.get("task_status", {}).get("name") in status_targets)
            ]
            
            self.data_ready.emit(tasks)
        except Exception as e:
            self.error_occurred.emit(str(e))


class InstallProjectWorker(QThread):
    """Hilo secundario asíncrono para ejecutar el motor de instalación local sin congelar la UI."""
    progress_updated = Signal(str, str)
    finished_install = Signal(bool, str)

    def __init__(self, project_root: Path, auth_manager: AuthManager, config_factory: ConfigFactory, task_data: dict):
        super().__init__()
        self.project_root = project_root
        self.auth = auth_manager
        self.config_factory = config_factory
        self.task_data = task_data

    def run(self):
        try:
            installer = LocalInstaller(self.project_root.parent, self.config_factory)
            
            vcs_user = self.auth.user_data.get("email", "artist") if self.auth.user_data else "artist"
            vcs_pwd = self.auth.get_current_token() 
            
            total_steps = 7
            current_step = 0
            
            def interceptor_progreso(mensaje: str, color: str):
                nonlocal current_step
                trigger_words = ["Reading structural", "Synchronizing", "Extracting", "Injecting", "Deploying", "Configuring", "Generating"]
                if any(word in mensaje for word in trigger_words):
                    current_step += 1
                
                pct = int((current_step / total_steps) * 100)
                if pct > 100: pct = 100
                self.progress_updated.emit(f"⏳ {pct}% - {mensaje}", "yellow")

            success, msg = installer.instalar_entorno(
                project_root=self.project_root,
                vcs_user=vcs_user,
                vcs_pwd=vcs_pwd,
                status_callback=interceptor_progreso,
                user_role="artist",
                task_metadata=self.task_data
            )
            
            self.finished_install.emit(success, msg)
        except Exception as e:
            self.finished_install.emit(False, str(e))


class ViewArtist(BaseDashboardView):
    def __init__(self, parent: QWidget, auth_manager: AuthManager, nextcloud_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None], **kwargs):
        
        super().__init__(parent, auth_manager, config_factory, on_logout, **kwargs)
        
        self.nextcloud_dir = nextcloud_dir
        self.vault = vault_manager
        
        self._task_widgets = []
        self._current_cols = 0
        self._install_worker = None

        self.setObjectName("ViewArtistBase")

        self.add_sidebar_button("mis_tareas", self.tr("My Tasks"), "📋", "list.svg", lambda: self._cambiar_panel("mis_tareas"), activo=True)
        self.add_sidebar_button("watchtower", self.tr("Watchtower"), "🗼", "radar.svg", lambda: self._cambiar_panel("watchtower"))

        self._build_artist_content()
        self.cargar_tareas()

    def _build_artist_content(self):
        self.stacked_content = QStackedWidget()

        self.panel_tareas = QFrame()
        layout_tareas = QVBoxLayout(self.panel_tareas)
        layout_tareas.setContentsMargins(0, 0, 0, 0)
        layout_tareas.setSpacing(20)

        lbl_title = QLabel(self.tr("My Assigned Tasks"))
        lbl_title.setObjectName("PageTitle")
        layout_tareas.addWidget(lbl_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("InvisibleScrollArea")
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("TransparentGridContainer")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.grid_widget)
        layout_tareas.addWidget(self.scroll_area, stretch=1)

        self.stacked_content.addWidget(self.panel_tareas)

        placeholder_wt = QLabel(self.tr("🚧 Watchtower module under construction..."))
        placeholder_wt.setAlignment(Qt.AlignCenter)
        placeholder_wt.setObjectName("PlaceholderText")
        self.stacked_content.addWidget(placeholder_wt)

        self.content_layout.addWidget(self.stacked_content, stretch=1)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._rearrange_grid()

    def _rearrange_grid(self):
        if not self._task_widgets: return

        viewport_width = self.scroll_area.viewport().width()
        card_width = 280  
        spacing = self.grid_layout.spacing()
        
        cols = max(1, (viewport_width + spacing) // (card_width + spacing))

        if getattr(self, '_current_cols', 0) == cols: return

        self._current_cols = cols
        row, col = 0, 0

        for widget in self._task_widgets:
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _cambiar_panel(self, panel_id: str):
        self.set_active_sidebar_button(panel_id) 
        indices = {"mis_tareas": 0, "watchtower": 1}
        self.stacked_content.setCurrentIndex(indices.get(panel_id, 0))

    def cargar_tareas(self):
        self.actualizar_status(self.tr("Fetching your assigned tasks from Kitsu..."), "yellow")
        
        for widget in self._task_widgets:
            widget.hide()
            widget.deleteLater()
        self._task_widgets.clear()
        
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.worker = FetchArtistTasksWorker(self.auth)
        self.worker.data_ready.connect(self._renderizar_tareas)
        self.worker.error_occurred.connect(lambda e: self.actualizar_status(f"Network error: {e}", "red"))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _renderizar_tareas(self, tasks: list):
        if not tasks:
            self.actualizar_status(self.tr("You have no pending tasks. Enjoy your coffee! ☕"), "white")
            return
            
        self.actualizar_status(self.tr("🟢 Synchronized: {0} active tasks found.").format(len(tasks)), "green")
        
        vfs_pipeline = self.config_factory.get_vfs_pipeline_name()
        
        for task_data in tasks:
            if TaskCard:
                p_name = task_data.get('project', {}).get('name', 'Unknown')
                p_code = task_data.get('project', {}).get('code', p_name)
                
                temp_root = self.nextcloud_dir / p_name
                if not temp_root.exists() and p_code:
                    temp_root = self.nextcloud_dir / p_code

                # Verificación estricta de la existencia física en disco
                if temp_root.exists():
                    project_root = temp_root
                else:
                    project_root = None

                is_installed = False
                can_work = True
                blocked_reason = ""
                
                if project_root:
                    try:
                        is_installed = LocalInstaller(project_root.parent, self.config_factory).verificar_instalacion(project_root)
                    except Exception:
                        is_installed = False

                    if not is_installed:
                        init_json_path = project_root / vfs_pipeline / "project_init.json"
                        if not init_json_path.exists():
                            can_work = False
                            blocked_reason = self.tr("Missing NAS Setup")
                else:
                    can_work = False
                    blocked_reason = self.tr("Folder Missing on NAS")

                def launch_cb(p_root: Path, conf_path: Path, t_data: dict):
                    self.actualizar_status(self.tr("Launch requested for: {0}").format(t_data.get('name', 'Unknown')), "yellow")
                
                def install_cb(p_root: Path, t_data: dict):
                    self.iniciar_instalacion_fisica(p_root, t_data)

                tarjeta = TaskCard(
                    parent=self.grid_widget,
                    task_data=task_data,
                    project_root=project_root,
                    is_installed=is_installed,
                    auth_manager=self.auth,
                    config_factory=self.config_factory,
                    on_launch_callback=launch_cb,
                    on_install_callback=install_cb,
                    can_work=can_work,
                    blocked_reason=blocked_reason
                )
            else:
                tarjeta = QFrame()
                tarjeta.setFixedSize(280, 220)

            self._task_widgets.append(tarjeta)
            
        self._current_cols = 0 
        self._rearrange_grid()

    def iniciar_instalacion_fisica(self, project_root: Path, task_data: dict):
        if not project_root:
            self.actualizar_status(self.tr("Cannot install: Project folder is missing on NAS."), "red")
            return
            
        if self._install_worker and self._install_worker.isRunning():
            self.actualizar_status(self.tr("Please wait, an installation is already running..."), "red")
            return

        self._install_worker = InstallProjectWorker(
            project_root=project_root,
            auth_manager=self.auth,
            config_factory=self.config_factory,
            task_data=task_data
        )

        self._install_worker.progress_updated.connect(self.actualizar_status)
        self._install_worker.finished_install.connect(self._on_install_finished)
        self._install_worker.start()

    def _on_install_finished(self, success: bool, message: str):
        if success:
            self.actualizar_status(self.tr("🟢 100% - {0}").format(message), "green")
            self.cargar_tareas()
        else:
            self.actualizar_status(self.tr("🔴 Install Error: {0}").format(message), "red")
