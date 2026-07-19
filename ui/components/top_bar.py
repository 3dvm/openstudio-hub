# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/top_bar.py
# Rol Arquitectónico: UI Component / Header (User Utilities)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0
# =========================================================================================

"""
Header superior del Hub.
Diseño minimalista: Alojamiento exclusivo para utilidades de usuario alineadas a la derecha.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from pathlib import Path

class TopBar(QFrame):
    def __init__(self, parent, auth_manager, config_factory, on_logout):
        super().__init__(parent)
        self.auth = auth_manager
        self.config_factory = config_factory
        self.on_logout = on_logout
        
        self.setObjectName("TopBarFrame")
        self.setFixedHeight(65)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 0, 30, 0)
        layout.setSpacing(15)

        # Resorte expansivo para empujar todas las herramientas hacia la extrema derecha
        layout.addStretch()

        # Info de Usuario
        rol = self.auth.get_user_role().capitalize() if self.auth else "Offline"
        nombre_user = self.auth.user_data.get("first_name", "User") if self.auth and self.auth.user_data else "User"
        
        self.lbl_name = QLabel(self.tr("{0} ({1})").format(nombre_user, rol))
        self.lbl_name.setObjectName("TopBarUserLabel")
        self.lbl_name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_name)

        # Iconos de Utilidad
        self.avatar_icon = QLabel()
        self.avatar_icon.setAlignment(Qt.AlignCenter)
        self.avatar_icon.setFixedSize(35, 35)
        avatar_path = Path("assets/icons/user.svg")
        if avatar_path.exists():
            self.avatar_icon.setPixmap(QPixmap(str(avatar_path)).scaledToHeight(20, Qt.SmoothTransformation))
        else:
            self.avatar_icon.setText("👤")
        layout.addWidget(self.avatar_icon)

        self.bell_icon = QLabel()
        self.bell_icon.setAlignment(Qt.AlignCenter)
        bell_path = Path("assets/icons/bell.svg")
        if bell_path.exists():
            self.bell_icon.setPixmap(QPixmap(str(bell_path)).scaledToHeight(18, Qt.SmoothTransformation))
        else:
            self.bell_icon.setText("🔔")
        self.bell_icon.setContentsMargins(10, 0, 15, 0)
        layout.addWidget(self.bell_icon)

        # Botón Logout
        self.btn_logout = QPushButton(self.tr("Log Out"))
        self.btn_logout.setObjectName("SecondaryButton")
        self.btn_logout.setFixedSize(80, 32)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        if self.on_logout:
            self.btn_logout.clicked.connect(self.on_logout)
        layout.addWidget(self.btn_logout)
