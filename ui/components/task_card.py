# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/task_card.py
# Rol Arquitectónico: UI Component / Reusable Card
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.8
# =========================================================================================

"""
Componente visual reutilizable para las Tarjetas de Tareas (Task Cards).
Encapsula el diseño AAA (CustomTkinter) y la lógica de descarga diferida (Lazy Loading)
de las miniaturas desde Kitsu usando PIL. Implementa algoritmos de luminancia para 
accesibilidad visual, recortes inteligentes en proporción 16:9 y navegación profunda (Deep Linking).
"""

import io
import threading
import webbrowser
import requests
import customtkinter as ctk
from PIL import Image, ImageOps
from pathlib import Path

class TaskCard(ctk.CTkFrame):
    def __init__(self, parent, task_data: dict, project_root: Path, is_installed: bool, 
                 auth_manager, on_launch_callback, on_install_callback, 
                 can_work: bool = True, blocked_reason: str = "", **kwargs):
        
        # Color base de la tarjeta y bordes redondeados
        super().__init__(parent, fg_color="#242424", corner_radius=12, **kwargs)
        
        self.task_data = task_data
        self.project_root = project_root
        self.is_installed = is_installed
        self.auth_manager = auth_manager
        
        # Parámetros de seguridad (Fail-Fast UI)
        self.can_work = can_work
        self.blocked_reason = blocked_reason
        
        # Callbacks inyectados desde el widget principal para manejar la lógica de negocio
        self.on_launch_callback = on_launch_callback
        self.on_install_callback = on_install_callback
        
        self._build_ui()
        self._cargar_miniatura()

    def _obtener_color_texto_contraste(self, hex_color: str) -> str:
        """
        Calcula la luminancia relativa (sRGB) de un color HEX para determinar
        si el texto superpuesto debe ser oscuro o claro.
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return "white" # Fallback de seguridad
            
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            # Formula estándar de luminancia percibida
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            
            if luminance > 0.5:
                return "#0F172A" # Texto gris muy oscuro para fondos claros
            else:
                return "#F8FAFC" # Texto blanco nieve para fondos oscuros
        except Exception:
            return "white"

    def _build_ui(self):
        # ---------------------------------------------------------
        # Fila Superior: Título y Badge de Estado
        # ---------------------------------------------------------
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        title_text = f"{self.task_data['entity_name']} - {self.task_data['task_type_name']}"
        title = ctk.CTkLabel(
            header_frame, text=title_text, 
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#F8FAFC"
        )
        title.pack(side="left")

        # Configuración dinámica del Badge con contraste inteligente
        status_color = self.task_data.get("status_color", "#444444")
        text_color_contraste = self._obtener_color_texto_contraste(status_color)
        
        status = ctk.CTkLabel(
            header_frame, text=self.task_data['status_name'].upper(), font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=status_color, text_color=text_color_contraste, corner_radius=10, width=60, height=24
        )
        status.pack(side="right")

        # ---------------------------------------------------------
        # Fila Central: Thumbnail Cinematográfico (16:9)
        # ---------------------------------------------------------
        # Se ajustó la altura a 252px para mantener la proporción exacta 16:9 (448x252)
        self.thumb_frame = ctk.CTkFrame(self, fg_color="#1A1A1A", height=252, corner_radius=8)
        self.thumb_frame.pack(fill="x", padx=15, pady=10)
        self.thumb_frame.pack_propagate(False) # Forzar altura para mantener diseño uniforme
        
        self.thumb_label = ctk.CTkLabel(
            self.thumb_frame, text="Cargando miniatura...", 
            font=ctk.CTkFont(slant="italic", size=11), text_color="#475569"
        )
        self.thumb_label.pack(expand=True, fill="both")

        # ---------------------------------------------------------
        # Fila Inferior: Botones de Acción (Glow Effect) y Deep Linking
        # ---------------------------------------------------------
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        # Botón de Hyperlink hacia Kitsu (Izquierda)
        task_url = self.task_data.get("task_url")
        if task_url:
            kitsu_btn = ctk.CTkButton(
                btn_frame, text="Ver en Kitsu ↗", 
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="transparent", hover_color="#334155", text_color="#3B82F6",
                height=40, width=100,
                command=lambda u=task_url: webbrowser.open(u)
            )
            kitsu_btn.pack(side="left", padx=(0, 10))

        # Botón de Acción Principal del Ecosistema (Derecha)
        if not self.project_root:
            btn = ctk.CTkButton(
                btn_frame, text="Carpeta de Proyecto Extraviada en NAS", state="disabled", 
                fg_color="transparent", border_width=2, border_color="#EF4444", text_color="#EF4444", height=40
            )
        elif self.is_installed:
            if self.can_work:
                config_path = self.project_root / "06_conf_LOCAL" / "project_config.json"
                btn = ctk.CTkButton(
                    btn_frame, text="Work on Task / Launch Blender", font=ctk.CTkFont(size=14, weight="bold"),
                    fg_color="transparent", border_width=2, border_color="#10B981", text_color="#10B981",
                    hover_color="#064E3B", height=40,
                    command=lambda: self.on_launch_callback(self.project_root, config_path, self.task_data)
                )
            else:
                # Botón bloqueado por seguridad (Fail-Fast UI)
                msg = self.blocked_reason if self.blocked_reason else "Acceso Denegado"
                btn = ctk.CTkButton(
                    btn_frame, text=f"🔒 {msg}", font=ctk.CTkFont(size=14, weight="bold"),
                    state="disabled", fg_color="transparent", border_width=2, 
                    border_color="#475569", text_color="#94A3B8", height=40
                )
        else:
            btn = ctk.CTkButton(
                btn_frame, text="Install Project Locally", font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="transparent", border_width=2, border_color="#F59E0B", text_color="#F59E0B",
                hover_color="#78350F", height=40,
                command=lambda: self.on_install_callback(self.project_root, self.task_data)
            )
            
        btn.pack(side="right", fill="x", expand=True)

    # ---------------------------------------------------------
    # LAZY LOADING DE IMÁGENES (PIL)
    # ---------------------------------------------------------
    
    def _cargar_miniatura(self):
        preview_id = self.task_data.get("preview_file_id")
        # Disparamos el hilo asíncrono para inyectar la imagen en PIL
        threading.Thread(target=self._hilo_descargar_miniatura, args=(preview_id,), daemon=True).start()

    def _hilo_descargar_miniatura(self, preview_id: str):
        """Descarga la imagen en RAM usando requests y la inyecta vía CTkImage con recorte 16:9."""
        if not preview_id:
            self.after(0, lambda: self._actualizar_label_seguro(text="No Thumbnail Available"))
            return

        try:
            token = self.auth_manager.get_current_token()
            base_url = self.auth_manager.kitsu_host
            img_url = f"{base_url}/pictures/thumbnails/preview-files/{preview_id}.png"
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(img_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                img_data = response.content
                img = Image.open(io.BytesIO(img_data)).convert("RGB")
                
                # Recorte central inteligente para forzar la proporción 16:9 sin aplastar
                img = ImageOps.fit(img, (448, 252), Image.Resampling.LANCZOS)
                
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(448, 252))
                self.after(0, lambda: self._actualizar_label_seguro(image=ctk_img, text=""))
            else:
                self.after(0, lambda: self._actualizar_label_seguro(text="Thumbnail no encontrado en servidor"))
                
        except Exception as e:
            print(f"[UI THUMBNAIL ERROR] Fallo en la descarga: {e}")
            self.after(0, lambda: self._actualizar_label_seguro(text="Error de conexión (Thumbnail)"))

    def _actualizar_label_seguro(self, image=None, text=""):
        """Asegura que el widget no haya sido destruido antes de inyectar la imagen."""
        if self.thumb_label.winfo_exists():
            if image:
                self.thumb_label.configure(image=image, text=text)
            else:
                self.thumb_label.configure(text=text)
