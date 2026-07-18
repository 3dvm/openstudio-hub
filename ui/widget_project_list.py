# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_project_list.py
# Rol Arquitectónico: UI Component / TD Project Grid (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.1
# =========================================================================================

"""
Componente independiente para la Lista de Proyectos del TD.
Encapsula la lógica de cuadrícula responsiva, extracción de datos vía Kitsu
y el botón de creación de nuevos proyectos.
"""

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QLabel, QPushButton, QScrollArea, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QResizeEvent
from pathlib import Path

from ui.window_new_project import NewProjectWindow

try:
    from ui.components.project_card import ProjectCard
except ImportError:
    ProjectCard = None


class ProjectGridWorker(QThread):
    """Hilo secundario para extraer los proyectos abiertos del estudio desde Kitsu."""
    data_ready = Signal(list)

    def __init__(self, auth_manager):
        super().__init__()
        self.auth = auth_manager

    def run(self):
        import gazu
        try:
            proyectos = gazu.project.all_open_projects()
            self.data_ready.emit(proyectos)
        except Exception as e:
            print(f"[ProjectList] Error obteniendo proyectos: {e}")
            self.data_ready.emit([])


class ProjectListWidget(QFrame):
    def __init__(self, parent, nextcloud_dir: Path, auth_manager, vault_manager, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.nextcloud_dir = nextcloud_dir
        self.auth = auth_manager
        self.vault = vault_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        self._project_widgets = []
        self._current_cols = 0
        
        self.setObjectName("ProjectListWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()

    def _build_ui(self):
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # HERO ACTION (Botón Crear Proyecto)
        self.btn_nuevo_proy = QPushButton("+ Create New Project")
        self.btn_nuevo_proy.setObjectName("PrimaryButton") 
        self.btn_nuevo_proy.setFixedHeight(50)
        self.btn_nuevo_proy.setCursor(Qt.PointingHandCursor)
        # Corrección B2B: Forzado explícito de hoja de estilo para igualar el mockup corporativo
        self.btn_nuevo_proy.setStyleSheet("background-color: #10B981; color: #0F172A; font-weight: bold; border-radius: 8px; font-size: 14px; border: none;")
        self.btn_nuevo_proy.clicked.connect(self.abrir_wizard_proyecto)
        content_layout.addWidget(self.btn_nuevo_proy)

        # CONTENEDOR GRID CON SCROLL
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)  
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
        card_width = 320 
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
    # LÓGICA DE DATOS
    # ---------------------------------------------------------

    def _emit_status(self, mensaje: str, color: str = "white"):
        if self.status_callback:
            self.status_callback(mensaje, color)

    def cargar_proyectos(self):
        self._emit_status("🔄 Sincronizando catálogo de proyectos con el servidor...", "yellow")
        
        for widget in self._project_widgets:
            widget.hide()
            widget.deleteLater()
        self._project_widgets.clear()
        
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.worker = ProjectGridWorker(self.auth)
        self.worker.data_ready.connect(self._renderizar_proyectos)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _renderizar_proyectos(self, proyectos: list):
        if not proyectos:
            self._emit_status("⚠️ No hay proyectos abiertos en Kitsu.", "yellow")
            return
            
        self._emit_status(f"🟢 Sincronizado: {len(proyectos)} proyectos activos.", "green")
        
        for project_data in proyectos:
            if ProjectCard:
                tarjeta = ProjectCard(
                    parent=self.grid_widget,
                    project_data=project_data,
                    auth_manager=self.auth
                )
            else:
                tarjeta = QLabel(f"📦 {project_data.get('name', 'Unknown')}")
                tarjeta.setStyleSheet("background-color: #1E293B; border-radius: 8px; padding: 20px; font-weight: bold;")
                tarjeta.setFixedSize(320, 280)

            self._project_widgets.append(tarjeta)
            
        self._current_cols = 0 
        self._rearrange_grid()

    def abrir_wizard_proyecto(self):
        # Corrección de API: Se inyecta la dependencia requerida 'config_factory' al Wizard.
        self.wizard_window = NewProjectWindow(
            parent=self.window(),
            nextcloud_dir=self.nextcloud_dir,
            config_factory=self.config_factory,
            on_success_callback=self.cargar_proyectos
        )
        self.wizard_window.show()
