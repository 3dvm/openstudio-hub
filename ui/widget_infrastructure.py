# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_infrastructure.py
# Rol Arquitectónico: UI Component / DevOps & Server Management Placeholder (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.4.0
# =========================================================================================

"""
Panel de gestión de infraestructura para el Director Técnico.
Actualmente en construcción. Reservado para la fase de despliegue DevOps
(Granjas de Render, Servidores de Caché locales y monitoreo de Nodos).
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class InfrastructureWidget(QFrame):
    def __init__(self, parent, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        self.setObjectName("InfrastructureWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_placeholder = QLabel(self.tr("🚧 DevOps & Server Infrastructure module under construction..."))
        lbl_placeholder.setAlignment(Qt.AlignCenter)
        lbl_placeholder.setStyleSheet("color: #64748B; font-size: 16px; font-weight: bold;")
        
        main_layout.addWidget(lbl_placeholder)
