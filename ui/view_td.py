# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_td.py
# Rol Arquitectónico: UI View / Command Center Dashboard (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.7.2
# =========================================================================================

"""
Advanced control panel for the Technical Director (TD) and Supervisors.
Refactored into a Router architecture using QStackedWidget to dynamically switch panels.
Injects auth_manager correctly into SettingsWidget to resolve downstream type errors.
Features comprehensive Qt native i18n support.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QPushButton, QStackedWidget)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path
from typing import Callable

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

from ui.widget_project_list import ProjectListWidget
from ui.widget_infrastructure import InfrastructureWidget
from ui.widget_settings import SettingsWidget


class ViewTD(QWidget):
    def __init__(self, parent: QWidget, auth_manager: AuthManager, nextcloud_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None]):
        super().__init__(parent)
        
        self.auth = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.vault = vault_manager
        self.config_factory = config_factory
        self.on_logout = on_logout

        self.setObjectName("ViewTDBase")

        # ---------------------------------------------------------
        # ROOT LAYOUT
        # ---------------------------------------------------------
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_top_bar()

        # Secondary layout to divide Sidebar and Main Area
        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)

        self._build_sidebar()
        self._build_main_area()
        
        self.main_layout.addLayout(self.body_layout)
        
        # Initial project feed load
        self.vista_proyectos.cargar_proyectos()

    def _build_top_bar(self):
        self.top_bar = QFrame(self)
        self.top_bar.setObjectName("TopBar")
        self.top_bar.setFixedHeight(65)
        
        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(30, 0, 30, 0)
        top_bar_layout.setSpacing(15)

        self.logo_icon = QLabel()
        logo_path = Path("assets/logo_topbar.png")
        if logo_path.exists():
            self.logo_icon.setPixmap(QPixmap(str(logo_path)).scaledToHeight(40, Qt.SmoothTransformation))
        top_bar_layout.addWidget(self.logo_icon)
        
        self.top_separator = QFrame()
        self.top_separator.setObjectName("TopSeparator")
        self.top_separator.setFixedSize(2, 24)
        top_bar_layout.addWidget(self.top_separator)
        
        studio_name = self.config_factory.get_studio_name()
        if not studio_name:
            studio_name = "OpenStudio"
        self.lbl_title = QLabel(self.tr("{0} Hub").format(studio_name))
        self.lbl_title.setObjectName("H1Title")
        top_bar_layout.addWidget(self.lbl_title)

        top_bar_layout.addStretch()

        rol = self.auth.get_user_role().capitalize()
        nombre_user = self.auth.user_data.get("first_name", "Tech Director") if self.auth.user_data else "Tech Director"
        self.lbl_name = QLabel(self.tr("{0} ({1})").format(nombre_user, rol))
        self.lbl_name.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: bold;")
        self.lbl_name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_bar_layout.addWidget(self.lbl_name)

        self.avatar_icon = QLabel()
        self.avatar_icon.setAlignment(Qt.AlignCenter)
        self.avatar_icon.setFixedSize(35, 35)
        avatar_path = Path("assets/icons/user.svg")
        if avatar_path.exists():
            self.avatar_icon.setPixmap(QPixmap(str(avatar_path)).scaledToHeight(20, Qt.SmoothTransformation))
        else:
            self.avatar_icon.setText("👤")
        top_bar_layout.addWidget(self.avatar_icon)

        self.bell_icon = QLabel()
        self.bell_icon.setAlignment(Qt.AlignCenter)
        bell_path = Path("assets/icons/bell.svg")
        if bell_path.exists():
            self.bell_icon.setPixmap(QPixmap(str(bell_path)).scaledToHeight(18, Qt.SmoothTransformation))
        else:
            self.bell_icon.setText("🔔")
        self.bell_icon.setContentsMargins(10, 0, 15, 0)
        top_bar_layout.addWidget(self.bell_icon)

        self.btn_logout = QPushButton(self.tr("Log Out"))
        self.btn_logout.setObjectName("SecondaryButton")
        self.btn_logout.setFixedSize(80, 32)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.clicked.connect(self.on_logout)
        top_bar_layout.addWidget(self.btn_logout)

        self.main_layout.addWidget(self.top_bar)

    def _crear_icono_coloreado(self, icon_path: Path, color_hex: str) -> QIcon:
        if not icon_path.exists():
            return QIcon()
            
        try:
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            svg_content = svg_content.replace('currentColor', color_hex)
            svg_content = svg_content.replace('#000000', color_hex)
            svg_content = svg_content.replace('#000"', f'{color_hex}"')
            svg_content = svg_content.replace("#000'", f"{color_hex}'")
            
            pixmap = QPixmap()
            pixmap.loadFromData(svg_content.encode('utf-8'), "SVG")
            return QIcon(pixmap)
        except Exception:
            return QIcon(str(icon_path))

    def _crear_boton_sidebar(self, texto: str, emoji: str, icon_name: str, activo: bool = False) -> QPushButton:
        btn = QPushButton()
        icon_path = Path(f"assets/icons/{icon_name}")
        color_hex = "#F97316" if activo else "#94A3B8"
        
        if icon_path.exists():
            btn.setIcon(self._crear_icono_coloreado(icon_path, color_hex))
            btn.setIconSize(QSize(22, 22))
            btn.setText(f"   {texto}")
        else:
            btn.setText(f"{emoji}   {texto}")
            
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("SidebarNavActive" if activo else "SidebarNavInactive")
        return btn

    def _build_sidebar(self):
        self.sidebar = QFrame(self)
        self.sidebar.setObjectName("TopBar") 
        self.sidebar.setFixedWidth(240)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 20)
        sidebar_layout.setSpacing(10)

        # Dictionary to track button active states
        self.sidebar_buttons = {}

        self.btn_nav_projects = self._crear_boton_sidebar(self.tr("Projects"), "🗂️", "folder.svg", activo=True)
        self.btn_nav_projects.clicked.connect(lambda: self._cambiar_panel("proyectos"))
        sidebar_layout.addWidget(self.btn_nav_projects)
        self.sidebar_buttons["proyectos"] = self.btn_nav_projects
        
        self.btn_nav_wt = self._crear_boton_sidebar(self.tr("Watchtower"), "🗼", "radar.svg", activo=False)
        self.btn_nav_wt.clicked.connect(lambda: self._cambiar_panel("watchtower"))
        sidebar_layout.addWidget(self.btn_nav_wt)
        self.sidebar_buttons["watchtower"] = self.btn_nav_wt

        self.btn_nav_infra = self._crear_boton_sidebar(self.tr("Infrastructure"), "⚙️", "server.svg", activo=False)
        self.btn_nav_infra.clicked.connect(lambda: self._cambiar_panel("infra"))
        sidebar_layout.addWidget(self.btn_nav_infra)
        self.sidebar_buttons["infra"] = self.btn_nav_infra

        sidebar_layout.addStretch()
        
        self.btn_nav_settings = self._crear_boton_sidebar(self.tr("Settings"), "🔧", "settings.svg", activo=False)
        self.btn_nav_settings.clicked.connect(lambda: self._cambiar_panel("settings"))
        sidebar_layout.addWidget(self.btn_nav_settings)
        self.sidebar_buttons["settings"] = self.btn_nav_settings
        
        self.body_layout.addWidget(self.sidebar)

    def _cambiar_panel(self, panel_id: str):
        """Visual Router: Shifts the current QStackedWidget index and refreshes button styling classes."""
        icon_map = {"proyectos": "folder.svg", "watchtower": "radar.svg", "infra": "server.svg", "settings": "settings.svg"}
        
        for key, btn in self.sidebar_buttons.items():
            if key == panel_id:
                btn.setObjectName("SidebarNavActive")
                btn.setIcon(self._crear_icono_coloreado(Path(f"assets/icons/{icon_map[key]}"), "#F97316"))
            else:
                btn.setObjectName("SidebarNavInactive")
                btn.setIcon(self._crear_icono_coloreado(Path(f"assets/icons/{icon_map[key]}"), "#94A3B8"))
                
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        indices = {"proyectos": 0, "watchtower": 1, "infra": 2, "settings": 3}
        self.stacked_content.setCurrentIndex(indices.get(panel_id, 0))

    def _build_main_area(self):
        self.main_content = QFrame(self)
        self.main_content.setObjectName("MainContentFrame")
        
        content_layout = QVBoxLayout(self.main_content)
        content_layout.setContentsMargins(15, 25, 15, 20)
        content_layout.setSpacing(20)

        # ---------------------------------------------------------
        # CENTRAL STACK OVERVIEW (QStackedWidget)
        # ---------------------------------------------------------
        self.stacked_content = QStackedWidget(self.main_content)

        # Index 0: Project Management List
        self.vista_proyectos = ProjectListWidget(
            parent=self.stacked_content,
            nextcloud_dir=self.nextcloud_dir,
            auth_manager=self.auth,
            vault_manager=self.vault,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.vista_proyectos)

        # Index 1: Watchtower Hub Window (Placeholder)
        placeholder_wt = QLabel(self.tr("🚧 Watchtower module under construction..."))
        placeholder_wt.setAlignment(Qt.AlignCenter)
        placeholder_wt.setStyleSheet("color: #64748B; font-size: 16px; font-weight: bold;")
        self.stacked_content.addWidget(placeholder_wt)
        
        # Index 2: Infrastructure Configuration Panel
        self.vista_infra = InfrastructureWidget(
            parent=self.stacked_content,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.vista_infra)

        # Index 3: Global System Settings (Fixed signature instantiation injection)
        self.vista_configuraciones = SettingsWidget(
            parent=self.stacked_content,
            config_factory=self.config_factory,
            auth_manager=self.auth,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.vista_configuraciones)

        content_layout.addWidget(self.stacked_content, stretch=1)

        # STATUS BAR
        self.status_bar = QFrame(self.main_content)
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.setFixedHeight(35)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(15, 0, 15, 0)
        self.lbl_status = QLabel(self.tr("🟢 Waiting for project synchronization..."))
        self.lbl_status.setObjectName("StatusText")
        status_layout.addWidget(self.lbl_status)

        content_layout.addWidget(self.status_bar)
        self.body_layout.addWidget(self.main_content)

    def actualizar_status(self, mensaje: str, color: str = "white"):
        if not hasattr(self, 'lbl_status'):
            return
        colores = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444", "gray": "#9CA3AF", "white": "#F8FAFC"}
        texto_color = colores.get(color, color)
        self.lbl_status.setText(mensaje)
        self.lbl_status.setStyleSheet(f"color: {texto_color}; font-size: 12px;")
