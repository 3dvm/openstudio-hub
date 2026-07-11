import customtkinter as ctk
from typing import Callable
from core.vault_manager import VaultManager

class SVNLoginWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk | ctk.CTkFrame, vault_manager: VaultManager, on_success_callback: Callable[[], None]):
        """Ventana modal Just-In-Time para solicitar credenciales del Repositorio VCS."""
        super().__init__(parent)
        
        self.title("Autenticación de Repositorio (VCS)")
        self.geometry("350x250")
        self.resizable(False, False)
        
        # Modal constraints (Forzar foco para bloquear la UI principal)
        self.transient(parent)
        self.grab_set()

        self.vault_manager = vault_manager
        self.on_success_callback = on_success_callback

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        self.lbl_info = ctk.CTkLabel(
            self, 
            text="Se requieren credenciales del Repositorio\npara sincronizar el entorno.", 
            text_color="yellow"
        )
        self.lbl_info.grid(row=0, column=0, pady=(20, 10), padx=20)

        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuario (VCS)")
        self.entry_user.grid(row=1, column=0, pady=10, padx=40, sticky="ew")

        self.entry_pwd = ctk.CTkEntry(self, placeholder_text="Contraseña", show="*")
        self.entry_pwd.grid(row=2, column=0, pady=10, padx=40, sticky="ew")

        self.btn_login = ctk.CTkButton(
            self, 
            text="Continuar Sincronización", 
            command=self.ejecutar_login,
            fg_color="#2ea043", hover_color="#238636"
        )
        self.btn_login.grid(row=3, column=0, pady=20, padx=40, sticky="ew")

    def ejecutar_login(self) -> None:
        """Valida los campos, guarda en la bóveda RAM y reanuda el proceso en pausa."""
        user = self.entry_user.get().strip()
        pwd = self.entry_pwd.get()

        if not user or not pwd:
            self.lbl_info.configure(text="Ambos campos son obligatorios.", text_color="red")
            return

        # Zero-Disk Passwords: Guardar estrictamente en RAM
        self.vault_manager.save_svn_credentials(user, pwd)
        
        self.destroy()
        # Retomamos el hilo o la función que había invocado esta modal
        self.on_success_callback()
