import customtkinter as ctk
from pathlib import Path
from typing import Callable
from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory
from ui.widget_project_list import ProjectListWidget

class ViewArtist(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk, auth_manager: AuthManager, nextcloud_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None]):
        """Panel de control modular para la interfaz de los Artistas."""
        super().__init__(parent)
        
        # === ASIGNACIÓN DE DEPENDENCIAS ===
        self.auth_manager = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.vault_manager = vault_manager
        self.config_factory = config_factory
        self.on_logout = on_logout

        self._build_ui()

    def _build_ui(self) -> None:
        # Configuración de distribución de la cuadrícula
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Bar superior de navegación / acciones
        self.top_bar = ctk.CTkFrame(self, height=50)
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.top_bar.grid_propagate(False)
        
        self.lbl_title = ctk.CTkLabel(self.top_bar, text="Proyectos Asignados (Artist Workspace)", font=ctk.CTkFont(weight="bold"))
        self.lbl_title.pack(side="left", padx=15, pady=10)

        self.btn_logout = ctk.CTkButton(self.top_bar, text="Cerrar Sesión", fg_color="#991B1B", hover_color="#7F1D1D", command=self.on_logout)
        self.btn_logout.pack(side="right", padx=15, pady=10)

        # === SOLUCIÓN: BARRA DE ESTADO CONSTRUIDA ANTES ===
        # Definimos el widget contenedor y el label en RAM para que el callback asíncrono
        # del ProjectListWidget pueda encontrar el atributo inicializado.
        self.status_bar = ctk.CTkFrame(self, height=30, fg_color="#1E293B")
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.status_bar.grid_propagate(False)

        self.lbl_status = ctk.CTkLabel(self.status_bar, text="Sistema listo.", text_color="white", font=ctk.CTkFont(size=11))
        self.lbl_status.pack(side="left", padx=15, pady=2)

        # === INYECCIÓN DEL WIDGET DE PROYECTOS ===
        # Al ejecutarse cargar_proyectos() en su __init__, lbl_status ya existirá.
        self.lista_proyectos = ProjectListWidget(
            parent=self,
            nextcloud_dir=self.nextcloud_dir,
            auth_manager=self.auth_manager,
            vault_manager=self.vault_manager,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.lista_proyectos.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    def actualizar_status(self, mensaje: str, color: str = 'white') -> None:
        """Callback seguro para que los componentes hijos reporten su progreso."""
        color_map = {
            "white": "#F8FAFC",
            "yellow": "#F59E0B",
            "green": "#10B981",
            "red": "#EF4444",
            "gray": "#94A3B8"
        }
        text_color = color_map.get(color.lower(), color)
        self.lbl_status.configure(text=mensaje, text_color=text_color)
