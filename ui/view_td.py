# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_td.py
# Rol Arquitectónico: UI View / Command Center Dashboard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.0.1
# =========================================================================================

"""
Panel de control avanzado para el Director Técnico (TD) y Supervisores.
Orquesta la navegación entre el monitoreo de proyectos y la infraestructura del estudio.
Estructurado en un modelo Sidebar/MainView preparatorio para la migración a PySide6.
"""

import customtkinter as ctk
from pathlib import Path
from typing import Callable

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory
from ui.window_new_project import NewProjectWindow
from ui.widget_project_list import ProjectListWidget

class ViewTD(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk, auth_manager: AuthManager, nextcloud_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None]):
        super().__init__(parent, fg_color="#121212") # Color base Carbono/Slate
        
        self.auth = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.vault = vault_manager
        self.config_factory = config_factory
        self.on_logout = on_logout

        # Configuración de expansión de cuadrícula (Preparando paradigma QGridLayout)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        """Construye la barra lateral de navegación (Sidebar)."""
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1A1A1A")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Branding del Estudio
        lbl_branding = ctk.CTkLabel(
            self.sidebar, text="MACUARE\nSTUDIOS", 
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#F8FAFC", justify="left"
        )
        lbl_branding.pack(pady=(30, 40), padx=20, anchor="w")

        # Botones de Navegación (Simulando Tabs)
        self.btn_nav_projects = ctk.CTkButton(
            self.sidebar, text="📁  Proyectos", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#064E3B", text_color="#10B981", hover_color="#064E3B", # Estado Activo
            anchor="w", height=45, corner_radius=8
        )
        self.btn_nav_projects.pack(fill="x", padx=10, pady=5)

        self.btn_nav_infra = ctk.CTkButton(
            self.sidebar, text="⚙️  Infraestructura", 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent", text_color="#94A3B8", hover_color="#334155", # Estado Inactivo
            anchor="w", height=45, corner_radius=8
        )
        self.btn_nav_infra.pack(fill="x", padx=10, pady=5)

    def _build_main_area(self):
        """Construye el área principal de contenido elástico."""
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=30, pady=20)
        
        # --- CABECERA SUPERIOR (TOP BAR) ---
        top_bar = ctk.CTkFrame(self.main_content, height=50, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 20))

        rol = self.auth.get_user_role()
        nombre_user = self.auth.user_data.get("first_name", rol.capitalize())
        
        # Simulando el "User Avatar & Role" del diseño
        lbl_user_info = ctk.CTkLabel(
            top_bar, text=f"👤 {nombre_user} — Tech Director", 
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#E2E8F0"
        )
        lbl_user_info.pack(side="left")

        btn_logout = ctk.CTkButton(
            top_bar, text="Cerrar Sesión", width=120, height=35,
            fg_color="transparent", border_width=1, border_color="#EF4444", 
            text_color="#EF4444", hover_color="#7F1D1D", 
            command=self.on_logout
        )
        btn_logout.pack(side="right")

        # --- HERO ACTION (Botón Crear Proyecto) ---
        # Botón gigante verde esmeralda basado en el mockup de diseño AAA
        btn_nuevo_proy = ctk.CTkButton(
            self.main_content, 
            text="+ Create New Project", 
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10B981", hover_color="#059669", text_color="#022C22",
            height=50, corner_radius=8,
            command=self.abrir_wizard_proyecto
        )
        btn_nuevo_proy.pack(fill="x", pady=(0, 20))

        # --- GRID DE PROYECTOS (Componente Inyectado) ---
        self.lista_proyectos = ProjectListWidget(
            parent=self.main_content,
            nextcloud_dir=self.nextcloud_dir,
            auth_manager=self.auth,
            vault_manager=self.vault,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.lista_proyectos.pack(fill="both", expand=True)

        # --- BARRA DE ESTADO (STATUS BAR) ---
        self.status_bar = ctk.CTkFrame(self.main_content, height=35, corner_radius=8, fg_color="#1A1A1A")
        self.status_bar.pack(fill="x", pady=(20, 0))

        self.lbl_status = ctk.CTkLabel(
            self.status_bar, text="🟢 Sistema Listo. Conectado a Kitsu.", 
            text_color="#94A3B8", font=ctk.CTkFont(size=12)
        )
        self.lbl_status.pack(side="left", padx=15, pady=5)

    def abrir_wizard_proyecto(self):
        """Abre la ventana modal para inicializar un proyecto nuevo delegando el flujo (MVC)."""
        NewProjectWindow(
            parent=self.winfo_toplevel(),
            nextcloud_dir=self.nextcloud_dir,
            on_success_callback=self.lista_proyectos.cargar_proyectos
        )

    def actualizar_status(self, mensaje: str, color: str = "white"):
        """Callback de estado (Preparatorio para arquitectura de Signals/Slots en PySide6)."""
        colores = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444", "gray": "#9CA3AF", "white": "#F8FAFC"}
        texto_color = colores.get(color, color)
        self.lbl_status.configure(text=mensaje, text_color=texto_color)
