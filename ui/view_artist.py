# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_artist.py
# Rol Arquitectónico: UI View / Artist Dashboard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.11
# =========================================================================================

"""
Panel de control modular para la interfaz de los Artistas (Dashboard).
Implementa el diseño de interfaz AAA (Dark Mode), separando el área de tareas
del Activity Feed lateral, y gestionando la telemetría visual.
"""

import threading
import customtkinter as ctk
from pathlib import Path
from typing import Callable

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory
from ui.widget_project_list import ProjectListWidget
from ui.components.activity_card import ActivityCard

class ViewArtist(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk, auth_manager: AuthManager, nextcloud_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None]):
        
        # Color de fondo base oscuro corporativo
        super().__init__(parent, fg_color="#0F172A")
        
        # === ASIGNACIÓN DE DEPENDENCIAS ===
        self.auth_manager = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.vault_manager = vault_manager
        self.config_factory = config_factory
        self.on_logout = on_logout

        self._build_ui()
        self._cargar_activity_feed()

    def _build_ui(self) -> None:
        # Configuración de distribución de la cuadrícula principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------------------------------------------------------
        # 1. BARRA SUPERIOR (TOP BAR)
        # ---------------------------------------------------------
        self.top_bar = ctk.CTkFrame(self, height=60, fg_color="#1E293B", corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_propagate(False)
        
        # Logo / Título
        self.lbl_title = ctk.CTkLabel(
            self.top_bar, 
            text="OpenStudio Hub", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#F8FAFC"
        )
        self.lbl_title.pack(side="left", padx=20, pady=15)

        # Perfil de Usuario (Derecha)
        self.profile_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.profile_frame.pack(side="right", padx=20, pady=10)
        
        # Extraer datos de sesión
        user_name = "Artista"
        if self.auth_manager.user_data:
            user_name = self.auth_manager.user_data.get("first_name", "Artista")
        user_role = self.auth_manager.get_user_role().capitalize()

        # Botón discreto de Logout
        self.btn_logout = ctk.CTkButton(
            self.profile_frame, text="Log Out", width=60, height=28,
            fg_color="transparent", border_width=1, border_color="#64748B", text_color="#94A3B8",
            hover_color="#334155", command=self.on_logout
        )
        self.btn_logout.pack(side="right", padx=(15, 0))

        # Textos de Perfil
        self.lbl_role = ctk.CTkLabel(
            self.profile_frame, text=f"Role: {user_role}", 
            font=ctk.CTkFont(size=11), text_color="#D97706",
            fg_color="#451A03", corner_radius=8, width=70, height=20
        )
        self.lbl_role.pack(side="right", padx=10)
        
        self.lbl_name = ctk.CTkLabel(
            self.profile_frame, text=user_name, 
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#F8FAFC"
        )
        self.lbl_name.pack(side="right", padx=5)

        # Placeholder para Avatar Circular
        self.avatar_placeholder = ctk.CTkLabel(
            self.profile_frame, text=user_name[0] if user_name else "U",
            font=ctk.CTkFont(size=14, weight="bold"), width=35, height=35,
            fg_color="#334155", text_color="white", corner_radius=17
        )
        self.avatar_placeholder.pack(side="right", padx=5)

        # ---------------------------------------------------------
        # 2. BARRA DE ESTADO (SYSTEM LOGGER)
        # ---------------------------------------------------------
        self.status_bar = ctk.CTkFrame(self, height=30, fg_color="#0F172A", corner_radius=0)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.status_bar.grid_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            self.status_bar, text="🔵 Kitsu: Online   |   🔄 VCS: Conectando...", 
            text_color="#64748B", font=ctk.CTkFont(size=11)
        )
        self.lbl_status.pack(side="left", padx=10)

        # ---------------------------------------------------------
        # 3. ÁREA DE CONTENIDO PRINCIPAL (SPLIT VIEW)
        # ---------------------------------------------------------
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # 75% Tareas / 25% Feed
        self.main_content.grid_columnconfigure(0, weight=3)
        self.main_content.grid_columnconfigure(1, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        # 3.A: Columna Izquierda (Task Grid)
        self.lista_proyectos = ProjectListWidget(
            parent=self.main_content,
            nextcloud_dir=self.nextcloud_dir,
            auth_manager=self.auth_manager,
            vault_manager=self.vault_manager,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.lista_proyectos.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # 3.B: Columna Derecha (Activity Feed)
        self.feed_container = ctk.CTkFrame(self.main_content, fg_color="#1E293B", corner_radius=12)
        self.feed_container.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.feed_container.grid_rowconfigure(1, weight=1)
        self.feed_container.grid_columnconfigure(0, weight=1)

        # Cabecera del Feed (Título + Botón Refresh)
        self.feed_header = ctk.CTkFrame(self.feed_container, fg_color="transparent")
        self.feed_header.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        self.feed_header.grid_columnconfigure(0, weight=1)

        self.feed_title = ctk.CTkLabel(
            self.feed_header, text="Activity Feed", 
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#F8FAFC"
        )
        self.feed_title.grid(row=0, column=0, sticky="w")
        
        self.btn_refresh_feed = ctk.CTkButton(
            self.feed_header, text="↻ Refresh", width=60, height=24,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155", hover_color="#475569", text_color="#F8FAFC", corner_radius=6,
            command=self._cargar_activity_feed
        )
        self.btn_refresh_feed.grid(row=0, column=1, sticky="e")

        self.feed_scroll = ctk.CTkScrollableFrame(self.feed_container, fg_color="transparent")
        self.feed_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 10))

    # ---------------------------------------------------------
    # MÉTODOS DE DATOS ASÍNCRONOS
    # ---------------------------------------------------------

    def _cargar_activity_feed(self):
        """Dispara la carga de comentarios en un hilo secundario limpiando la UI previa."""
        # Limpiamos los elementos actuales para dar feedback visual de recarga
        for widget in self.feed_scroll.winfo_children():
            widget.destroy()
            
        self.feed_loading = ctk.CTkLabel(self.feed_scroll, text="Sincronizando...", text_color="#64748B", font=ctk.CTkFont(slant="italic"))
        self.feed_loading.pack(pady=20)
        
        threading.Thread(target=self._hilo_cargar_actividad, daemon=True).start()

    def _hilo_cargar_actividad(self):
        actividad = self.auth_manager.get_recent_activity(limit=15)
        self.after(0, self._renderizar_feed, actividad)

    def _mostrar_feed_vacio(self):
        """Dibuja un mensaje positivo cuando no hay notificaciones."""
        ctk.CTkLabel(
            self.feed_scroll, text="🎉 Inbox Zero\n\nNo tienes notificaciones pendientes.\nTodo está al día.",
            text_color="#10B981", justify="center"
        ).pack(pady=40)

    def _renderizar_feed(self, actividad: list):
        if hasattr(self, "feed_loading"):
            self.feed_loading.destroy()

        for widget in self.feed_scroll.winfo_children():
            widget.destroy()

        if not actividad:
            self._mostrar_feed_vacio()
            return

        # Renderizar cada componente modular inyectándole el Callback de destrucción
        for evento in actividad:
            card = ActivityCard(
                parent=self.feed_scroll,
                activity_data=evento,
                auth_manager=self.auth_manager,
                on_acknowledge_callback=self._on_activity_acknowledged
            )
            card.pack(fill="x", pady=4, padx=5)

    def _on_activity_acknowledged(self, card_widget: ctk.CTkFrame):
        """Callback detonado por ActivityCard tras enviar la señal a Kitsu."""
        card_widget.destroy()
        
        # Validar si el Inbox quedó vacío después de destruir esta tarjeta
        if not self.feed_scroll.winfo_children():
            self._mostrar_feed_vacio()

    def actualizar_status(self, mensaje: str, color: str = 'white') -> None:
        """Callback seguro para que los componentes hijos reporten su progreso."""
        color_map = {
            "white": "#F8FAFC",
            "yellow": "#F59E0B",
            "green": "#10B981",
            "red": "#EF4444",
            "gray": "#64748B"
        }
        text_color = color_map.get(color.lower(), color)
        formato = f"🔵 Kitsu: Online   |   🔄 VCS: Ready   |   {mensaje}"
        self.lbl_status.configure(text=formato, text_color=text_color)
