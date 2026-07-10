import threading
import customtkinter as ctk

class ViewLogin(ctk.CTkFrame):
    def __init__(self, parent, auth_manager, vault_manager, on_login_success):
        """
        Vista modular para el inicio de sesion.
        parent: Ventana principal (Tk o CTk)
        auth_manager: Instancia del nucleo de autenticacion
        vault_manager: Gestor de credenciales criticas en RAM (Boveda)
        on_login_success: Callback para avisar a la app que el login fue correcto
        """
        super().__init__(parent, fg_color="transparent")
        self.auth = auth_manager
        self.vault = vault_manager
        self.on_success = on_login_success


        frame = ctk.CTkFrame(self)
        frame.pack(pady=40, padx=40, fill="both", expand=True)

        lbl_titulo = ctk.CTkLabel(frame, text="OpenStudio Hub", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(30, 20))

        lbl_sub = ctk.CTkLabel(frame, text="Inicia sesion con tu cuenta de Kitsu", text_color="gray")
        lbl_sub.pack(pady=(0, 20))

        self.entry_host = ctk.CTkEntry(frame, placeholder_text="URL del Servidor (ej. https://kitsu...)")
        self.entry_host.insert(0, "https://proyectos.macuare.com.ve")
        self.entry_host.pack(pady=10, padx=30, fill="x")

        self.entry_email = ctk.CTkEntry(frame, placeholder_text="Correo Electronico")
        self.entry_email.pack(pady=10, padx=30, fill="x")

        self.entry_pass = ctk.CTkEntry(frame, placeholder_text="Contrasena", show="*")
        self.entry_pass.pack(pady=10, padx=30, fill="x")

        self.lbl_error = ctk.CTkLabel(frame, text="", text_color="red")
        self.lbl_error.pack(pady=5)

        self.btn_login = ctk.CTkButton(frame, text="Iniciar Sesion", command=self.ejecutar_login)
        self.btn_login.pack(pady=20, padx=30, fill="x")

    def ejecutar_login(self):
        """Valida campos locales y delega el proceso a un hilo secundario."""
        host = self.entry_host.get().strip()
        email = self.entry_email.get().strip()
        password = self.entry_pass.get().strip()

        if not host or not email or not password:
            self.lbl_error.configure(text="Por favor llena todos los campos.")
            return

        self.btn_login.configure(state="disabled", text="Conectando...")
        self.lbl_error.configure(text="")

        # Hilo secundario para no congelar la ventana mientras se habla con la API
        threading.Thread(target=self._hilo_login, args=(email, password, host), daemon=True).start()

    def _hilo_login(self, email, password, host):
        exito, mensaje = self.auth.login_with_credentials(email, password, host)
        if exito:
            # === CAPTURA EN RAM ===
            # Almacenamos de forma segura el email y password validados en la boveda volatil
            self.vault.save_kitsu_credentials(email, password)
            
            # Encolar el exito de vuelta al Hilo Principal (GUI Thread) para evitar TclError
            self.after(0, self.on_success)
        else:
            # Encolar la restauracion de la UI en caso de error
            self.after(0, self._restore_ui_on_error, mensaje)

    def _restore_ui_on_error(self, mensaje):
        """Metodo auxiliar para restaurar la interfaz desde el hilo principal."""
        self.btn_login.configure(state="normal", text="Iniciar Sesion")
        self.lbl_error.configure(text=mensaje)
