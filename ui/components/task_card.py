# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/task_card.py
# Rol Arquitectónico: UI Component / Reusable Task Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.5
# =========================================================================================

"""
Componente visual reutilizable para las Tarjetas de Tareas (Task Cards).
Implementa variables de instancia para asegurar la persistencia en memoria
y evitar fugas de rutas en los callbacks de PySide6.
"""

import webbrowser
import requests
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage


class ThumbnailWorker(QThread):
    """QThread dedicado a la descarga de miniaturas por HTTP."""
    image_downloaded = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, preview_id: str, token: str, host_url: str):
        super().__init__()
        self.preview_id = preview_id
        self.token = token
        self.host_url = host_url

    def run(self):
        if not self.preview_id:
            self.error_occurred.emit("No Thumbnail Available")
            return

        try:
            img_url = f"{self.host_url}/pictures/thumbnails/preview-files/{self.preview_id}.png"
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = requests.get(img_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.image_downloaded.emit(response.content)
            else:
                self.error_occurred.emit("Thumbnail no encontrado en servidor")
                
        except Exception as e:
            print(f"[UI THUMBNAIL ERROR] Fallo en la descarga: {e}")
            self.error_occurred.emit("Error de conexión (Thumbnail)")


class TaskCard(QFrame):
    def __init__(self, parent, task_data: dict, project_root: Path, is_installed: bool, 
                 auth_manager, on_launch_callback, on_install_callback, 
                 can_work: bool = True, blocked_reason: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.task_data = task_data
        self.project_root = project_root
        self.is_installed = is_installed
        self.auth_manager = auth_manager
        
        self.can_work = can_work
        self.blocked_reason = blocked_reason
        
        self.on_launch_callback = on_launch_callback
        self.on_install_callback = on_install_callback
        
        # Persistencia en RAM: Guardamos la ruta config como propiedad de la clase
        if self.project_root:
            self.config_path = self.project_root / "06_conf_LOCAL" / "project_config.json"
        else:
            self.config_path = None
        
        self.setObjectName("FloatingCard")
        self.setMinimumHeight(350)
        self.setMinimumWidth(400)

        self._build_ui()
        self._cargar_miniatura()

    def _obtener_color_texto_contraste(self, hex_color: str) -> str:
        """Calcula luminancia sRGB relativa para el contraste del badge."""
        if not hex_color: return "white"
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return "white"
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#0F172A" if luminance > 0.5 else "#F8FAFC"
        except Exception:
            return "white"

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Fila Superior: Título y Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        entity_name = self.task_data.get('entity_name', self.task_data.get('name', 'Unknown Entity'))
        task_type = self.task_data.get('task_type_name', 'Task')
        title_text = f"{entity_name} - {task_type}"
        
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("H2Title")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        status_color = self.task_data.get("task_status_color", self.task_data.get("status_color", "#444444"))
        status_name = self.task_data.get("task_status_name", self.task_data.get("status_name", "TODO"))
        text_color_contraste = self._obtener_color_texto_contraste(status_color)
        
        self.status_badge = QLabel(status_name.upper())
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedHeight(24)
        self.status_badge.setStyleSheet(f"""
            background-color: {status_color};
            color: {text_color_contraste};
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            padding: 0 12px;
        """)
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)

        # Fila Central: Thumbnail Cinematográfico
        self.thumb_frame = QFrame(self)
        self.thumb_frame.setFixedHeight(252)
        self.thumb_frame.setStyleSheet("background-color: #0B1120; border-radius: 8px;") 
        
        thumb_layout = QVBoxLayout(self.thumb_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        self.thumb_label = QLabel("Cargando miniatura...")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("color: #475569; font-style: italic; font-size: 12px;")
        thumb_layout.addWidget(self.thumb_label)
        main_layout.addWidget(self.thumb_frame)

        # Fila Inferior: Botones de Acción
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 5, 0, 0)
        btn_layout.setSpacing(15)

        task_url = self.task_data.get("task_url")
        if task_url:
            self.kitsu_btn = QPushButton("Ver en Kitsu ↗")
            self.kitsu_btn.setObjectName("LinkButton")
            self.kitsu_btn.setFixedSize(100, 40)
            self.kitsu_btn.setCursor(Qt.PointingHandCursor)
            self.kitsu_btn.clicked.connect(lambda checked=False, u=task_url: webbrowser.open(u))
            btn_layout.addWidget(self.kitsu_btn)

        if not self.project_root:
            self.action_btn = QPushButton("Carpeta Extraviada en NAS")
            self.action_btn.setEnabled(False)
            self.action_btn.setStyleSheet("QPushButton { border: 2px solid #EF4444; color: #EF4444; background: transparent; border-radius: 8px; font-weight: bold; }")
        elif self.is_installed:
            if self.can_work:
                self.action_btn = QPushButton("Work on Task / Launch Blender")
                self.action_btn.setCursor(Qt.PointingHandCursor)
                self.action_btn.setStyleSheet("""
                    QPushButton { border: 1px solid #10B981; color: #10B981; background: transparent; border-radius: 8px; font-weight: bold; font-size: 14px; }
                    QPushButton:hover { background-color: rgba(16, 185, 129, 0.1); }
                """)
                # Callback blindado con variables de clase
                self.action_btn.clicked.connect(
                    lambda checked=False: self.on_launch_callback(self.project_root, self.config_path, self.task_data)
                )
            else:
                msg = self.blocked_reason if self.blocked_reason else "Acceso Denegado"
                self.action_btn = QPushButton(f"🔒 {msg}")
                self.action_btn.setEnabled(False)
                self.action_btn.setStyleSheet("QPushButton:disabled { border: 1px solid #475569; color: #94A3B8; background: transparent; border-radius: 8px; font-weight: bold; font-size: 14px; }")
        else:
            self.action_btn = QPushButton("Install Project Locally")
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet("""
                QPushButton { border: 1px solid #F59E0B; color: #F59E0B; background: transparent; border-radius: 8px; font-weight: bold; font-size: 14px; }
                QPushButton:hover { background-color: rgba(245, 158, 11, 0.1); }
            """)
            self.action_btn.clicked.connect(
                lambda checked=False: self.on_install_callback(self.project_root, self.task_data)
            )

        self.action_btn.setFixedHeight(40)
        self.action_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(self.action_btn)

        main_layout.addLayout(btn_layout)

    def _cargar_miniatura(self):
        preview_id = self.task_data.get("preview_file_id")
        token = self.auth_manager.get_current_token()
        base_url = self.auth_manager.kitsu_host
        
        self.worker = ThumbnailWorker(preview_id, token, base_url)
        self.worker.image_downloaded.connect(self._on_thumbnail_ready)
        self.worker.error_occurred.connect(self._on_thumbnail_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_thumbnail_ready(self, img_bytes: bytes):
        image = QImage.fromData(img_bytes)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(self.thumb_frame.width(), self.thumb_frame.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label.setText("") 
        else:
            self._on_thumbnail_error("Archivo de imagen corrupto")

    def _on_thumbnail_error(self, message: str):
        self.thumb_label.setText(message)
