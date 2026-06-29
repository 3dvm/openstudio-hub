import customtkinter as ctk

class SVNLoginWindow(ctk.CTkToplevel):
    def __init__(self, parent, vault_manager, on_success_callback):
        """
        Ventana modal Just-In-Time para solicitar credenciales de SVN.
        """
        super().__init__(parent)
        self.title("Autenticacion Requerida")
        self.geometry("350x300")
        self.resizable(False, False)

        # Bloquear la ventana principal hasta que se resuelva esta
        self.transient(parent)
        self.grab_set()

        self.vault = vault_manager
        self.on_success = on_success_callback

        # --- DISEÑO DE LA INTERFAZ ---
        lbl_titulo = ctk.CTkLabel(self, text="Credenciales del Repositorio", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_titulo.pack(pady=(20, 10))

        lbl_info = ctk.CTkLabel(self, text="Ingresa tus datos de SVN.", text_color="gray")
        lbl_info.pack(pady=(0, 20))

        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuario SVN", width=250)
        self.entry_user.pack(pady=10)

        # Campo ofuscado para la contraseña
        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Contrasena SVN", show="*", width=250)
        self.entry_pass.pack(pady=10)

        self.lbl_error = ctk.CTkLabel(self, text="", text_color="red")
        self.lbl_error.pack(pady=5)

        self.btn_login = ctk.CTkButton(self, text="Continuar", command=self.ejecutar_login)
        self.btn_login.pack(pady=10)

    def ejecutar_login(self):
        """Valida, guarda en RAM y reanuda el proceso original."""
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()

        if not user or not pwd:
            self.lbl_error.configure(text="Ambos campos son obligatorios.")
            return

        # 1. Guardar de forma segura en RAM
        self.vault.save_svn_credentials(user, pwd)

        # 2. Ejecutar la accion que habia sido pausada (Callback)
        self.on_success()
        
        # 3. Autodestruir el modal
        self.destroy()
