# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_artist.py
# Rol Arquitectónico: UI View / Artist Dashboard (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.7.0
# =========================================================================================

"""
Panel de control modular para la interfaz de los Artistas (Dashboard).
Integra el QStackedWidget para alternar entre Workspaces (Instalación) y Tareas.
Orquesta los filtros dinámicos, el Activity Feed e implementa i18n nativo (Qt).
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QStackedWidget)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path
from typing import Callable

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

from ui.widget_task_list import TaskListWidget
from ui.widget_artist_project_list import ArtistProjectListWidget
from ui.components.activity_card import ActivityCard


class FeedWorker(QThread):
    data_ready = Signal(list)

    def __init__(self, auth_manager):
        super().__init__()
        self.auth_manager = auth_manager

    def run(self):
        actividad = self.auth_manager.get_recent_activity(limit=15)
        self.data_ready.emit(actividad)


class ViewArtist(QWidget):
    def __init__(self, parent: QWidget, auth_manager: AuthManager, nextcloud_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None]):
        
        super().__init__(parent)
        
        self.auth_manager = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.vault_manager = vault_manager
        self.config_factory = config_factory
        self.on_logout = on_logout

        self.setObjectName("ViewArtistBase")
        self._sidebar_buttons = {}
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._build_top_bar()

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)

        self._build_sidebar()
        self._build_main_area()
        
        self.main_layout.addLayout(self.body_layout)
        
        # Auto-Carga Inicial
        self._cargar_activity_feed()
        self.project_grid.cargar_proyectos()

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
            pixmap = QPixmap(str(logo_path))
            self.logo_icon.setPixmap(pixmap.scaledToHeight(40, Qt.SmoothTransformation))
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

        user_name = self.tr("Artist")
        if self.auth_manager.user_data:
            user_name = self.auth_manager.user_data.get("first_name", self.tr("Artist"))
        user_role = self.auth_manager.get_user_role().capitalize()
        
        self.lbl_name = QLabel(self.tr("{0} ({1})").format(user_name, user_role))
        self.lbl_name.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: bold;")
        self.lbl_name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_bar_layout.addWidget(self.lbl_name)

        self.avatar_icon = QLabel()
        self.avatar_icon.setObjectName("AvatarIcon")
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
            self.bell_icon.setStyleSheet("color: #64748B; font-size: 16px;")
        
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

    def _crear_boton_sidebar(self, texto: str, fallback_emoji: str, icon_name: str, activo: bool = False) -> QPushButton:
        btn = QPushButton()
        icon_path = Path(f"assets/icons/{icon_name}")
        
        color_hex = "#F97316" if activo else "#94A3B8"
        
        if icon_path.exists():
            btn.setIcon(self._crear_icono_coloreado(icon_path, color_hex))
            btn.setIconSize(QSize(22, 22))
            btn.setText(f"   {texto}")
        else:
            btn.setText(f"{fallback_emoji}   {texto}")
            
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

        # 1. Botón Maestro: Workspaces (Instalador/Launcher)
        self.btn_nav_projects = self._crear_boton_sidebar(self.tr("My Workspaces"), "🚀", "server.svg", activo=True)
        self.btn_nav_projects.clicked.connect(self._show_projects_view)
        sidebar_layout.addWidget(self.btn_nav_projects)

        sidebar_layout.addSpacing(15)

        # 2. Botón Tareas (TaskListWidget)
        self.btn_nav_tasks = self._crear_boton_sidebar(self.tr("All Tasks"), "📝", "folder.svg", activo=False)
        self.btn_nav_tasks.clicked.connect(lambda checked=False: self._show_tasks_view("All"))
        sidebar_layout.addWidget(self.btn_nav_tasks)

        # Contenedor Dinámico de Proyectos (Para filtrar Tareas)
        self.dynamic_projects_layout = QVBoxLayout()
        self.dynamic_projects_layout.setContentsMargins(0, 5, 0, 0)
        self.dynamic_projects_layout.setSpacing(5)
        sidebar_layout.addLayout(self.dynamic_projects_layout)

        sidebar_layout.addStretch()
        
        self.btn_nav_settings = self._crear_boton_sidebar(self.tr("Settings"), "🔧", "settings.svg", activo=False)
        sidebar_layout.addWidget(self.btn_nav_settings)
        
        self.body_layout.addWidget(self.sidebar)

    # ---------------------------------------------------------
    # NAVEGACIÓN Y ENRUTAMIENTO VIRTUAL
    # ---------------------------------------------------------

    def _update_sidebar_ui(self, active_button: QPushButton):
        """Gestiona las clases CSS y el teñido de iconos para reflejar el estado activo."""
        all_buttons = [self.btn_nav_projects, self.btn_nav_tasks, self.btn_nav_settings] + list(self._sidebar_buttons.values())
        
        for btn in all_buttons:
            if btn == active_button:
                btn.setObjectName("SidebarNavActive")
                # Intenta teñir el icono actual a naranja si tiene uno
                if not btn.icon().isNull():
                    # Nota: simplificamos asumiendo que el icono base es svg
                    btn.setStyleSheet(btn.styleSheet()) # Forzar repintado
            else:
                btn.setObjectName("SidebarNavInactive")
            
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _show_projects_view(self):
        self.stacked_content.setCurrentIndex(0)
        self._update_sidebar_ui(self.btn_nav_projects)

    def _show_tasks_view(self, filtro_name: str):
        self.stacked_content.setCurrentIndex(1)
        self.lista_tareas.aplicar_filtro(filtro_name)
        
        if filtro_name == "All":
            self._update_sidebar_ui(self.btn_nav_tasks)
        else:
            if filtro_name in self._sidebar_buttons:
                self._update_sidebar_ui(self._sidebar_buttons[filtro_name])

    def _actualizar_sidebar_proyectos(self, project_counts: dict):
        """Callback: Reconstruye los botones de proyectos subordinados del TaskList."""
        while self.dynamic_projects_layout.count():
            child = self.dynamic_projects_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self._sidebar_buttons.clear()

        for p_name, count in project_counts.items():
            btn = self._crear_boton_sidebar(f"{p_name} ({count})", "📦", "folder.svg", activo=False)
            btn.setStyleSheet(btn.styleSheet() + " font-size: 13px; padding-left: 35px;")
            
            btn.clicked.connect(lambda checked=False, n=p_name: self._show_tasks_view(n))
            self.dynamic_projects_layout.addWidget(btn)
            self._sidebar_buttons[p_name] = btn

    # ---------------------------------------------------------
    # CONSTRUCCIÓN DEL MAIN ÁREA (SPLIT)
    # ---------------------------------------------------------

    def _build_main_area(self):
        self.main_content = QFrame(self)
        self.main_content.setObjectName("MainContentFrame")
        
        content_layout = QVBoxLayout(self.main_content)
        content_layout.setContentsMargins(15, 25, 15, 20)
        content_layout.setSpacing(20)

        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(10)

        # Columna Izquierda: SISTEMA MULTIVISTA (StackedWidget)
        self.stacked_content = QStackedWidget(self.main_content)
        
        # Indice 0: Gestor de Workspaces (Blender Launcher)
        self.project_grid = ArtistProjectListWidget(
            parent=self.stacked_content,
            config_factory=self.config_factory,
            auth_manager=self.auth_manager,
            vault_manager=self.vault_manager,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.project_grid)

        # Indice 1: Gestor de Tareas de Kitsu
        self.lista_tareas = TaskListWidget(
            parent=self.stacked_content,
            nextcloud_dir=self.nextcloud_dir,
            auth_manager=self.auth_manager,
            vault_manager=self.vault_manager,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.lista_tareas.projects_discovered.connect(self._actualizar_sidebar_proyectos)
        self.stacked_content.addWidget(self.lista_tareas)

        self.stacked_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        split_layout.addWidget(self.stacked_content, stretch=3)

        # Columna Derecha: ACTIVITY FEED
        self.feed_container = QFrame(self.main_content)
        self.feed_container.setObjectName("FloatingCard") 
        
        feed_layout = QVBoxLayout(self.feed_container)
        feed_layout.setContentsMargins(15, 15, 15, 15)
        feed_layout.setSpacing(10)

        feed_header_layout = QHBoxLayout()
        self.feed_title = QLabel(self.tr("Activity Feed"))
        self.feed_title.setObjectName("H2Title")
        feed_header_layout.addWidget(self.feed_title)
        
        feed_header_layout.addStretch()
        
        self.btn_refresh_feed = QPushButton(self.tr("↻ Refresh"))
        self.btn_refresh_feed.setObjectName("SecondaryButton")
        self.btn_refresh_feed.setFixedSize(80, 25)
        self.btn_refresh_feed.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_feed.clicked.connect(self._cargar_activity_feed)
        feed_header_layout.addWidget(self.btn_refresh_feed)
        
        feed_layout.addLayout(feed_header_layout)

        self.feed_scroll_area = QScrollArea(self.feed_container)
        self.feed_scroll_area.setWidgetResizable(True)
        self.feed_scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.feed_scroll_widget = QWidget()
        self.feed_scroll_widget.setStyleSheet("background: transparent;")
        self.feed_scroll_layout = QVBoxLayout(self.feed_scroll_widget)
        self.feed_scroll_layout.setAlignment(Qt.AlignTop)
        
        self.feed_scroll_area.setWidget(self.feed_scroll_widget)
        feed_layout.addWidget(self.feed_scroll_area)

        split_layout.addWidget(self.feed_container, stretch=1)
        content_layout.addLayout(split_layout, stretch=1)

        # STATUS BAR
        self.status_bar = QFrame(self.main_content)
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.setFixedHeight(35)
        
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(15, 0, 15, 0)
        self.lbl_status = QLabel(self.tr("🔵 Kitsu: Online   |   🔄 VCS: Connecting..."))
        self.lbl_status.setObjectName("StatusText")
        status_layout.addWidget(self.lbl_status)

        content_layout.addWidget(self.status_bar)
        self.body_layout.addWidget(self.main_content)

    # ---------------------------------------------------------
    # FEED & STATUS LOGIC
    # ---------------------------------------------------------

    def _clear_feed_layout(self):
        while self.feed_scroll_layout.count():
            child = self.feed_scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _cargar_activity_feed(self):
        self._clear_feed_layout()
            
        self.feed_loading = QLabel(self.tr("Syncing..."))
        self.feed_loading.setStyleSheet("color: #64748B; font-style: italic;")
        self.feed_loading.setAlignment(Qt.AlignCenter)
        self.feed_scroll_layout.addWidget(self.feed_loading)
        
        self.worker = FeedWorker(self.auth_manager)
        self.worker.data_ready.connect(self._renderizar_feed)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _mostrar_feed_vacio(self):
        lbl_vacio = QLabel(self.tr("🎉 Inbox Zero\n\nYou have no pending notifications.\nYou are all caught up."))
        lbl_vacio.setStyleSheet("color: #10B981;")
        lbl_vacio.setAlignment(Qt.AlignCenter)
        self.feed_scroll_layout.addWidget(lbl_vacio)

    def _renderizar_feed(self, actividad: list):
        self._clear_feed_layout()

        if not actividad:
            self._mostrar_feed_vacio()
            return

        for evento in actividad:
            card = ActivityCard(
                parent=self.feed_scroll_widget,
                activity_data=evento,
                auth_manager=self.auth_manager,
                on_acknowledge_callback=self._on_activity_acknowledged
            )
            self.feed_scroll_layout.addWidget(card)

    def _on_activity_acknowledged(self, card_widget: QWidget):
        card_widget.hide()
        card_widget.deleteLater()
        
        visible_cards = sum(1 for i in range(self.feed_scroll_layout.count()) 
                            if self.feed_scroll_layout.itemAt(i).widget() 
                            and not self.feed_scroll_layout.itemAt(i).widget().isHidden())
        
        if visible_cards == 0:
            self._mostrar_feed_vacio()

    def actualizar_status(self, mensaje: str, color: str = 'white') -> None:
        if not hasattr(self, 'lbl_status'):
            return

        color_map = {"white": "#F8FAFC", "yellow": "#F59E0B", "green": "#10B981", "red": "#EF4444", "gray": "#64748B"}
        text_color = color_map.get(color.lower(), color)
        
        formato = self.tr("🔵 Kitsu: Online   |   🔄 VCS: Ready   |   {0}").format(mensaje)
        
        self.lbl_status.setText(formato)
        self.lbl_status.setStyleSheet(f"color: {text_color}; font-size: 12px;")
