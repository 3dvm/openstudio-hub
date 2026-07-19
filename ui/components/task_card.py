# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/task_card.py
# Rol Arquitectónico: UI Component / Reusable Task Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.8.0 (CTA Logic Matrix Fix)
# =========================================================================================

"""
Reusable visual component for Task Cards in the Artist Dashboard.
Uses ConfigFactory to resolve dynamic VFS local directory paths natively.
Implements a strict priority matrix for Call-To-Action (CTA) rendering.
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
                self.error_occurred.emit("Thumbnail not found on server")
                
        except Exception as e:
            print(f"[UI THUMBNAIL ERROR] Download failed: {e}")
            self.error_occurred.emit("Network connection error")


class TaskCard(QFrame):
    def __init__(self, parent, task_data: dict, project_root: Path, is_installed: bool, 
                 auth_manager, config_factory, on_launch_callback, on_install_callback, 
                 can_work: bool = True, blocked_reason: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.task_data = task_data
        self.project_root = project_root
        self.is_installed = is_installed
        self.auth_manager = auth_manager
        self.config_factory = config_factory
        
        self.can_work = can_work
        self.blocked_reason = blocked_reason
        
        self.on_launch_callback = on_launch_callback
        self.on_install_callback = on_install_callback
        
        if self.project_root and self.config_factory:
            vfs_local = self.config_factory.get_vfs_local_name()
            self.config_path = self.project_root / vfs_local / "project_config.json"
        else:
            self.config_path = None
        
        self.setObjectName("FloatingCard")
        self.setMinimumHeight(280)
        self.setMinimumWidth(380)

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
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ---------------------------------------------------------
        # Fila Superior: Título de Entidad y Tipo de Tarea
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        entity_name = self.task_data.get('entity_name', self.task_data.get('name', 'Unknown Entity'))
        task_type = self.task_data.get('task_type_name', 'Task')
        title_text = f"{entity_name} - {task_type}"
        
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("H2Title")
        self.title_label.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        status_color = self.task_data.get("task_status_color", self.task_data.get("status_color", "#444444"))
        status_name = self.task_data.get("task_status_name", self.task_data.get("status_name", "TODO"))
        text_color_contraste = self._obtener_color_texto_contraste(status_color)
        
        self.status_badge = QLabel(status_name.upper())
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedHeight(22)
        self.status_badge.setStyleSheet(f"""
            background-color: {status_color};
            color: {text_color_contraste};
            border-radius: 11px;
            font-size: 10px;
            font-weight: bold;
            padding: 0 10px;
        """)
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Fila Central: Thumbnail Cinematográfico
        # ---------------------------------------------------------
        self.thumb_frame = QFrame(self)
        self.thumb_frame.setFixedHeight(160)
        self.thumb_frame.setStyleSheet("background-color: #0B1120; border-radius: 8px;") 
        
        thumb_layout = QVBoxLayout(self.thumb_frame)
        thumb_layout.setContentsMargins(5, 5, 5, 5)
        
        self.thumb_label = QLabel(self.tr("No Thumbnail Available"))
        self.thumb_label.setObjectName("PlaceholderText")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("color: #475569; font-style: italic; font-size: 12px;")
        thumb_layout.addWidget(self.thumb_label)
        main_layout.addWidget(self.thumb_frame)

        # ---------------------------------------------------------
        # Fila Inferior: Botones de Acción Modulares
        # ---------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)

        task_url = self.task_data.get("task_url")
        if task_url:
            self.kitsu_btn = QPushButton(self.tr("Kitsu ↗"))
            self.kitsu_btn.setObjectName("LinkButton")
            self.kitsu_btn.setFixedSize(80, 36)
            self.kitsu_btn.setCursor(Qt.PointingHandCursor)
            self.kitsu_btn.setStyleSheet("""
                QPushButton#LinkButton { background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; font-size: 12px; }
                QPushButton#LinkButton:hover { background-color: #334155; color: #F8FAFC; }
            """)
            self.kitsu_btn.clicked.connect(lambda checked=False, u=task_url: webbrowser.open(u))
            btn_layout.addWidget(self.kitsu_btn)

        # Matriz Condicional de Renderizado del CTA Primario (Corregida)
        if not self.project_root:
            self.action_btn = QPushButton(self.tr("Folder Missing on NAS"))
            self.action_btn.setEnabled(False)
            self.action_btn.setStyleSheet("QPushButton { border: 1px solid #EF4444; color: #EF4444; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }")
        
        elif not self.can_work:
            # Prioridad Absoluta: Si está bloqueada, no importa si está instalada o no.
            msg = self.blocked_reason if self.blocked_reason else self.tr("Access Denied")
            self.action_btn = QPushButton(f"🔒 {msg}")
            self.action_btn.setEnabled(False)
            self.action_btn.setStyleSheet("QPushButton:disabled { border: 1px solid #475569; color: #94A3B8; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }")
        
        elif self.is_installed:
            self.action_btn = QPushButton(self.tr("Launch Project Environment"))
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet("""
                QPushButton { border: 1px solid #10B981; color: #10B981; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }
                QPushButton:hover { background-color: rgba(16, 185, 129, 0.1); }
            """)
            self.action_btn.clicked.connect(
                lambda checked=False: self.on_launch_callback(self.project_root, self.config_path, self.task_data)
            )
        
        else:
            self.action_btn = QPushButton(self.tr("Install Project Locally"))
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet("""
                QPushButton { border: 1px solid #F59E0B; color: #F59E0B; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }
                QPushButton:hover { background-color: rgba(245, 158, 11, 0.1); }
            """)
            self.action_btn.clicked.connect(
                lambda checked=False: self.on_install_callback(self.project_root, self.task_data)
            )

        self.action_btn.setFixedHeight(36)
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
            self._on_thumbnail_error(self.tr("Corrupted image format"))

    def _on_thumbnail_error(self, message: str):
        if "No Thumbnail" in message or "not found" in message:
            self.thumb_label.setText(self.tr("No Thumbnail Available"))
        else:
            self.thumb_label.setText(message)
