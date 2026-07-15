# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_login.py
# Rol Arquitectónico: UI View / Authentication
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.1
# =========================================================================================

"""
Vista principal para el inicio de sesión del usuario.
Maneja la interfaz de entrada (email, contraseña, url), valida los datos 
y delega la autenticación real al AuthManager en un hilo asíncrono.
Implementa diseño AAA (Floating Card) basado en los lineamientos visuales.
"""

import threading
import customtkinter as ctk
from PIL import Image

class ViewLogin(ctk.CTkFrame):
    def __init__(self, parent, auth_manager, vault_manager, on_login_success):
        # Fondo corporativo oscuro
        super().__init__(parent, fg_color="#0F172A")
        
        self.auth_manager = auth_manager
        self.vault_manager = vault_manager
        self.on_login_success = on_login_success

        self._build_ui()

    def _build_ui(self):
        # ---------------------------------------------------------
        # BARRA SUPERIOR (BRANDING & TOP BAR)
        # ---------------------------------------------------------
        self.top_bar = ctk.CTkFrame(self, height=60, fg_color="transparent")
        self.top_bar.pack(side="top", fill="x", padx=20, pady=10)
        
        # Logo / Título
        self.lbl_title = ctk.CTkLabel(
            self.top_bar, text="OpenStudio Hub", font=ctk.CTkFont(size=20, weight="bold"), text_color="#F8FAFC"
        )
        self.lbl_title.pack(side="left")

        # Perfil / Estado Login
        self.profile_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.profile_frame.pack(side="right")
        
        self.lbl_account = ctk.CTkLabel(
            self.profile_frame, text="Account\nLogin", font=ctk.CTkFont(size=12), text_color="#94A3B8", justify="left"
        )
        self.lbl_account.pack(side="right", padx=(10, 0))
        
        self.avatar_icon = ctk.CTkLabel(
            self.profile_frame, text="👤", font=ctk.CTkFont(size=24), text_color="#64748B",
            width=40, height=40, fg_color="#1E293B", corner_radius=20
        )
        self.avatar_icon.pack(side="right")

        # ---------------------------------------------------------
        # CONTENEDOR CENTRAL FLOTANTE (LOGIN CARD)
        # ---------------------------------------------------------
        self.login_box = ctk.CTkFrame(
            self, width=450, fg_color="#1E293B", 
            border_width=1, border_color="#334155", corner_radius=15
        )
        # Centrado absoluto
        self.login_box.place(relx=0.5, rely=0.5, anchor="center")
        
        # Título de la tarjeta
        self.lbl_card_title = ctk.CTkLabel(
            self.login_box, text="Log In to Kitsu Server", 
            font=ctk.CTkFont(size=26, weight="bold"), text_color="#F8FAFC"
        )
        # Se inyecta padx=50 para forzar los márgenes laterales internos
        self.lbl_card_title.pack(padx=50, pady=(40, 30))

        # Campos de Entrada (Estilo Formulario)
        self.entry_host = ctk.CTkEntry(
            self.login_box, placeholder_text="🔗 Kitsu Server URL (e.g., https://kitsu.studio.com)",
            width=350, height=45, corner_radius=8, border_width=1, 
            fg_color="#0F172A", border_color="#475569", text_color="#F8FAFC", font=ctk.CTkFont(size=13)
        )
        self.entry_host.pack(padx=50, pady=(0, 15))
        
        # Intentar cargar URL por defecto desde el config general
        try:
            from pathlib import Path
            import json
            settings_path = Path("settings.json")
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    config_data = json.load(f)
                kitsu_url = config_data.get("kitsu", {}).get("api_url", "")
                if kitsu_url:
                    self.entry_host.insert(0, kitsu_url)
        except Exception:
            pass

        self.entry_email = ctk.CTkEntry(
            self.login_box, placeholder_text="✉ Email Address",
            width=350, height=45, corner_radius=8, border_width=1, 
            fg_color="#0F172A", border_color="#475569", text_color="#F8FAFC", font=ctk.CTkFont(size=13)
        )
        self.entry_email.pack(padx=50, pady=(0, 15))

        self.entry_password = ctk.CTkEntry(
            self.login_box, placeholder_text="🔑 Password", show="•",
            width=350, height=45, corner_radius=8, border_width=1, 
            fg_color="#0F172A", border_color="#475569", text_color="#F8FAFC", font=ctk.CTkFont(size=13)
        )
        self.entry_password.pack(padx=50, pady=(0, 25))

        # Etiqueta para mensajes de error (Oculta por defecto)
        self.lbl_error = ctk.CTkLabel(
            self.login_box, text="", text_color="#EF4444", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_error.pack(padx=50, pady=(0, 10))

        # Botón Principal (Neon Glow Effect)
        self.btn_login = ctk.CTkButton(
            self.login_box, text="Iniciar sesión",
            width=350, height=50, corner_radius=8,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10B981", hover_color="#059669", text_color="#022C22",
            border_width=2, border_color="#34D399", # Simula el resplandor
            command=self.ejecutar_login
        )
        self.btn_login.pack(padx=50, pady=(0, 15))

        # Botón secundario (Forgot Password)
        self.btn_forgot = ctk.CTkButton(
            self.login_box, text="Forgot Password?",
            font=ctk.CTkFont(size=12), text_color="#3B82F6", hover_color="#1E293B",
            fg_color="transparent", width=120, height=20,
            command=lambda: None # No implementado en esta versión
        )
        self.btn_forgot.pack(padx=50, pady=(0, 30))

        # ---------------------------------------------------------
        # BARRA DE ESTADO (SYSTEM LOGGER)
        # ---------------------------------------------------------
        self.status_bar = ctk.CTkFrame(self, height=30, fg_color="#0F172A", corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        self.status_bar.pack_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            self.status_bar, text="🔵 Kitsu: Waiting for Credentials   |   🔄 VCS: Waiting", 
            text_color="#64748B", font=ctk.CTkFont(size=11)
        )
        self.lbl_status.pack(side="left", padx=10)

    # ---------------------------------------------------------
    # LÓGICA DE AUTENTICACIÓN ASÍNCRONA
    # ---------------------------------------------------------

    def ejecutar_login(self):
        """Valida campos locales y delega el proceso a un hilo secundario."""
        email = self.entry_email.get().strip()
        password = self.entry_password.get().strip()
        host = self.entry_host.get().strip()

        # Reseteo visual
        self.lbl_error.configure(text="")
        
        if not email or not password or not host:
            self.lbl_error.configure(text="Por favor, completa todos los campos.")
            return

        # Desactivar botón y cambiar a estado de carga
        self.btn_login.configure(state="disabled", text="Conectando al servidor...", fg_color="#F59E0B", border_color="#FBBF24")
        self.lbl_status.configure(text="🔵 Kitsu: Autenticando... Por favor espera.", text_color="#F59E0B")

        # Iniciar Worker Thread
        threading.Thread(target=self._hilo_login, args=(email, password, host), daemon=True).start()

    def _hilo_login(self, email, password, host):
        """El Thread asíncrono para comunicarse con el AuthManager."""
        exito, mensaje = self.auth_manager.login_with_credentials(email, password, host)
        
        if exito:
            # Zero-Disk Passwords: Guardar credenciales explícitas en RAM
            self.vault_manager.save_kitsu_credentials(email, password)
            # Retornar al hilo principal para montar la vista correcta
            self.after(0, self.on_login_success)
        else:
            self.after(0, self._restore_ui_on_error, mensaje)

    def _restore_ui_on_error(self, mensaje):
        """Método auxiliar para restaurar la interfaz desde el hilo principal."""
        self.lbl_error.configure(text=mensaje)
        self.btn_login.configure(state="normal", text="Iniciar sesión", fg_color="#10B981", border_color="#34D399")
        self.lbl_status.configure(text="🔴 Kitsu: Error de Autenticación.", text_color="#EF4444")
