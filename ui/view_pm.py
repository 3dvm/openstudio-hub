# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_pm.py
# Rol Arquitectónico: UI Component / Production Manager Dashboard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 2.1.0 (Widget Extraction / Routing Only)
# =========================================================================================

from PySide6.QtWidgets import QStackedWidget, QLabel
from PySide6.QtCore import Qt

from ui.base_dashboard import BaseDashboardView
from ui.widget_blend_builder import WidgetBlendBuilder

class ViewPM(BaseDashboardView):
    def __init__(self, parent, auth_manager, config_factory, on_logout, **kwargs):
        super().__init__(parent, auth_manager, config_factory, on_logout, **kwargs)
        
        self.setObjectName("ViewPMBase")

        # 1. Configurar Navegación Lateral (Inyectada al Master Layout)
        self.add_sidebar_button("btn_batch", self.tr("Batch Creation"), "📦", "folder.svg", lambda: self._cambiar_panel("btn_batch"), activo=True)
        # Espacio preparado para futuros paneles del PM
        # self.add_sidebar_button("btn_metrics", self.tr("Metrics"), "📊", "chart.svg", lambda: self._cambiar_panel("btn_metrics"))

        # 2. Construir el Contenido Central
        self._build_pm_content()

    def _build_pm_content(self):
        """Prepara el StackedWidget e inyecta los widgets de trabajo modulares."""
        self.stacked_content = QStackedWidget()

        # Index 0: Batch Entity Genesis Tool
        self.widget_builder = WidgetBlendBuilder(
            parent=self.stacked_content,
            auth_manager=self.auth,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.widget_builder)

        # Index 1: Futuro panel (Ej. Métricas)
        placeholder = QLabel(self.tr("🚧 Future PM Module under construction..."))
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setObjectName("PlaceholderText")
        self.stacked_content.addWidget(placeholder)

        # Inyectar el stack completo en el contenedor de la clase padre
        self.content_layout.addWidget(self.stacked_content, stretch=1)

    def _cambiar_panel(self, panel_id: str):
        """Visual Router: Actualiza el sidebar y cambia la vista del stack."""
        self.set_active_sidebar_button(panel_id)
        
        indices = {"btn_batch": 0, "btn_metrics": 1}
        self.stacked_content.setCurrentIndex(indices.get(panel_id, 0))
