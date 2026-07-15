# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/activity_card.py
# Rol Arquitectónico: UI Component / Reusable Activity Item
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.10
# =========================================================================================

"""
Componente visual reutilizable para los elementos del Activity Feed (Bandeja de Entrada).
Renderiza metadatos ricos de Kitsu (adjuntos, playblasts, cambios de estado) y 
gestiona la lógica de Acuse de Recibo (Acknowledge) mediante hilos secundarios.
"""

import threading
import webbrowser
import customtkinter as ctk

class ActivityCard(ctk.CTkFrame):
    def __init__(self, parent, activity_data: dict, auth_manager, on_acknowledge_callback, **kwargs):
        
        # Color base ligeramente diferenciado del fondo para generar contraste (Efecto Tarjeta)
        super().__init__(parent, fg_color="#1E293B", border_width=1, border_color="#334155", corner_radius=8, **kwargs)
        
        self.activity_data = activity_data
        self.auth_manager = auth_manager
        self.on_acknowledge_callback = on_acknowledge_callback
        
        self._build_ui()

    def _obtener_color_texto_contraste(self, hex_color: str) -> str:
        """Calcula la luminancia relativa (sRGB) para contrastar el texto del Badge."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return "white"
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#0F172A" if luminance > 0.5 else "#F8FAFC"
        except Exception:
            return "white"

    def _build_ui(self):
        # ---------------------------------------------------------
        # Fila 1: Avatar, Autor y Fecha
        # ---------------------------------------------------------
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        avatar_char = self.activity_data.get('author_name', 'U')[0].upper()
        avatar = ctk.CTkLabel(
            header_frame, text=avatar_char, width=24, height=24, 
            fg_color="#3B82F6", text_color="white", corner_radius=12, font=ctk.CTkFont(size=10, weight="bold")
        )
        avatar.pack(side="left")
        
        title_text = f"{self.activity_data['author_name']} on {self.activity_data['task_name']}"
        title = ctk.CTkLabel(header_frame, text=title_text, font=ctk.CTkFont(size=12, weight="bold"), text_color="#F8FAFC")
        title.pack(side="left", padx=8)
        
        # Parseo simple de fecha (YYYY-MM-DD)
        date_str = self.activity_data.get("created_at", "")[:10]
        date_lbl = ctk.CTkLabel(header_frame, text=date_str, font=ctk.CTkFont(size=10), text_color="#64748B")
        date_lbl.pack(side="right")
        
        # ---------------------------------------------------------
        # Fila 2: Cuerpo del Comentario
        # ---------------------------------------------------------
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        body = self.activity_data.get('text', '')
        if body:
            body_lbl = ctk.CTkLabel(
                text_frame, text=body, font=ctk.CTkFont(size=11), text_color="#CBD5E1", 
                anchor="w", justify="left", wraplength=220
            )
            body_lbl.pack(fill="x", anchor="w")
            
        # ---------------------------------------------------------
        # Fila 3: Metadatos Ricos (Badges)
        # ---------------------------------------------------------
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.pack(fill="x", padx=10, pady=5)
        
        status_name = self.activity_data.get("status_name")
        if status_name:
            bg_color = self.activity_data.get("status_color", "#444444")
            fg_color = self._obtener_color_texto_contraste(bg_color)
            
            # Etiqueta de pre-aviso
            ctk.CTkLabel(meta_frame, text="Estado:", font=ctk.CTkFont(size=10), text_color="#64748B").pack(side="left", padx=(0, 4))
            
            status_badge = ctk.CTkLabel(
                meta_frame, text=status_name.upper(), font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=bg_color, text_color=fg_color, corner_radius=6, height=18, width=10
            )
            status_badge.pack(side="left", padx=(0, 10))
            
        if self.activity_data.get("has_previews"):
            ctk.CTkLabel(meta_frame, text="🎬 Video", font=ctk.CTkFont(size=10, weight="bold"), text_color="#10B981").pack(side="left", padx=(0, 8))
            
        if self.activity_data.get("has_attachments"):
            ctk.CTkLabel(meta_frame, text="📎 Adjunto", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="left", padx=(0, 8))
            
        reply_count = self.activity_data.get("reply_count", 0)
        if reply_count > 0:
            ctk.CTkLabel(meta_frame, text=f"💬 {reply_count}", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="left")

        # ---------------------------------------------------------
        # Fila 4: Botón de Acción (Acuse de Recibo)
        # ---------------------------------------------------------
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        action_btn = ctk.CTkButton(
            btn_frame, text="Abrir & Marcar Leído ↗", 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#3B82F6", hover_color="#2563EB", text_color="#F8FAFC",
            height=26,
            command=self._ejecutar_accion
        )
        action_btn.pack(side="right")

    def _ejecutar_accion(self):
        """Abre el navegador, notifica al backend y se destruye a sí misma."""
        # 1. Abrir navegador en la URL de la tarea
        task_url = self.activity_data.get("task_url")
        if task_url:
            webbrowser.open(task_url)
            
        # 2. Despachar señal a Kitsu (Acuse de Recibo) en un hilo para no congelar la UI
        threading.Thread(target=self._hilo_acknowledge, daemon=True).start()
        
        # 3. Avisar al controlador padre que esta tarjeta ya fue leída para que actualice la lista
        if self.on_acknowledge_callback:
            self.on_acknowledge_callback(self)

    def _hilo_acknowledge(self):
        task_id = self.activity_data.get("task_id")
        comment_id = self.activity_data.get("comment_id")
        if task_id and comment_id:
            self.auth_manager.acknowledge_activity(task_id, comment_id)
