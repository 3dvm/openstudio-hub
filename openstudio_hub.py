import customtkinter as ctk
from pathlib import Path

# --- CORE (Motores) ---
from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

# --- UI (Vistas) ---
from ui.view_login import ViewLogin
from ui.view_artist import ViewArtist
from ui.view_td import ViewTD

# --- CONFIGURACION GLOBAL ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MacuareHub(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Issue v0.3.0: Título con versión
        self.title("OpenStudio Hub - v0.3.0")
        self.geometry("600x600")
        self.resizable(False, False)

        # 1. Inicializar los Motores
        self.auth = AuthManager()
        self.vault = VaultManager()
        
        # Leemos la configuración global B2B
        settings_path = Path("settings.json")
        self.config_factory = ConfigFactory(settings_path)

        # 2. Enrutador Inicial (State Machine)
        if self.auth.login_with_saved_session():
            self.mostrar_dashboard()
        else:
            self.mostrar_login()

    def limpiar_pantalla(self):
        """Destruye la vista actual para poder montar una nueva."""
        for widget in self.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        """Monta la vista de Login inyectando dependencias."""
        self.limpiar_pantalla()
        
        vista_login = ViewLogin(
            parent=self, 
            auth_manager=self.auth, 
            vault_manager=self.vault, 
            on_login_success=self.mostrar_dashboard
        )
        vista_login.pack(fill="both", expand=True)

    def mostrar_dashboard(self):
        """Monta la vista correcta dependiendo del rol extraído de Kitsu."""
        self.limpiar_pantalla()
        
        rol = self.auth.get_user_role()
        
        # SOLUCIÓN: Tomamos el Workspace Root directo mapeado en settings.json sin alteraciones
        nextcloud_dir = self.config_factory.get_workspace_root()
        
        if rol in ["td", "supervisor"]:
            vista = ViewTD(
                parent=self, 
                auth_manager=self.auth, 
                nextcloud_dir=nextcloud_dir, 
                vault_manager=self.vault,
                config_factory=self.config_factory,
                on_logout=self.ejecutar_logout
            )
        else:
            vista = ViewArtist(
                parent=self, 
                auth_manager=self.auth, 
                nextcloud_dir=nextcloud_dir,
                vault_manager=self.vault,
                config_factory=self.config_factory,
                on_logout=self.ejecutar_logout
            )
        
        vista.pack(fill="both", expand=True)

    def ejecutar_logout(self):
        """Limpia el estado global y devuelve al usuario al inicio."""
        self.auth.logout()
        self.vault.clear()  # Zero-Disk Passwords: Vaciamos la RAM
        self.mostrar_login()

if __name__ == "__main__":
    app = MacuareHub()
    app.mainloop()
